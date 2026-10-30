
from direct.showbase.ShowBase import ShowBase
from panda3d.core import CardMaker


class GTRWorld(ShowBase):
    def __init__(self):
        super().__init__()

        # Sky
        self.setBackgroundColor(0.65, 0.80, 0.95)

        # Ground (20 x 20 meters)
        ground = CardMaker("ground")
        ground.setFrame(-10, 10, -10, 10)

        ground_node = self.render.attachNewNode(ground.generate())
        ground_node.setP(-90)
        ground_node.setColor(0.25, 0.50, 0.25)

        # Camera position
        self.disableMouse()
        self.camera.setPos(0, -18, 10)
        self.camera.lookAt(0, 0, 0)


if __name__ == "__main__":
    app = GTRWorld()
    app.run()
