"""A stationary example; replace with an architecture's own logic."""


class Controller:
    def __init__(self, config, data_dir):
        self.config = config
        self.data_dir = data_dir

    def start(self):
        pass

    def update(self, observation):
        return None

    def stop(self):
        pass
