"""Generic, small kinematic bicycle model for 2D GTR vehicle simulations.

This class is independent of Panda3D and any autonomous architecture.
Vehicle geometry and limits must be calibrated for the real car.
"""

import math


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value


class Car:
    """Vehicle capabilities, state, and simple forward-driving dynamics.

    Conventions:
        x, y in metres; heading measured counterclockwise from +X.
        steering_angle_deg is the equivalent FRONT ROAD-WHEEL angle,
        NOT the steering wheel / motor shaft angle.
        acceleration_mps2: positive accelerate, negative brake.
    """

    def __init__(self, model: str, specifications: dict, settings: dict | None = None):
        settings = settings or {}
        self.model = str(model)
        self.length_m = _positive("length_m", specifications["length_m"])
        self.width_m = _positive("width_m", specifications["width_m"])
        self.height_m = _positive("height_m", specifications["height_m"])
        self.wheelbase_m = _positive("wheelbase_m", specifications["wheelbase_m"])
        if self.wheelbase_m > self.length_m:
            raise ValueError("wheelbase_m cannot exceed length_m")

        self.max_speed_mps = _positive("max_speed_mps", specifications["max_speed_mps"])
        self.max_steering_angle_deg = _positive(
            "max_steering_angle_deg", specifications["max_steering_angle_deg"]
        )
        if self.max_steering_angle_deg >= 85:
            raise ValueError("max_steering_angle_deg must be < 85")
        self.max_acceleration_mps2 = _positive(
            "max_acceleration_mps2", specifications["max_acceleration_mps2"]
        )
        self.max_braking_mps2 = _positive(
            "max_braking_mps2", specifications["max_braking_mps2"]
        )

        position = settings.get("initial_position_xy_m", [0.0, 0.0])
        if len(position) != 2:
            raise ValueError("initial_position_xy_m must contain [x, y]")
        self.x_m, self.y_m = map(float, position)
        self.heading_rad = math.radians(float(settings.get("initial_heading_deg", 0.0)))
        self.speed_mps = float(settings.get("initial_speed_mps", 0.0))
        self.steering_angle_deg = float(settings.get("initial_steering_angle_deg", 0.0))
        if not all(math.isfinite(v) for v in (
            self.x_m, self.y_m, self.heading_rad, self.speed_mps, self.steering_angle_deg
        )):
            raise ValueError("Initial vehicle state must be finite")
        if not 0 <= self.speed_mps <= self.max_speed_mps:
            raise ValueError("initial_speed_mps is outside the valid forward range")
        if abs(self.steering_angle_deg) > self.max_steering_angle_deg:
            raise ValueError("Initial steering angle exceeds vehicle limits")

    @classmethod
    def from_config(cls, config: dict) -> "Car":
        return cls(config["model"], config["specifications"], config.get("settings", {}))

    @property
    def heading_deg(self) -> float:
        return math.degrees(self.heading_rad)

    @property
    def center_turning_radius_m(self) -> float:
        """Bicycle-model REAR-AXLE path radius at maximum steering.

        Not Shell's outer-wheel turning radius, which is defined differently.
        """
        return self.wheelbase_m / math.tan(math.radians(self.max_steering_angle_deg))

    def step(self, dt_s: float, acceleration_mps2: float, steering_angle_deg: float) -> None:
        """Advance the car by dt seconds (constant commands over that step).

        V1 limitations: no tyre slip, actuator delay, grade, drag, or steering slew.
        Uses a midpoint approximation for position and heading integration.
        """
        dt_s = float(dt_s)
        acceleration_mps2 = float(acceleration_mps2)
        steering_angle_deg = float(steering_angle_deg)
        if not all(math.isfinite(v) for v in (dt_s, acceleration_mps2, steering_angle_deg)):
            raise ValueError("Vehicle commands and dt must be finite")
        if dt_s <= 0:
            raise ValueError("dt_s must be > 0")

        acceleration = max(-self.max_braking_mps2,
                           min(acceleration_mps2, self.max_acceleration_mps2))
        steering = max(-self.max_steering_angle_deg,
                       min(steering_angle_deg, self.max_steering_angle_deg))

        new_speed = max(0.0, min(self.max_speed_mps, self.speed_mps + acceleration * dt_s))
        average_speed = (self.speed_mps + new_speed) / 2.0
        yaw_change = (average_speed / self.wheelbase_m) * math.tan(math.radians(steering)) * dt_s
        heading_mid = self.heading_rad + yaw_change / 2.0

        self.x_m += average_speed * math.cos(heading_mid) * dt_s
        self.y_m += average_speed * math.sin(heading_mid) * dt_s
        self.heading_rad = (self.heading_rad + yaw_change + math.pi) % (2 * math.pi) - math.pi
        self.speed_mps = new_speed
        self.steering_angle_deg = steering

    def state(self) -> dict:
        return {
            "x_m": self.x_m,
            "y_m": self.y_m,
            "heading_deg": self.heading_deg,
            "speed_mps": self.speed_mps,
            "steering_angle_deg": self.steering_angle_deg,
        }
