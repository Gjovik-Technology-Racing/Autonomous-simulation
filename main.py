"""Single entry point for the GTR simulator.

Root config selects global track + autonomous architecture. The selected
architecture config selects sensor components and vehicle simulation settings.
"""

import json
from pathlib import Path

from components.camera_class import Camera
from components.car_class import Car
from components.lidar_class import LiDAR
from components.speedsensor_class import SpeedSensor
from components.steeringsensor_class import SteeringSensor
from components.track.track import Track
from components.world import GTRWorld


ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def main():
    config = load_json(ROOT / "config.json")
    track_settings = config["track"]

    track = Track(
        file=ROOT / track_settings["file"],
        cell_size_m=track_settings["cell_size_m"],
        width_m=track_settings["width_m"],
        mesh_resolution_m=track_settings.get("mesh_resolution_m", 0.5),
        corner_rounding=track_settings.get("corner_rounding", 0.45),
        line_width_m=track_settings.get("line_width_m", 0.12),
    )
    print(f"Track: {track.file.name} | {track.length_m:.1f} m")

    architecture_name = config["architecture"]
    # Keep this selection inside the architectures directory.
    architecture_dir = (ROOT / "architectures" / architecture_name).resolve()
    if not architecture_dir.is_relative_to((ROOT / "architectures").resolve()):
        raise ValueError("Architecture path must be within architectures/")
    architecture_config = load_json(architecture_dir / "config.json")
    print(f"Architecture: {architecture_name}")

    # Vehicle is required by the simulation, regardless of sensor selection.
    car = Car.from_config(architecture_config["car"])
    print(f"Car: {car.model} | wheelbase {car.wheelbase_m:.2f} m")

    # Only components listed by the chosen architecture are instantiated.
    components = {
        "camera": Camera,
        "speed_sensor": SpeedSensor,
        "steering_sensor": SteeringSensor,
        "lidar": LiDAR,
    }
    sensors = {}
    for name, cls in components.items():
        if name in architecture_config:
            sensors[name] = cls.from_config(architecture_config[name])
            print(f"{name}: {sensors[name].model}")

    print("Components configured; vehicle motion/sensor rendering not connected yet.")
    # V1 retains the existing static track preview without changing GTRWorld.
    world = GTRWorld(track)
    world.run()


if __name__ == "__main__":
    main()
