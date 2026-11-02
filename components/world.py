"""World rendering, camera previews, and the minimal simulation panel."""
import math
import numpy as np
from direct.gui.DirectGui import DirectButton, DirectFrame
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (Camera, CardMaker, Geom, GeomNode, GeomTriangles,
    GeomVertexData, GeomVertexFormat, GeomVertexWriter, PerspectiveLens,
    TextNode, Texture)
from components.camera_class import Camera as CameraDescription


class GTRWorld(ShowBase):
    def __init__(self, track, car, simulation_config=None):
        super().__init__()
        self.track, self.car = track, car
        self.config = simulation_config or {}
        self.simulation = None
        self.camera_buffer = self.camera_node = None
        self.camera_frame = None
        self.disableMouse()
        self.setBackgroundColor(0.65, 0.80, 0.95)
        self._create_ground()
        self._create_road()
        self._position_overview()
        self._create_car_visual()
        self._create_panel()
        self._create_debug_pov()
        self.accept('window-event', self._layout)
        self._layout(self.win)
        self.taskMgr.add(self._tick, 'simulation-update')
        self.accept('escape', self._close)

    def set_simulation(self, simulation):
        self.simulation = simulation
        self.update_vehicle_view()

    def _close(self):
        if self.simulation:
            self.simulation.cleanup()
        self.userExit()

    def _tick(self, task):
        if self.simulation:
            self.simulation.advance(self.clock.getDt())
            self.update_vehicle_view()
            self._refresh_panel()
        return task.cont

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

    def _create_panel(self):
        self.panel = DirectFrame(parent=self.pixel2d, frameColor=(0.08, 0.10, 0.12, 1))
        self.info = OnscreenText(parent=self.pixel2d, align=TextNode.ALeft,
                                 fg=(1, 1, 1, 1), mayChange=True)
        self.button = DirectButton(parent=self.pixel2d, text='Start', command=self._start,
                                   relief=1, frameColor=(0.65, 0.7, 0.75, 1))
        self.preview_texture = Texture('camera preview')
        card = CardMaker('camera preview')
        card.setFrame(0, 1, -1, 0)
        self.preview = self.pixel2d.attachNewNode(card.generate())
        self.preview.setTexture(self.preview_texture)
        self.preview.hide()

    def _start(self):
        if self.simulation:
            self.simulation.start()
            self.update_vehicle_view()
            self._refresh_panel()

    def _refresh_panel(self):
        sim = self.simulation
        self.info.setText(f'Speed: {self.car.speed_mps * 3.6:.1f} km/h\nSteering: {self.car.steering_angle_deg:.1f} deg\n{sim.status}' + (f'\n{sim.reason}' if sim.reason else ''))
        self.button['text'] = 'Start' if sim.status == 'READY' else 'Restart'
        self.button['state'] = 'disabled' if sim.status == 'RUNNING' else 'normal'

    def _layout(self, window):
        if window != self.win or not self.win.getXSize() or not self.win.getYSize():
            return
        w, h = self.win.getXSize(), self.win.getYSize()
        self.camNode.getDisplayRegion(0).setDimensions(0, 0.8, 0, 1)
        self.camLens.setAspectRatio(0.8 * w / h)
        x, panel_width = 0.8*w, 0.2*w
        self.panel.setPos(x, 0, 0)
        self.panel['frameSize'] = (0, panel_width, -h, 0)
        margin = panel_width * 0.05
        preview_width = panel_width - 2*margin
        # Both previews have fixed aspect ratios and remain within their panel slots.
        debug_height = min(preview_width * 0.75, h * 0.25)
        debug_width = debug_height / 0.75
        dx = x + (panel_width-debug_width)/2
        top = h*0.03
        self.debug_region.setDimensions(dx/w, (dx+debug_width)/w, 1-(top+debug_height)/h, 1-top/h)
        self.debug_lens.setAspectRatio(4/3)
        cam_top = top + debug_height + h*0.025
        ratio = self.camera_description.width / self.camera_description.height if self.camera_buffer else 4/3
        cam_height = min(preview_width / ratio, h*0.25)
        cam_width = cam_height*ratio
        self.preview.setPos(x+(panel_width-cam_width)/2, 0, -cam_top)
        self.preview.setScale(cam_width, 1, cam_height)
        text_y = cam_top + cam_height + h*0.04
        self.info.setPos(x+margin, -text_y)
        self.info.setScale(min(panel_width*0.065, h*0.027))
        self.info['wordwrap'] = 14
        self.button.setPos(x+panel_width/2, 0, -min(h*0.90, text_y+h*0.20))
        self.button.setScale(min(panel_width*0.09, h*0.035))

    def _create_debug_pov(self):
        settings = self.config.get('debug_pov', {})
        self.debug_region = self.win.makeDisplayRegion(0.8, 1, 0.7, 1)
        self.debug_region.setSort(10)
        self.debug_region.setClearColorActive(True)
        self.debug_region.setClearColor((0.65, 0.80, 0.95, 1))
        self.debug_region.setClearDepthActive(True)
        self.debug_lens = PerspectiveLens()
        self.debug_lens.setFov(settings.get('fov_deg', 75))
        self.debug_lens.setNearFar(0.05, 1500)
        self.pov_camera = self.car_node.attachNewNode(Camera('debug_pov'))
        self.pov_camera.node().setLens(self.debug_lens)
        self.pov_camera.setPos(0, self.car.length_m*0.2, settings.get('height_m', 0.8))
        self.pov_camera.lookAt(self.car_node, 0, self.car.length_m*0.2 + settings.get('lookahead_m', 6), 0.02)
        self.debug_region.setCamera(self.pov_camera)

    def start_camera(self, config):
        self.stop_camera()
        if not config or not config.get('enabled', True):
            return
        self.camera_description = CameraDescription.from_config(config)
        camera = self.camera_description
        lens = PerspectiveLens()
        lens.setFov(*camera.fov_deg)
        lens.setNearFar(0.05, 1500)
        self.camera_buffer = self.win.makeTextureBuffer('physical-camera', camera.width, camera.height, to_ram=True)
        if not self.camera_buffer:
            raise RuntimeError('Unable to create camera buffer')
        self.camera_buffer.setActive(False)
        self.camera_node = self.makeCamera(self.camera_buffer, lens=lens)
        self.camera_node.reparentTo(self.car_node)
        mount = self.config.get('camera_mount', {})
        self.camera_node.setPos(*mount.get('position_m', [0, 0, 0.8]))
        self.camera_node.setHpr(*mount.get('hpr_deg', [0, 0, 0]))
        self.next_capture_s = 0.0
        self.camera_frame = None
        self._layout(self.win)

    def capture_if_due(self, time_s):
        if not self.camera_buffer:
            return None
        if time_s + 1e-10 >= self.next_capture_s:
            # Synchronize the pose to this physics state before rendering the sensor.
            self.update_vehicle_view()
            self.camera_buffer.setActive(True)
            try:
                self.graphicsEngine.renderFrame()
                tex = self.camera_buffer.getTexture()
                raw = tex.getRamImageAs('RGB')
                if not raw:
                    raise RuntimeError('Camera frame unavailable')
                self.camera_frame = np.frombuffer(raw, dtype=np.uint8).reshape(self.camera_description.height, self.camera_description.width, 3)[::-1].copy()
                self.camera_frame.setflags(write=False)
            finally:
                self.camera_buffer.setActive(False)
            # Panda textures use bottom-up rows; preview uses the captured pixels.
            self.preview_texture.setup2dTexture(self.camera_description.width, self.camera_description.height, Texture.TUnsignedByte, Texture.FRgb8)
            self.preview_texture.setRamImageAs(self.camera_frame[::-1].tobytes(), 'RGB')
            self.preview.show()
            self.next_capture_s += self.camera_description.frame_period_s
            if self.next_capture_s <= time_s:
                self.next_capture_s = time_s + self.camera_description.frame_period_s
        return self.camera_frame

    def stop_camera(self):
        if self.camera_node:
            self.camera_node.removeNode()
            self.camera_node = None
        if self.camera_buffer:
            self.graphicsEngine.removeWindow(self.camera_buffer)
            self.camera_buffer = None
        self.camera_frame = None
        if hasattr(self, 'preview'):
            self.preview.hide()
