from gemini.gemini import Gemini, DummyBot
import asyncio, threading
from gemini import config
from gemini.controller import ControllerTest
from gemini.exchange import DummyExchange
from gemini.logger import Logger as log
from geminitest import GeminiTest
import unittest, os, asyncio

class TestMethods(GeminiTest):
    def test_trading(self):
        # no funds
        xchg_ask = ControllerTest(DummyExchange("FOO1"))
        xchg_bid = ControllerTest(DummyExchange("FOO2"))
        xchg_ask.async_submit_order(asyncio.new_event_loop(), [False], ("XVG","BTC"), "BUY", 1.0, 1510.0)
        xchg_bid.async_submit_order(asyncio.new_event_loop(), [False], ("XVG","BTC"), "SELL", 1.0, 1510.0)
        self.assertEqual(len(xchg_ask.orders), 0)
        self.assertEqual(len(xchg_bid.orders), 0)

        # bad format
        xchg_ask = ControllerTest(DummyExchange("FOO1", {"BTC": 0.17053, "XVG": 0.0}))
        xchg_bid = ControllerTest(DummyExchange("FOO2", {"BTC": 0.0, "XVG": 20.0}))
        xchg_ask.async_submit_order(asyncio.new_event_loop(), [False], ("xvg","btc"), "BUY", 0.01, 1510.0)
        xchg_bid.async_submit_order(asyncio.new_event_loop(), [False], ("xvg","btc"), "SELL", 0.01, 1510.0)
        self.assertEqual(len(xchg_ask.orders), 0)
        self.assertEqual(len(xchg_bid.orders), 0)

        # valid orders
        xchg_ask = ControllerTest(DummyExchange("FOO1", {"BTC": 0.17053, "XVG": 0.0}))
        xchg_bid = ControllerTest(DummyExchange("FOO2", {"BTC": 0.0, "XVG": 20.0}))
        xchg_ask.async_submit_order(asyncio.new_event_loop(), [False], ("XVG","BTC"), "BUY", 0.01, 1510.0)
        xchg_bid.async_submit_order(asyncio.new_event_loop(), [False], ("XVG","BTC"), "SELL", 0.01, 1510.0)
        self.assertEqual(len(xchg_ask.orders), 1)
        self.assertEqual(len(xchg_bid.orders), 1)
        self.assertEqual(xchg_ask.orders['DUMMYORD0'].p, 0.01)
        self.assertEqual(xchg_bid.orders['DUMMYORD0'].p, 0.01)
        self.assertEqual(xchg_ask.orders['DUMMYORD0'].v, 1000.0)
        self.assertEqual(xchg_bid.orders['DUMMYORD0'].v, 1000.0)

if __name__ == "__main__":
    unittest.main()