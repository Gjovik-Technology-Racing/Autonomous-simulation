"""Generic vehicle speed-feedback sensor for simulation (not hardware I/O)."""

import math
import random


class SpeedSensor:
    """Read ground/vehicle speed (m/s) at a configured sample rate.

    .sample() returns a timestamped reading when due, otherwise None.
    The calling simulation must supply the vehicle's true current speed.
    """

    def __init__(self, model: str, specifications: dict, settings: dict):
        self.model = str(model)
        self.measurement = specifications.get("measurement", "vehicle_speed")
        if self.measurement != "vehicle_speed":
            raise ValueError("V1 SpeedSensor expects vehicle_speed in m/s")
        min_speed, max_speed = map(float, specifications["range_mps"])
        self.min_speed_mps, self.max_speed_mps = min_speed, max_speed
        self.max_update_hz = float(specifications["max_update_hz"])
        self.update_hz = float(settings["update_hz"])
        self.noise_std_mps = float(settings.get("noise_std_mps", 0.0))
        self._rng = random.Random(settings.get("seed"))
        if not all(map(math.isfinite, (min_speed, max_speed, self.max_update_hz,
                                       self.update_hz, self.noise_std_mps))):
            raise ValueError("Speed sensor specifications must be finite")
        if min_speed >= max_speed or self.max_update_hz <= 0:
            raise ValueError("Invalid speed sensor measurement range or maximum rate")
        if not 0 < self.update_hz <= self.max_update_hz:
            raise ValueError("update_hz exceeds speed sensor capabilities")
        if self.noise_std_mps < 0:
            raise ValueError("noise_std_mps must be >= 0")
        self._next_sample_s = 0.0
        self._last_time_s = -math.inf

    @classmethod
    def from_config(cls, config: dict) -> "SpeedSensor":
        return cls(config["model"], config["specifications"], config["settings"])

    @property
    def sample_period_s(self) -> float:
        return 1 / self.update_hz

    def sample(self, true_speed_mps: float, time_s: float) -> dict | None:
        time_s = float(time_s)
        true_speed_mps = float(true_speed_mps)
        if not math.isfinite(time_s) or not math.isfinite(true_speed_mps) or time_s < 0:
            raise ValueError("Speed and time must be finite; time must be nonnegative")
        if time_s < self._last_time_s:
            raise ValueError("Simulation time cannot run backwards")
        self._last_time_s = time_s
        if time_s + 1e-10 < self._next_sample_s:
            return None
        value = true_speed_mps + self._rng.gauss(0.0, self.noise_std_mps)
        value = max(self.min_speed_mps, min(self.max_speed_mps, value))
        self._next_sample_s += self.sample_period_s
        return {"time_s": time_s, "speed_mps": value}
