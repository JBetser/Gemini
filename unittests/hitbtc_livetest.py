from gemini.keyhandler import KeyHandler
from gemini.hitbtcapi import Hitbtc
from gemini import config
from gemini.logger import Logger as log
from geminitest import GeminiLiveTest
import time, queue
import unittest, os, asyncio, time
config.IS_SERVICE = False
config.PAIRS = [("ETH","BTC"), ("XRP", "BTC"), ("XVG", "BTC"), ("IOTA", "BTC"), ("TRX", "BTC"), ("NEO", "BTC"), ("DASH", "BTC"), ("EOS", "BTC"),
                        ("XRP", "ETH"), ("XVG", "ETH"), ("IOTA", "ETH"), ("TRX", "ETH"), ("NEO", "ETH"), ("DASH", "ETH"), ("EOS", "ETH")]

class TestMethods(GeminiLiveTest):

    def test_order_book(self):
        api = Hitbtc(os.path.join(config.APIKEY_DIR, config.HITBTC_KEYFILE), asyncio.new_event_loop(), [False])
        time.sleep(5)
        self.assertTrue(api is not None)
        log.ok(api)
        time.sleep(5)
        bal = api.get_all_balances()
        log.ok(bal)
        ord = api.query_active_orders()
        log.ok(ord)
        time.sleep(15)
        for idx in range(10):
            book = api.get_depth("XRP","BTC")
            self.assertTrue(len(book['bids']) == 10)
            self.assertTrue(len(book['asks']) == 10)
            log.info("Highest bid: %.4g, Lowest ask: %.4g" % (book['bids'][0].p,book['asks'][0].p))
        log.ok("Hitbtc order book processed succesfully: %d bids, %d asks" % (len(book['bids']), len(book['asks'])))
        api.stop()
        # the lines below are LIVE orders!!!! TODO: Fix the rounding before seding to BTC, as they always take the floor
        #order = api.submit_order(("XRP","BTC"), "BUY", '0.00009', '100')
        #print(order)
        #print(api.query_active_orders())
        #time.sleep(10)
        #api.cancel_orders([order])
        #print(api.query_active_orders())

    def test_ticker(self):
        api = Hitbtc(os.path.join(config.APIKEY_DIR, config.HITBTC_KEYFILE), asyncio.new_event_loop(), [False])
        tickers = api.get_ticker()
        log.ok(tickers)

if __name__ == "__main__":
    unittest.main()