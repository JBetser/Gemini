from gemini.binanceapi import Binance
from gemini.logger import Logger as log
from gemini import config
from geminitest import GeminiLiveTest
import unittest, os, asyncio, time
config.IS_SERVICE = False
config.PAIRS = [("ETH","BTC"), ("XRP", "BTC"), ("XVG", "BTC"), ("IOTA", "BTC"), ("TRX", "BTC"), ("NEO", "BTC"), ("DASH", "BTC"), ("EOS", "BTC"),
                        ("XRP", "ETH"), ("XVG", "ETH"), ("IOTA", "ETH"), ("TRX", "ETH"), ("NEO", "ETH"), ("DASH", "ETH"), ("EOS", "ETH")]

class TestMethods(GeminiLiveTest):
    def test_order_book(self):
        api = Binance(os.path.join(config.APIKEY_DIR, config.BINANCE_KEYFILE), asyncio.new_event_loop(), [False])
        time.sleep(5)
        self.assertTrue(api is not None)
        log.ok("Connected to Binance: " + str(api))
        for idx in range(10):
            book = api.get_depth("XRP","BTC")
            self.assertTrue(len(book['bids']) == 10)
            self.assertTrue(len(book['asks']) == 10)
            log.info("Highest bid: %.4g, Lowest ask: %.4g" % (book['bids'][0].p,book['asks'][0].p))
        log.ok("Binance order book processed succesfully: %d bids, %d asks" % (len(book['bids']), len(book['asks'])))

        # the lines below are LIVE orders!!!!
        #order = api.submit_order(("XRP","BTC"), "BUY", '0.00009', '100')
        #print(order)
        #ords=api.query_active_orders()
        #api.cancel_orders(ords)
        #order = api.submit_order(("XRP","BTC"), "BUY", '0.00009', '100')
        #print(api.query_active_orders())

    def test_ticker(self):
        api = Binance(os.path.join(config.APIKEY_DIR, config.BINANCE_KEYFILE), asyncio.new_event_loop(), [False])
        tickers = api.get_ticker()
        log.ok(tickers)

    def test_balance(self):
        api = Binance(os.path.join(config.APIKEY_DIR, config.BINANCE_KEYFILE), asyncio.new_event_loop(), [False])
        bal = api.get_all_balances()
        log.ok(bal)

    def test_active_orders(self):
        api = Binance(os.path.join(config.APIKEY_DIR, config.BINANCE_KEYFILE), asyncio.new_event_loop(), [False])
        ord = api.query_active_orders()
        log.ok(ord)


if __name__ == "__main__":
    unittest.main()