
"""GTR simulation entry point."""

import json
from pathlib import Path

from components.car_class import Car
from components.track.track import Track
from components.world import GTRWorld
from components.vehicle_interface_class import VehicleInterface


ROOT = Path(__file__).resolve().parent


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    config = load_json(ROOT / "config.json")

    track_config = config["track"]

    track = Track(
        file=ROOT / track_config["file"],
        cell_size_m=track_config["cell_size_m"],
        width_m=track_config["width_m"],
        mesh_resolution_m=track_config.get("mesh_resolution_m", 0.5),
        corner_rounding=track_config.get("corner_rounding", 0.45),
        line_width_m=track_config.get("line_width_m", 0.12),
    )

    architecture_file = (
        ROOT / "architectures"
        / config["architecture"]
        / "config.json"
    )

    architecture = load_json(architecture_file)
    car = Car.from_config(architecture["car"])

    print(f"Track: {track.file.name}")
    print(f"Architecture: {config['architecture']}")

    world = GTRWorld(
        track,
        car,
        simulation_config=config.get("simulation", {}),
    )

    vehicle = VehicleInterface(car, world)

    world.run()


if __name__ == "__main__":
    main()
