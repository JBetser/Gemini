# Top classes for the Gemini scheduler, Live and Simulation modes

from .scheduler import Scheduler
from .logger import Logger as log
from .controller import ControllerSimulator

class LiveBot(Scheduler):
    def __init__(self, config):
        super(LiveBot, self).__init__(config, "LIVE")

class DummyBot(Scheduler):
    def __init__(self, config):
        super(DummyBot, self).__init__(config, "DUMMY")

    def create_exchanges(self):
        controllers = super(DummyBot, self).create_exchanges()
        return [ControllerSimulator(controller.xchg) for controller in controllers]

class Gemini:
    def __init__(self, config):
        if config.MODE == "LIVE":
            self.scheduler = LiveBot(config)
        else:
            self.scheduler = DummyBot(config)

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.stop()
