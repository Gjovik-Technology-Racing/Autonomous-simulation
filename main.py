
"""Single entry point for the GTR simulator."""

import json
from pathlib import Path

from components.camera_class import Camera
from components.track.track import Track
from components.world import GTRWorld


ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def main():
    # Global track configuration
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

    # Load selected architecture configuration
    architecture_name = config["architecture"]
    architecture_file = (
        ROOT / "architectures" / architecture_name / "config.json"
    )

    architecture_config = load_json(architecture_file)
    print(f"Architecture: {architecture_name}")

    # Initialize configured components
    if "camera" in architecture_config:
        camera = Camera.from_config(architecture_config["camera"])
        print(
            f"Camera: {camera.model} | "
            f"{camera.width}x{camera.height} @ {camera.fps:g} FPS"
        )

    # Initialize 3D environment
    world = GTRWorld(track)
    world.run()


if __name__ == "__main__":
    main()
