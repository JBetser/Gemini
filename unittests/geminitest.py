from gemini import config
from gemini.config import setDefaultConfig
import unittest

class GeminiTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(GeminiTest, self).__init__(*args, **kwargs)
        setDefaultConfig()

    def run(self, result=None):
        setDefaultConfig()
        try:
            super(GeminiTest, self).run(result)
        finally:
            setDefaultConfig()

class GeminiLiveTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(GeminiLiveTest, self).__init__(*args, **kwargs)
        setDefaultConfig()
        config.MODE = 'LIVE'

    def run(self, result=None):
        setDefaultConfig()
        config.MODE = 'LIVE'
        try:
            super(GeminiLiveTest, self).run(result)
        finally:
            setDefaultConfig()
            config.MODE = 'LIVE'