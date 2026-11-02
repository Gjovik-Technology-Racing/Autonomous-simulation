
"""Common vehicle control interface for all architectures."""


class VehicleInterface:
    def __init__(self, car, world):
        self.car = car
        self.world = world

    def apply_control(
        self,
        steering_deg: float,
        acceleration_mps2: float,
        dt_s: float,
    ):
        """Apply steering and acceleration for one simulation step."""

        self.car.step(
            dt_s=dt_s,
            acceleration_mps2=acceleration_mps2,
            steering_angle_deg=steering_deg,
        )

        self.world.update_vehicle_view()
