"""Validate and apply the shared vehicle command."""
import math
from numbers import Real


class VehicleInterface:
    def __init__(self, car):
        self.car = car

    def validate(self, command):
        if not isinstance(command, dict) or set(command) != {'steering_deg', 'acceleration_mps2'}:
            raise ValueError('Command must contain steering_deg and acceleration_mps2')
        values = tuple(command[k] for k in ('steering_deg', 'acceleration_mps2'))
        if any(isinstance(v, bool) or not isinstance(v, Real) or not math.isfinite(v) for v in values):
            raise ValueError('Control values must be finite numbers')
        steering, acceleration = values
        if abs(steering) > self.car.max_steering_angle_deg:
            raise ValueError('Steering exceeds vehicle limits')
        if not -self.car.max_braking_mps2 <= acceleration <= self.car.max_acceleration_mps2:
            raise ValueError('Acceleration exceeds vehicle limits')
        return dict(zip(('steering_deg', 'acceleration_mps2'), map(float, values)))

    def apply_control(self, command, dt_s):
        self.car.step(dt_s, command['acceleration_mps2'], command['steering_deg'])
