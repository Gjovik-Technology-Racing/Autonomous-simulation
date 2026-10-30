"""Single entry point for the GTR simulation."""

import json
from pathlib import Path

from components.track.track import Track
from components.world import GTRWorld


ROOT = Path(__file__).resolve().parent


def main():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    settings = config["track"]

    track = Track(
        file=ROOT / settings["file"],
        cell_size_m=settings["cell_size_m"],
        width_m=settings["width_m"],
        mesh_resolution_m=settings.get("mesh_resolution_m", 0.5),
        corner_rounding=settings.get("corner_rounding", 0.45),
        line_width_m=settings.get("line_width_m", 0.12),
    )
    print(f"Track loaded: {track.file.name} | {track.length_m:.1f} m | width {track.width_m:.1f} m")

    world = GTRWorld(track)
    world.run()


if __name__ == "__main__":
    main()
