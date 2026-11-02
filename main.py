"""GTR simulation entry point."""
import json
from pathlib import Path
from components.car_class import Car
from components.simulation import Simulation
from components.track.track import Track
from components.world import GTRWorld

ROOT = Path(__file__).resolve().parent


def main():
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    tc = config['track']
    track = Track(file=ROOT / tc['file'], cell_size_m=tc['cell_size_m'],
                  width_m=tc['width_m'], mesh_resolution_m=tc.get('mesh_resolution_m', 0.5),
                  corner_rounding=tc.get('corner_rounding', 0.45),
                  line_width_m=tc.get('line_width_m', 0.12))
    car = Car.from_config(config['car'])
    simulation = Simulation(ROOT, config, track, car)
    world = GTRWorld(track, car, config.get('simulation', {}))
    simulation.sensor_view = world
    world.set_simulation(simulation)
    world.run()


if __name__ == '__main__':
    main()
