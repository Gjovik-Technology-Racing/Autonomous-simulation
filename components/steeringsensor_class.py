"""Generic steering-angle feedback sensor for simulation (not hardware I/O)."""

import math
import random


class SteeringSensor:
    """Reports front road-wheel-equivalent steering angle in degrees.

    IMPORTANT: a steering-wheel encoder / actuator encoder may have a
    different angular measurement. Convert that reading before using this
    class's road-wheel-angle configuration.
    """

    def __init__(self, model: str, specifications: dict, settings: dict):
        self.model = str(model)
        self.measurement = specifications.get("measurement", "road_wheel_angle")
        if self.measurement != "road_wheel_angle":
            raise ValueError("V1 SteeringSensor expects road_wheel_angle in degrees")
        min_angle, max_angle = map(float, specifications["range_deg"])
        self.min_angle_deg, self.max_angle_deg = min_angle, max_angle
        self.max_update_hz = float(specifications["max_update_hz"])
        self.update_hz = float(settings["update_hz"])
        self.noise_std_deg = float(settings.get("noise_std_deg", 0.0))
        self._rng = random.Random(settings.get("seed"))
        if not all(map(math.isfinite, (min_angle, max_angle, self.max_update_hz,
                                       self.update_hz, self.noise_std_deg))):
            raise ValueError("Steering sensor specifications must be finite")
        if min_angle >= max_angle or self.max_update_hz <= 0:
            raise ValueError("Invalid steering measurement range or maximum rate")
        if not 0 < self.update_hz <= self.max_update_hz:
            raise ValueError("update_hz exceeds steering sensor capabilities")
        if self.noise_std_deg < 0:
            raise ValueError("noise_std_deg must be >= 0")
        self._next_sample_s = 0.0
        self._last_time_s = -math.inf

    @classmethod
    def from_config(cls, config: dict) -> "SteeringSensor":
        return cls(config["model"], config["specifications"], config["settings"])

    @property
    def sample_period_s(self) -> float:
        return 1 / self.update_hz

    def sample(self, true_angle_deg: float, time_s: float) -> dict | None:
        time_s = float(time_s)
        true_angle_deg = float(true_angle_deg)
        if not math.isfinite(time_s) or not math.isfinite(true_angle_deg) or time_s < 0:
            raise ValueError("Steering angle and time must be finite; time must be nonnegative")
        if time_s < self._last_time_s:
            raise ValueError("Simulation time cannot run backwards")
        self._last_time_s = time_s
        if time_s + 1e-10 < self._next_sample_s:
            return None
        value = true_angle_deg + self._rng.gauss(0.0, self.noise_std_deg)
        value = max(self.min_angle_deg, min(self.max_angle_deg, value))
        self._next_sample_s = time_s + self.sample_period_s
        return {"time_s": time_s, "steering_angle_deg": value}
