"""Panda3D scene and rendering of the geometry calculated by Track."""

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    CardMaker,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
)


class GTRWorld(ShowBase):
    def __init__(self, track):
        super().__init__()
        self.track = track
        self.disableMouse()
        self.setBackgroundColor(0.65, 0.80, 0.95)

        self._create_ground()
        self._create_road()
        self._position_preview_camera()

    def _create_ground(self):
        min_x, max_x, min_y, max_y = self.track.bounds_m
        margin = max(30.0, self.track.width_m * 5)
        mid_x, mid_y = (min_x + max_x) / 2, (min_y + max_y) / 2
        half_x = (max_x - min_x) / 2 + margin
        half_y = (max_y - min_y) / 2 + margin

        card = CardMaker("grass")
        card.setFrame(-half_x, half_x, -half_y, half_y)
        ground = self.render.attachNewNode(card.generate())
        ground.setPos(mid_x, mid_y, -0.5)
        ground.setP(-90)
        ground.setColor(0.24, 0.47, 0.24, 1.0)
        ground.setLightOff()
        ground.setTwoSided(True)

    def _create_road(self):
        half = self.track.width_m / 2
        line = self.track.line_width_m

        # Asphalt, then thin white borders slightly above it (avoids z-fighting).
        self._strip("asphalt", half, -half, 0.025, (0.18, 0.20, 0.23, 1.0))
        self._strip("left_white_edge", half, half - line, 0.04, (1, 1, 1, 1))
        self._strip("right_white_edge", -half + line, -half, 0.04, (1, 1, 1, 1))

    def _strip(self, name, left_offset, right_offset, z, color):
        left = self.track.offset_curve(left_offset)
        right = self.track.offset_curve(right_offset)
        data = GeomVertexData(name, GeomVertexFormat.getV3n3(), Geom.UHStatic)
        vertices = GeomVertexWriter(data, "vertex")
        normals = GeomVertexWriter(data, "normal")
        for l, r in zip(left, right):
            vertices.addData3f(float(l[0]), float(l[1]), z)
            vertices.addData3f(float(r[0]), float(r[1]), z)
            normals.addData3f(0, 0, 1)
            normals.addData3f(0, 0, 1)

        faces = GeomTriangles(Geom.UHStatic)
        for i in range(len(left) - 1):
            j = 2 * i
            faces.addVertices(j, j + 1, j + 2)
            faces.addVertices(j + 1, j + 3, j + 2)
        faces.closePrimitive()

        geom = Geom(data)
        geom.addPrimitive(faces)
        node = GeomNode(name)
        node.addGeom(geom)
        path = self.render.attachNewNode(node)
        path.setColor(*color)
        path.setLightOff()
        path.setTwoSided(True)

    def _position_preview_camera(self):
        min_x, max_x, min_y, max_y = self.track.bounds_m
        mid_x, mid_y = (min_x + max_x) / 2, (min_y + max_y) / 2
        extent = max(max_x - min_x, max_y - min_y, 20)
        self.camera.setPos(mid_x, mid_y - extent * 0.45, extent * 1.25)
        self.camera.lookAt(mid_x, mid_y, 0)
        self.camLens.setFov(65)
        self.camLens.setNearFar(1, max(1000, extent * 5))
