from gemini.keyhandler import KeyHandler
from gemini.bittrexapi import Bittrex
from gemini import config
from gemini.logger import Logger as log
from geminitest import GeminiLiveTest
import time, queue
import unittest, os, asyncio, time

class TestMethods(GeminiLiveTest):

    def test_order_book(self):
        api = Bittrex(os.path.join(config.APIKEY_DIR, config.BITTREX_KEYFILE), asyncio.new_event_loop(), [False])
        time.sleep(2)
        self.assertTrue(api is not None)
        log.ok(api)
        tickers = api.get_ticker()
        log.ok(tickers)
        bal = api.get_all_balances()
        log.ok(bal)
        ord = api.query_active_orders()
        log.ok(ord)
        time.sleep(2)
        for idx in range(10):
            book = api.get_depth("XRP","BTC")
            log.info("Highest bid: %.4g, Lowest ask: %.4g" % (book['bids'][0].p,book['asks'][0].p))
        self.assertTrue(len(book['bids']) >= 1)
        self.assertTrue(len(book['asks']) >= 1)
        log.ok("Bittrex order book processed succesfully")
        api.stop()
        # the lines below are LIVE orders!!!!
##        order = api.submit_order(("XRP","BTC"), "SELL", '0.00009', '100')
##        print(order)
##        print(api.query_active_orders())
##        time.sleep(10)
##        api.cancel_orders([order])
##        print(api.query_active_orders())

if __name__ == "__main__":
    unittest.main()