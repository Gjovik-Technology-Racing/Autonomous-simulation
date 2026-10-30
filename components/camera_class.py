
import math


class ArducamMira220:
    """
    Arducam Mira220 RGB-IR USB 3.0 Camera (EK035).

    Manufacturer specifications:
    https://www.arducam.com/blog/product/arducam-2-2mp-mira220-rgb-ir-global-shutter-usb3-0-camera-evaluation-kit/

    Simulation model based on published hardware specifications.
    Camera intrinsics are estimates, not calibrated measurements.
    """

    # Sensor
    MODEL = "Mira220"
    SKU = "EK035"
    SENSOR_TYPE = "CMOS BSI"
    SHUTTER = "Global"
    COLOR_FILTER = "RGB-IR"
    OUTPUT_FORMAT = "RAW12"
    BIT_DEPTH = 12

    SENSOR_WIDTH_PX = 1600
    SENSOR_HEIGHT_PX = 1400
    PIXEL_SIZE_UM = 2.79
    OPTICAL_FORMAT = "1/2.7 inch"
    IR_CUT_FILTER = False

    # Lens
    FOCAL_LENGTH_MM = 3.6
    APERTURE_F = 2.8
    FOCUS = "Manual"
    LENS_MOUNT = "M12"

    FOV_HORIZONTAL_DEG = 68.0
    FOV_VERTICAL_DEG = 53.0
    FOV_DIAGONAL_DEG = 80.0

    # Supported capture modes: (width, height) -> maximum FPS
    MODES = {
        (1600, 1400): 30,
        (640, 480): 80,
    }

    # Exposure
    EXPOSURE_MIN_US = 12
    EXPOSURE_MAX_US = 33333
    GAIN_CONTROL = False

    # Electrical
    VOLTAGE_V = 5.0
    VOLTAGE_TOLERANCE = 0.05
    MAX_POWER_W = 1.32
    INTERFACE = "USB 3.0"

    # Operating conditions
    MIN_TEMPERATURE_C = 0
    MAX_TEMPERATURE_C = 50

    # Unknown parameters: require physical calibration
    DISTORTION_COEFFICIENTS = None
    SENSOR_NOISE_MODEL = None
    CAMERA_LATENCY_S = None

    def __init__(
        self,
        resolution=(1600, 1400),
        fps=None,
        exposure_us=1000,
        calibrated_fov_deg=None,
    ):
        if resolution not in self.MODES:
            raise ValueError("Unsupported camera resolution")

        self.width, self.height = resolution
        self.max_fps = self.MODES[resolution]
        self.fps = self.max_fps if fps is None else fps

        if not 0 < self.fps <= self.max_fps:
            raise ValueError("FPS exceeds supported camera mode")

        max_exposure = min(
            self.EXPOSURE_MAX_US,
            1_000_000 / self.fps,
        )

        if not self.EXPOSURE_MIN_US <= exposure_us <= max_exposure:
            raise ValueError("Exposure outside valid range")

        self.exposure_us = exposure_us

        if calibrated_fov_deg is not None:
            h_fov, v_fov = calibrated_fov_deg
            if not (0 < h_fov < 180 and 0 < v_fov < 180):
                raise ValueError("Invalid field of view")

        self.calibrated_fov_deg = calibrated_fov_deg

    @property
    def frame_period_s(self):
        return 1.0 / self.fps

    @property
    def exposure_s(self):
        return self.exposure_us / 1_000_000

    @property
    def sensor_size_mm(self):
        return (
            self.SENSOR_WIDTH_PX * self.PIXEL_SIZE_UM / 1000,
            self.SENSOR_HEIGHT_PX * self.PIXEL_SIZE_UM / 1000,
        )

    @property
    def fov_deg(self):
        if self.calibrated_fov_deg is not None:
            return self.calibrated_fov_deg

        if (self.width, self.height) != (1600, 1400):
            raise ValueError(
                "640x480 FOV is not specified by Arducam. "
                "Provide calibrated_fov_deg for geometric simulation."
            )

        return (
            self.FOV_HORIZONTAL_DEG,
            self.FOV_VERTICAL_DEG,
        )

    def camera_matrix(self):
        """
        Estimated pinhole camera intrinsics.
        Returns the 3x3 intrinsic matrix K.
        Lens distortion is not modeled.
        """
        h_fov, v_fov = self.fov_deg

        fx = self.width / (
            2 * math.tan(math.radians(h_fov) / 2)
        )
        fy = self.height / (
            2 * math.tan(math.radians(v_fov) / 2)
        )

        cx = (self.width - 1) / 2
        cy = (self.height - 1) / 2

        return [
            [fx, 0.0, cx],
            [0.0, fy, cy],
            [0.0, 0.0, 1.0],
        ]

    def project_point(self, x, y, z):
        """
        Project a 3D point into image coordinates.

        Optical coordinate frame:
            X = right
            Y = down
            Z = forward

        Coordinates are in meters.
        Returns (u, v) or None if outside the image.
        """
        if z <= 0:
            return None

        K = self.camera_matrix()

        u = K[0][0] * x / z + K[0][2]
        v = K[1][1] * y / z + K[1][2]

        if 0 <= u < self.width and 0 <= v < self.height:
            return (u, v)

        return None

    def specifications(self):
        """Return camera capabilities for simulation configuration."""
        return {
            "model": self.MODEL,
            "sku": self.SKU,
            "resolution": (self.width, self.height),
            "fps": self.fps,
            "global_shutter": True,
            "color_filter": self.COLOR_FILTER,
            "bit_depth": self.BIT_DEPTH,
            "pixel_size_um": self.PIXEL_SIZE_UM,
            "sensor_size_mm": self.sensor_size_mm,
            "focal_length_mm": self.FOCAL_LENGTH_MM,
            "aperture_f": self.APERTURE_F,
            "nominal_fov_deg": (
                self.FOV_HORIZONTAL_DEG,
                self.FOV_VERTICAL_DEG,
            ),
            "exposure_us": self.exposure_us,
            "frame_period_s": self.frame_period_s,
            "max_power_w": self.MAX_POWER_W,
            "voltage_v": self.VOLTAGE_V,
            "interface": self.INTERFACE,
            "distortion_calibrated": False,
            "noise_calibrated": False,
        }
