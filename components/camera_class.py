"""Hardware-independent camera description for GTR simulation.

Camera holds capabilities and selected operating settings. It does NOT
render frames, access USB hardware, or implement perception algorithms.

Coordinate convention for project_point():
    +X = image right, +Y = image down, +Z = forward (meters).
"""

import math


class Camera:
    def __init__(self, model: str, specifications: dict, settings: dict):
        self.model = model
        self.shutter = specifications["shutter"]
        self.color_filter = specifications["color_filter"]
        min_exp, max_exp = specifications["exposure_range_us"]

        self.width, self.height = map(int, settings["resolution"])
        self.fps = float(settings["fps"])
        self.exposure_us = float(settings["exposure_us"])

        if self.width <= 0 or self.height <= 0:
            raise ValueError("Camera resolution must be positive")
        if not math.isfinite(self.fps) or self.fps <= 0:
            raise ValueError("Camera FPS must be positive and finite")
        if not math.isfinite(self.exposure_us):
            raise ValueError("Camera exposure must be finite")

        # The available capture modes belong to the hardware, not the architecture.
        mode = next(
            (
                m for m in specifications["modes"]
                if tuple(m["resolution"]) == (self.width, self.height)
            ),
            None,
        )
        if mode is None:
            raise ValueError(f"Unsupported resolution: {self.width}x{self.height}")
        if self.fps > float(mode["max_fps"]):
            raise ValueError("Configured FPS exceeds the selected camera mode")
        if not float(min_exp) <= self.exposure_us <= min(float(max_exp), 1e6 / self.fps):
            raise ValueError("Exposure is outside camera limits or frame duration")

        # FOV is mode-dependent: cropped modes may have a different field of view.
        # None means the mode needs measurement/calibration before geometric use.
        self.horizontal_fov_deg = mode.get("horizontal_fov_deg")
        if self.horizontal_fov_deg is not None:
            self.horizontal_fov_deg = float(self.horizontal_fov_deg)
            if not 0 < self.horizontal_fov_deg < 180:
                raise ValueError("Horizontal FOV must be between 0 and 180 degrees")

    @classmethod
    def from_config(cls, config: dict) -> "Camera":
        """Create from the 'camera' section of an architecture config."""
        return cls(
            model=config["model"],
            specifications=config["specifications"],
            settings=config["settings"],
        )

    @property
    def frame_period_s(self) -> float:
        return 1.0 / self.fps

    @property
    def fov_deg(self) -> tuple[float, float]:
        """Approximate H/V FOV, assuming square pixels and no distortion."""
        if self.horizontal_fov_deg is None:
            raise ValueError("FOV not specified for this mode; calibrate before use")
        horizontal_rad = math.radians(self.horizontal_fov_deg)
        vertical_rad = 2 * math.atan(
            (self.height / self.width) * math.tan(horizontal_rad / 2)
        )
        return self.horizontal_fov_deg, math.degrees(vertical_rad)

    def camera_matrix(self) -> list[list[float]]:
        """Estimated pinhole intrinsics K, NOT a calibrated real-camera matrix."""
        h_fov, _ = self.fov_deg
        focal_px = self.width / (2 * math.tan(math.radians(h_fov) / 2))
        return [
            [focal_px, 0.0, (self.width - 1) / 2],
            [0.0, focal_px, (self.height - 1) / 2],
            [0.0, 0.0, 1.0],
        ]

    def project_point(self, x: float, y: float, z: float) -> tuple[float, float] | None:
        """Project a point in the camera-optical frame into image pixels."""
        if z <= 0:
            return None
        K = self.camera_matrix()
        u = K[0][0] * x / z + K[0][2]
        v = K[1][1] * y / z + K[1][2]
        return (u, v) if 0 <= u < self.width and 0 <= v < self.height else None
