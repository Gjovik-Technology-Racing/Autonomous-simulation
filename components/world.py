
"""3D world visualization. No driving or control logic."""

import math

from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    Camera,
    CardMaker,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    PerspectiveLens,
    TextNode,
)


class GTRWorld(ShowBase):

    def __init__(self, track, car, simulation_config=None):
        super().__init__()

        self.track = track
        self.car = car
        self.config = simulation_config or {}

        self.disableMouse()
        self.setBackgroundColor(0.65, 0.80, 0.95)

        self._create_ground()
        self._create_road()
        self._position_overview()

        self._spawn_car()
        self._create_car_visual()

        self._create_debug_pov()
        self._create_hud()

    # ---------------------------------------------
    # WORLD
    # ---------------------------------------------

    def _create_ground(self):
        x0, x1, y0, y1 = self.track.bounds_m
        margin = 50

        card = CardMaker("ground")
        card.setFrame(
            x0 - margin, x1 + margin,
            y0 - margin, y1 + margin
        )

        ground = self.render.attachNewNode(card.generate())
        ground.setP(-90)
        ground.setZ(-0.5)
        ground.setColor(0.24, 0.47, 0.24, 1)
        ground.setLightOff()
        ground.setTwoSided(True)

    def _create_road(self):
        half = self.track.width_m / 2
        line = self.track.line_width_m

        self._create_strip(
            half, -half, 0.025,
            (0.18, 0.20, 0.23, 1)
        )
        self._create_strip(
            half, half - line, 0.04,
            (1, 1, 1, 1)
        )
        self._create_strip(
            -half + line, -half, 0.04,
            (1, 1, 1, 1)
        )

    def _create_strip(self, left_offset, right_offset, z, color):
        left = self.track.offset_curve(left_offset)
        right = self.track.offset_curve(right_offset)

        data = GeomVertexData(
            "road", GeomVertexFormat.getV3(), Geom.UHStatic
        )
        vertices = GeomVertexWriter(data, "vertex")

        for l, r in zip(left, right):
            vertices.addData3f(float(l[0]), float(l[1]), z)
            vertices.addData3f(float(r[0]), float(r[1]), z)

        triangles = GeomTriangles(Geom.UHStatic)

        for i in range(len(left) - 1):
            j = i * 2
            triangles.addVertices(j, j + 1, j + 2)
            triangles.addVertices(j + 1, j + 3, j + 2)

        triangles.closePrimitive()

        geom = Geom(data)
        geom.addPrimitive(triangles)

        node = GeomNode("road")
        node.addGeom(geom)

        road = self.render.attachNewNode(node)
        road.setColor(*color)
        road.setLightOff()
        road.setTwoSided(True)

    def _position_overview(self):
        x0, x1, y0, y1 = self.track.bounds_m

        x = (x0 + x1) / 2
        y = (y0 + y1) / 2
        extent = max(x1 - x0, y1 - y0, 20)

        self.camera.setPos(
            x, y - extent * 0.45, extent * 1.25
        )
        self.camera.lookAt(x, y, 0)

        self.camLens.setFov(65)
        self.camLens.setNearFar(
            1, max(1000, extent * 5)
        )

    # ---------------------------------------------
    # CAR VISUALIZATION
    # ---------------------------------------------

    def _spawn_car(self):
        points = self.track.centerline_m

        # Spawn far enough inside the track that the
        # vehicle is not hanging over the start edge.
        index = min(
            len(points) - 1,
            max(
                1,
                round(
                    (self.car.length_m / 2 + 0.5)
                    / self.track.mesh_resolution_m
                ),
            ),
        )

        start = points[index]
        ahead = points[min(index + 1, len(points) - 1)]

        self.car.x_m = float(start[0])
        self.car.y_m = float(start[1])

        self.car.heading_rad = math.atan2(
            float(ahead[1] - start[1]),
            float(ahead[0] - start[0]),
        )

        self.car.speed_mps = 0.0
        self.car.steering_angle_deg = 0.0

    def _create_car_visual(self):
        self.car_node = self.render.attachNewNode("car")

        # Simple flat blue vehicle footprint
        self._car_rectangle(
            "body",
            self.car.width_m,
            -self.car.length_m / 2,
            self.car.length_m / 2,
            0.10,
            (0.10, 0.35, 0.95, 1),
        )

        # Yellow front marker
        self._car_rectangle(
            "front",
            self.car.width_m * 0.75,
            self.car.length_m * 0.35,
            self.car.length_m * 0.48,
            0.12,
            (1.0, 0.8, 0.1, 1),
        )

        self.update_vehicle_view()

    def _car_rectangle(self, name, width, back, front, z, color):
        card = CardMaker(name)
        card.setFrame(-width / 2, width / 2, back, front)

        part = self.car_node.attachNewNode(card.generate())
        part.setP(-90)
        part.setZ(z)
        part.setColor(*color)
        part.setLightOff()
        part.setTwoSided(True)

    def update_vehicle_view(self):
        """Refresh visuals from the Car state. Does not move the car."""
        self.car_node.setPos(self.car.x_m, self.car.y_m, 0)

        # Avoid coordinate-convention mistakes by
        # explicitly pointing the vehicle along its heading.
        self.car_node.lookAt(
            self.car.x_m + math.cos(self.car.heading_rad),
            self.car.y_m + math.sin(self.car.heading_rad),
            0,
        )

        if hasattr(self, "hud_text"):
            self._refresh_hud()

    # ---------------------------------------------
    # DEBUG POV
    # ---------------------------------------------

    def _create_debug_pov(self):
        settings = self.config.get("debug_pov", {})

        if not settings.get("enabled", True):
            return

        region = self.win.makeDisplayRegion(
            0.7, 1, 0.70, 1.0
        )

        region.setSort(10)
        region.setClearColorActive(True)
        region.setClearColor((0.65, 0.80, 0.95, 1))
        region.setClearDepthActive(True)

        lens = PerspectiveLens()
        lens.setFov(settings.get("fov_deg", 75))

        width = 0.29 * self.win.getXSize()
        height = 0.31 * self.win.getYSize()

        lens.setAspectRatio(width / height)
        lens.setNearFar(0.05, 1500)

        self.pov_camera = self.car_node.attachNewNode(
            Camera("debug_pov")
        )
        self.pov_camera.node().setLens(lens)

        self.pov_camera.setPos(
            0,
            self.car.length_m * 0.20,
            settings.get("height_m", 0.8),
        )

        # Look at the road ahead, not the sky.
        self.pov_camera.lookAt(
            self.car_node,
            0,
            self.car.length_m * 0.20
            + settings.get("lookahead_m", 6.0),
            0.02,
        )

        region.setCamera(self.pov_camera)

    # ---------------------------------------------
    # TELEMETRY
    # ---------------------------------------------

    def _create_hud(self):
        settings = self.config.get("hud", {})

        if not settings.get("enabled", True):
            return

        self.hud_fields = settings.get("fields", [
            "speed_kmh",
            "steering_deg",
            "heading_deg",
            "position_xy",
        ])

        DirectFrame(
            parent=self.a2dTopLeft,
            frameSize=(0, 0.68, -0.34, 0),
            frameColor=(0.04, 0.06, 0.08, 0.85),
            pos=(0.04, 0, -0.04),
        )

        self.hud_text = OnscreenText(
            parent=self.a2dTopLeft,
            text="",
            pos=(0.08, -0.10),
            align=TextNode.ALeft,
            scale=0.037,
            fg=(1, 1, 1, 1),
            mayChange=True,
        )

        self._refresh_hud()

    def _refresh_hud(self):
        state = {
            "speed_kmh": f"Speed: {self.car.speed_mps * 3.6:.1f} km/h",
            "steering_deg": f"Steering: {self.car.steering_angle_deg:.1f} deg",
            "heading_deg": f"Heading: {self.car.heading_deg:.1f} deg",
            "position_xy": (
                f"Position: {self.car.x_m:.1f}, "
                f"{self.car.y_m:.1f} m"
            ),
        }

        self.hud_text.setText(
            "GTR / CAR STATE\n\n"
            + "\n".join(
                state[field] for field in self.hud_fields
            )
        )
