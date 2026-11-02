import json
import math
from pathlib import Path
import tempfile
import unittest

from architecture_wizard import create, list_architectures, select
from components.car_class import Car
from components.simulation import Simulation, architecture_path
from components.track.track import Track

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))


def make_track():
    c = CONFIG['track']
    return Track(ROOT / c['file'], c['cell_size_m'], c['width_m'], c['mesh_resolution_m'], c['corner_rounding'], c['line_width_m'])


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'architectures').mkdir()
        create('test/example', root=self.root)
        self.config = dict(CONFIG, architecture='test/example')
        self.car = Car.from_config(CONFIG['car'])
        self.sim = Simulation(self.root, self.config, make_track(), self.car)

    def tearDown(self):
        self.sim.cleanup()
        self.temp.cleanup()

    def controller(self, statement):
        path = self.root / 'architectures/test/example/controller.py'
        path.write_text('class Controller:\n def __init__(self, config, data_dir): self.data_dir=data_dir\n def start(self): pass\n def update(self, observation):\n  ' + statement + '\n def stop(self): pass\n', encoding='utf-8')

    def test_ready_stationary_and_restart(self):
        initial = self.car.state().copy()
        self.sim.advance(1)
        self.assertEqual((self.sim.status, self.sim.time_s, self.car.state()), ('READY', 0, initial))
        self.controller("return {'steering_deg': 0, 'acceleration_mps2': 1}")
        self.sim.start()
        self.sim.advance(0.25)
        self.assertGreater(self.car.speed_mps, 0)
        self.sim.fail('test')
        self.assertEqual(self.car.state(), initial)
        self.sim.start()
        self.assertEqual(self.sim.status, 'RUNNING')
        self.assertEqual(self.sim.time_s, 0)
        self.assertEqual(self.car.state(), initial)

    def test_invalid_commands_and_exceptions_fail_safely(self):
        for statement in ["return {'steering_deg': float('nan'), 'acceleration_mps2': 0}", "return {'steering_deg': 26, 'acceleration_mps2': 0}", "return {'steering_deg': 0, 'acceleration_mps2': True}", "raise RuntimeError('controller broke')"]:
            self.controller(statement)
            self.sim.start()
            self.sim.step()
            self.assertEqual(self.sim.status, 'FAILED', statement)
            self.assertEqual(self.sim.time_s, 0)
            self.assertEqual(self.car.speed_mps, 0)

    def test_observation_retained_commands_and_departure(self):
        self.controller("assert set(observation) == {'time_s', 'sensors'} and observation['sensors'] == {}; return {'steering_deg': 10, 'acceleration_mps2': 1}")
        self.sim.start()
        self.sim.step()
        self.assertEqual(self.sim.status, 'RUNNING')
        self.assertEqual(self.car.steering_angle_deg, 10)
        self.car.x_m += 1000
        self.sim.step()
        self.assertEqual(self.sim.status, 'FAILED')
        self.assertIn('track', self.sim.reason)
        self.assertEqual(self.car.speed_mps, 0)

    def test_footprint_and_finish(self):
        self.assertTrue(self.sim.on_road())
        self.car.y_m += self.sim.track.width_m / 2
        self.assertFalse(self.sim.on_road())
        end = self.sim.track.centerline_m[-1]
        tangent = end - self.sim.track.centerline_m[-2]
        tangent /= math.hypot(*tangent)
        self.car.heading_rad = math.atan2(tangent[1], tangent[0])
        self.car.x_m, self.car.y_m = end - tangent * self.car.length_m / 2
        self.assertTrue(self.sim.finished())

    def test_initialization_error_and_stop(self):
        path = self.root / 'architectures/test/example/controller.py'
        path.write_text("class Controller:\n def __init__(self, config, data_dir): self.data_dir=data_dir\n def start(self): raise RuntimeError('start broke')\n def stop(self): (self.data_dir / 'stopped').touch()\n", encoding='utf-8')
        self.sim.start()
        self.assertEqual(self.sim.status, 'FAILED')
        self.assertIn('start broke', self.sim.reason)
        self.assertTrue((path.parent / 'data/stopped').exists())

    def test_sensor_rates_and_held_command(self):
        config_path = self.root / 'architectures/test/example/config.json'
        sensor_config = json.loads((ROOT / 'architectures/camera_only/try_1/config.json').read_text(encoding='utf-8'))
        config_path.write_text(json.dumps({'speed_sensor': sensor_config['speed_sensor']}), encoding='utf-8')
        self.controller("self.samples = getattr(self, 'samples', []) + [observation]; return {'steering_deg': 0, 'acceleration_mps2': 1} if len(self.samples) == 1 else None")
        self.sim.start()
        for _ in range(60): self.sim.step()
        observations = self.sim.controller.samples
        self.assertEqual(sum('speed_sensor' in o['sensors'] for o in observations), 20)
        self.assertTrue(all(set(o['sensors']) <= {'speed_sensor'} for o in observations))
        self.assertAlmostEqual(self.car.speed_mps, 1.0)

    def test_wizard_and_path_safety(self):
        data = self.root / 'architectures/test/example/data/dataset.bin'
        data.write_bytes(b'keep')
        create('test/copy', 'test/example', self.root)
        self.assertEqual(list_architectures(self.root), ['test/copy', 'test/example'])
        self.assertFalse((self.root / 'architectures/test/copy/data/dataset.bin').exists())
        with self.assertRaises(FileExistsError): create('test/example', root=self.root)
        self.assertEqual(data.read_bytes(), b'keep')
        for name in ('../escape', 'x/../../escape', 'x/..', '/x'):
            with self.assertRaises(ValueError): architecture_path(self.root, name)
        (self.root / 'config.json').write_text('{}', encoding='utf-8')
        select('test/copy', self.root)
        self.assertEqual(json.loads((self.root / 'config.json').read_text())['architecture'], 'test/copy')


if __name__ == '__main__':
    unittest.main()
