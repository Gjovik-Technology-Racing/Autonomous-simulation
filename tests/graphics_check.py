"""Run with a real display: python tests/graphics_check.py"""
import json
import sys
from pathlib import Path
import numpy as np
from panda3d.core import WindowProperties

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from components.car_class import Car
from components.simulation import Simulation
from components.track.track import Track
from components.world import GTRWorld

config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
t = config['track']
track = Track(ROOT / t['file'], t['cell_size_m'], t['width_m'], t['mesh_resolution_m'], t['corner_rounding'], t['line_width_m'])
car = Car.from_config(config['car'])
sim = Simulation(ROOT, config, track, car)
world = GTRWorld(track, car, config['simulation'])
sim.sensor_view = world
world.set_simulation(sim)
try:
    world.graphicsEngine.renderFrame()
    assert sim.status == 'READY' and sim.time_s == 0 and car.speed_mps == 0
    assert abs(world.camNode.getDisplayRegion(0).getRight() - 0.8) < 1e-6
    assert world.debug_region.getLeft() >= 0.8 - 1e-6
    count = world.graphicsEngine.getNumWindows()
    sim.start()
    assert sim.status == 'RUNNING', sim.reason
    world.graphicsEngine.renderFrame()
    assert world.graphicsEngine.getNumWindows() == count + 1
    captured = []
    for _ in range(12):
        sim.step()
        assert sim.status == 'RUNNING', sim.reason
        if not captured or captured[-1] is not world.camera_frame:
            captured.append(world.camera_frame)
    frame = captured[-1]
    assert len(captured) == 6, len(captured)
    assert frame.shape == (1400, 1600, 3) and frame.dtype == np.uint8
    assert not frame.flags.writeable
    tex = np.frombuffer(world.preview_texture.getRamImageAs('RGB'), dtype=np.uint8).reshape(frame.shape)
    assert np.array_equal(tex[::-1], frame)
    sim.fail('test failure')
    assert sim.status == 'FAILED' and world.graphicsEngine.getNumWindows() == count
    world._start()  # The Restart button invokes this callback.
    assert sim.status == 'RUNNING', sim.reason
    world.graphicsEngine.renderFrame()
    assert sim.time_s == 0 and world.graphicsEngine.getNumWindows() == count + 1
    sim.step()
    assert sim.status == 'RUNNING' and world.camera_frame is not None, sim.reason
    assert len(world.taskMgr.getTasksNamed('simulation-update')) == 1
    props = WindowProperties()
    props.setSize(1000, 700)
    world.win.requestProperties(props)
    for _ in range(4): world.taskMgr.step()
    assert abs(world.camNode.getDisplayRegion(0).getRight() - 0.8) < 1e-6
    assert world.debug_region.getLeft() >= 0.8 - 1e-6
    print('PASS: real Panda3D window, viewport, frame RGB/preview, 30 FPS sampling, failure/restart, resize')
finally:
    sim.cleanup()
    world.destroy()
