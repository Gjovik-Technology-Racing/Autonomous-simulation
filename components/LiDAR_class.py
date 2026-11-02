"""Generic 2D scanning LiDAR capabilities for future architectures.

Describes operating settings; does not perform raycasting or connect to hardware.
Not used by camera_only/try_1.
"""

import math


class LiDAR:
    def __init__(self, model: str, specifications: dict, settings: dict):
        self.model = str(model)
        self.min_range_m = float(specifications["min_range_m"])
        self.max_range_m = float(specifications["max_range_m"])
        self.max_scan_hz = float(specifications["max_scan_hz"])
        self.max_fov_deg = float(specifications["max_fov_deg"])
        self.scan_hz = float(settings["scan_hz"])
        self.fov_deg = float(settings["fov_deg"])
        self.angular_resolution_deg = float(settings["angular_resolution_deg"])

        values = [self.min_range_m, self.max_range_m, self.max_scan_hz,
                  self.max_fov_deg, self.scan_hz, self.fov_deg, self.angular_resolution_deg]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("LiDAR parameters must be finite")
        if not 0 <= self.min_range_m < self.max_range_m:
            raise ValueError("Invalid LiDAR distance limits")
        if not 0 < self.scan_hz <= self.max_scan_hz:
            raise ValueError("LiDAR scan rate exceeds hardware limit")
        if not 0 < self.fov_deg <= self.max_fov_deg <= 360:
            raise ValueError("LiDAR FOV exceeds hardware limit")
        if not 0 < self.angular_resolution_deg <= self.fov_deg:
            raise ValueError("Invalid angular resolution")

    @classmethod
    def from_config(cls, config: dict) -> "LiDAR":
        return cls(config["model"], config["specifications"], config["settings"])

    @property
    def scan_period_s(self) -> float:
        return 1.0 / self.scan_hz

    @property
    def approximate_beams_per_scan(self) -> int:
        """Approximate configured angular samples; real devices may vary."""
        return max(1, int(round(self.fov_deg / self.angular_resolution_deg)))
