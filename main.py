from gemini.gemini import Gemini
from gemini.logger import Logger as log
from gemini import config
import pkg_resources
config.IS_SERVICE = False
config.MODE = "TEST"
config.MIN_PROFIT = 0.0001
config.MAX_VOL = config.MIN_VOL

def run():
    distrib = pkg_resources.get_distribution("gemini")
    log.ok("Running %s Gemini version %s" % (config.MODE, distrib.version if distrib else "UNVERSIONED"))
    bot = Gemini(config)
    bot.start()

if __name__ == "__main__":
    run()

