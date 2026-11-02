"""Architecture loading, simulation lifecycle, and generic rules."""
import importlib.util
import json
import math

import numpy as np

from components.architecture import architecture_path
from components.vehicle_interface_class import VehicleInterface
from components.speedsensor_class import SpeedSensor
from components.steeringsensor_class import SteeringSensor

def load_architecture(root, name):
    path = architecture_path(root, name)
    config = json.loads((path / 'config.json').read_text(encoding='utf-8'))
    spec = importlib.util.spec_from_file_location('gtr_architecture', path / 'controller.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = path / 'data'
    data.mkdir(exist_ok=True)
    return module.Controller(config, data), config


class Simulation:
    def __init__(self, root, config, track, car, sensor_view=None):
        self.root, self.config, self.track, self.car = root, config, track, car
        self.sensor_view = sensor_view
        hz = float(config.get('simulation', {}).get('physics_hz', 60))
        if not math.isfinite(hz) or hz <= 0:
            raise ValueError('physics_hz must be positive and finite')
        self.dt = 1 / hz
        self.tolerance = float(config.get('simulation', {}).get('road_tolerance_m', 0.1))
        if not math.isfinite(self.tolerance) or self.tolerance < 0:
            raise ValueError('road_tolerance_m must be nonnegative and finite')
        self.vehicle = VehicleInterface(car)
        points = track.centerline_m
        index = min(len(points)-2, max(1, math.ceil((car.length_m/2 + 0.5) / track.mesh_resolution_m)))
        start, ahead = points[index], points[index+1]
        self.initial = (float(start[0]), float(start[1]), math.atan2(*(ahead-start)[::-1]), 0.0, 0.0)
        self.status, self.reason = 'READY', ''
        self.controller = None
        self.time_s = self.accumulator = 0.0
        self.reset_car()

    def reset_car(self):
        (self.car.x_m, self.car.y_m, self.car.heading_rad, self.car.speed_mps,
         self.car.steering_angle_deg) = self.initial

    def start(self):
        if self.status == 'RUNNING':
            return
        self.reset_car()
        self.time_s = self.accumulator = 0.0
        self.command = {'steering_deg': 0.0, 'acceleration_mps2': 0.0}
        self.reason = ''
        self.sensors = {}
        try:
            self.controller, settings = load_architecture(self.root, self.config['architecture'])
            for key, cls in (('speed_sensor', SpeedSensor), ('steering_sensor', SteeringSensor)):
                if settings.get(key) and settings[key].get('enabled', True):
                    self.sensors[key] = cls.from_config(settings[key])
                    if self.sensors[key].update_hz > 1 / self.dt:
                        raise ValueError(f'{key} update rate exceeds physics_hz')
            if self.sensor_view:
                self.sensor_view.start_camera(settings.get('camera'))
                if self.sensor_view.camera_buffer and self.sensor_view.camera_description.fps > 1 / self.dt:
                    raise ValueError('Camera FPS exceeds physics_hz')
            elif settings.get('camera') and settings['camera'].get('enabled', True):
                raise ValueError('Camera rendering is unavailable')
            self.controller.start()
            self.status = 'RUNNING'
        except Exception as exc:
            self.fail(f'Initialization error: {exc}')

    def cleanup(self):
        controller, self.controller = self.controller, None
        if controller:
            try:
                controller.stop()
            except Exception as exc:
                self.reason = self.reason or f'Architecture stop error: {exc}'
                self.status = 'FAILED'
                self.reset_car()
        if self.sensor_view:
            self.sensor_view.stop_camera()

    def fail(self, reason):
        self.reason = reason
        self.status = 'FAILED'
        self.cleanup()
        self.reset_car()
        self.accumulator = 0.0

    def advance(self, frame_dt):
        if self.status != 'RUNNING':
            return
        # Drop excessive elapsed time after pauses; never integrate a giant step.
        self.accumulator += max(0.0, min(float(frame_dt), 0.25))
        while self.accumulator + 1e-12 >= self.dt and self.status == 'RUNNING':
            self.accumulator -= self.dt
            self.step()

    def step(self):
        try:
            observation = {'time_s': self.time_s, 'sensors': {}}
            if self.sensor_view:
                frame = self.sensor_view.capture_if_due(self.time_s)
                if frame is not None:
                    observation['sensors']['camera'] = frame
            for key, sensor in self.sensors.items():
                value = self.car.speed_mps if key == 'speed_sensor' else self.car.steering_angle_deg
                reading = sensor.sample(value, self.time_s)
                if reading is not None:
                    observation['sensors'][key] = reading
            command = self.controller.update(observation)
            if command is not None:
                self.command = self.vehicle.validate(command)
            self.vehicle.apply_control(self.command, self.dt)
            self.time_s += self.dt
            if not all(math.isfinite(v) for v in self.car.state().values()):
                raise ValueError('Non-finite vehicle state')
            if not self.on_road():
                self.fail('Vehicle left the drivable track')
            elif self.finished():
                self.status = 'FINISHED'
                self.cleanup()
        except Exception as exc:
            self.fail(f'Execution error: {exc}')

    def on_road(self):
        # Test the entire rectangular footprint at a spacing finer than road mesh.
        c, s = math.cos(self.car.heading_rad), math.sin(self.car.heading_rad)
        forward = np.array([c, s]); left = np.array([-s, c])
        center = np.array([self.car.x_m, self.car.y_m])
        points = self.track.centerline_m
        a, segments = points[:-1], np.diff(points, axis=0)
        lengths2 = (segments * segments).sum(axis=1)
        for longitudinal in np.linspace(-self.car.length_m/2, self.car.length_m/2, 7):
            for lateral in np.linspace(-self.car.width_m/2, self.car.width_m/2, 3):
                p = center + forward * longitudinal + left * lateral
                t = np.clip(((p-a)*segments).sum(axis=1)/lengths2, 0, 1)
                distances = np.linalg.norm(a + t[:, None]*segments-p, axis=1)
                if distances.min() > self.track.width_m/2 + self.tolerance:
                    return False
        return True

    def finished(self):
        end = self.track.centerline_m[-1]
        tangent = end - self.track.centerline_m[-2]
        tangent /= np.linalg.norm(tangent)
        # Finish when the front reaches the finish plane, while still on the road.
        front = np.array([self.car.x_m, self.car.y_m]) + self.car.length_m/2 * np.array([math.cos(self.car.heading_rad), math.sin(self.car.heading_rad)])
        return np.dot(front-end, tangent) >= 0 and np.linalg.norm(front-end) <= self.track.width_m/2 + self.tolerance
