from gemini.keyhandler import KeyHandler
from gemini.cexioapi import CEX
from gemini import config
from gemini.logger import Logger as log
from geminitest import GeminiLiveTest
import unittest, os, asyncio, time
config.IS_SERVICE = False
config.PAIRS = [("ETH","BTC"), ("XRP", "BTC"), ("XVG", "BTC"), ("IOTA", "BTC"), ("TRX", "BTC"), ("NEO", "BTC"), ("DASH", "BTC"), ("EOS", "BTC"),
                        ("XRP", "ETH"), ("XVG", "ETH"), ("IOTA", "ETH"), ("TRX", "ETH"), ("NEO", "ETH"), ("DASH", "ETH"), ("EOS", "ETH")]

class TestMethods(GeminiLiveTest):
    def test_order_book(self):
        loop = asyncio.new_event_loop()
        api = CEX(os.path.join(config.APIKEY_DIR, config.CEX_KEYFILE), loop, [False])
        time.sleep(2)
        self.assertTrue(api is not None)
        log.ok("Connected to CEX: " + str(api))
        for idx in range(10):
            loop.run_until_complete(asyncio.sleep(1))
            book = api.get_depth("XRP","BTC")
            self.assertTrue(len(book['bids']) == 10)
            self.assertTrue(len(book['asks']) == 10)
        api.stop()
        log.ok("CEX order book processed succesfully: %d bids, %d asks" % (len(book['bids']), len(book['asks'])))
        # the lines below are LIVE orders!!!!
        #order = api.submit_order(("XRP","BTC"), "BUY", '0.00009', '100')
        #print(order)
        #ords=api.query_active_orders()
        #ords_raw=api.trade_api.current_orders('XRP/BTC')
        #api.cancel_orders(ords)
        #print(api.query_active_orders())

    def test_ticker(self):
        api = CEX(os.path.join(config.APIKEY_DIR, config.CEX_KEYFILE), asyncio.new_event_loop(), [False])
        tickers = api.get_ticker()
        log.ok(tickers)

    def test_balance(self):
        api = CEX(os.path.join(config.APIKEY_DIR, config.CEX_KEYFILE), asyncio.new_event_loop(), [False])
        bal = api.get_all_balances()
        log.ok(bal)

    def test_active_orders(self):
        api = CEX(os.path.join(config.APIKEY_DIR, config.CEX_KEYFILE), asyncio.new_event_loop(), [False])
        ord = api.query_active_orders()
        log.ok(ord)
        # the lines below are LIVE orders!!!!
        #order = api.submit_order(("XRP","BTC"), "BUY", 0.00009, 100)
        #print(order)
        #time.sleep(1)
        #print(api.query_active_orders())
        #time.sleep(1)
        #api.cancel_orders()
        #time.sleep(1)
        #print(api.query_active_orders())

if __name__ == "__main__":
    unittest.main()