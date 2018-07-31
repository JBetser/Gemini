from gemini.bitfinexapi import Bitfinex
from gemini.bitfinex.client import BtfxWss
from gemini.bitfinex.trade_client import Client, TradeClient
from gemini.exchange import DummyExchange
from gemini.controller import ControllerTest
from gemini.order import Order
from gemini.keyhandler import KeyHandler
from gemini.logger import Logger as log
from gemini import config
from geminitest import GeminiLiveTest
import unittest, os, time, asyncio
config.IS_SERVICE = False
config.PAIRS = [("ETH","BTC"), ("XRP", "BTC"), ("XVG", "BTC"), ("IOTA", "BTC"), ("TRX", "BTC"), ("NEO", "BTC"), ("DASH", "BTC"), ("EOS", "BTC"),
                        ("XRP", "ETH"), ("XVG", "ETH"), ("IOTA", "ETH"), ("TRX", "ETH"), ("NEO", "ETH"), ("DASH", "ETH"), ("EOS", "ETH")]

class DummyBitfinexExchange(Bitfinex):
    def __init__(self, test_case, expected_orders):
        super(DummyBitfinexExchange, self).__init__(os.path.abspath(os.path.join(config.APIKEY_DIR, config.BITFINEX_KEYFILE)), asyncio.new_event_loop(), [False])
        self.test_case = test_case
        self.set_expected_orders(expected_orders)

    def submit_order(self, pair, side, price, volume):
        self.test_case.assertEqual(self.expected_orders[self.count], (pair, side, price, volume))
        neword = Order(orderID='DUMMYORD' + str(len(self.orders)), price=price, volume=float(volume)*0.5, type=side, pair=pair)
        self.orders.append(neword)
        self.count += 1
        return neword

    def cancel_orders(self, orders):
        return orders

    def query_active_orders(self):
        orders=[]
        for order in self.orders:
            pair=self.pair_from_symbol(Bitfinex.mapping(order.pair))
            orders.append(Order(order.p,order.v,order.type,pair,order.id))
        return orders

    def set_expected_orders(self, expected_orders):
        self.expected_orders = expected_orders
        self.count = 0
        self.orders = []

class TestMethods(GeminiLiveTest):
    def __init__(self, *args, **kwargs):
        super(TestMethods, self).__init__(*args, **kwargs)
        self.bitfinex = DummyBitfinexExchange(self, [])
        self.assertTrue(self.bitfinex is not None)
        log.ok("Connected to Bitfinex: " + str(self.bitfinex))

    def test_order_book(self):
        keyhandler = KeyHandler(os.path.join(config.APIKEY_DIR, "bitfinex_key.txt"))
        key = list(keyhandler.getKeys())[0]
        secret = keyhandler.getSecret(key)
        public_api = Client()
        self.assertTrue(public_api is not None)
        log.ok(public_api)
        trade_api = TradeClient(key, secret)
        self.assertTrue(trade_api is not None)
        log.ok(trade_api)
        book = public_api.order_book("xrpbtc", {'limit_asks': 10, 'limit_bids': 10})
        self.assertTrue(len(book['bids']) == 10)
        self.assertTrue(len(book['asks']) == 10)
        log.ok(book)

    def test_ticker(self):
        api = self.bitfinex
        tickers = api.get_ticker()
        log.ok(tickers)

    def test_api(self):
        api = self.bitfinex
        time.sleep(5)
        for idx in range(10):
            book = api.get_depth("XRP","BTC")
            self.assertTrue(len(book['bids']) > 10)
            self.assertTrue(len(book['asks']) > 10)
            book = api.get_depth("IOTA","BTC")
            self.assertTrue(len(book['bids']) > 10)
            self.assertTrue(len(book['asks']) > 10)
            book = api.get_depth("DASH","BTC")
            self.assertTrue(len(book['bids']) > 10)
            self.assertTrue(len(book['asks']) > 10)
            log.info("Highest bid: %.4g, Lowest ask: %.4g" % (book['bids'][0].p,book['asks'][0].p))
        log.ok("Bitfinex order book processed succesfully: %d bids, %d asks" % (len(book['bids']), len(book['asks'])))

        # the lines below are LIVE orders!!!!
        #order = api.submit_order(("XRP","BTC"), "BUY", '0.00009', '100')
        #print(order)
        #acts=api.query_active_orders()
        #canc=api.cancel_orders([order])
        #print(api.query_active_orders())

    def test_balance(self):
        api = self.bitfinex
        bal = api.get_all_balances()
        log.ok(bal)

    def test_active_orders(self):
        api = self.bitfinex
        ord = api.query_active_orders()
        log.ok(ord)
        # the lines below are LIVE orders!!!!
        #order = api.submit_order(("XRP","BTC"), "BUY", '0.00009', '100')
        #print(order)
        #ords=api.query_active_orders()
        #ords_raw=api.trade_api.active_orders()
        #api.cancel_orders(ords)
        #print(api.query_active_orders())

    def test_price_update(self):
        # check that the price update works for both 3 letter ccy and the mapped 4 letter -> 3 letter ccies
        # 3 letter ccy
        expected_orders = [(('NEO','BTC'), 'BUY', '0.00000756', '19000'),
                            (('NEO','BTC'), 'BUY', '0.000008', '9500.00')]
        dummy_bitfinex = self.bitfinex
        dummy_bitfinex.set_expected_orders(expected_orders)
        controller = ControllerTest(dummy_bitfinex,
                                        {"BTC": 0.17053, "NEO": 20000},
                                        {"NEO_BTC":{"bids":[Order(0.00000775, 10000)],"asks":[Order(0.00000776, 20000)]}})
        controller.submit_order(('NEO','BTC'), 'BUY', '0.00000756', '19000')
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(dummy_bitfinex.count, 1)
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(dummy_bitfinex.count, 2)

        # 4 letter ccy
        expected_orders = [(('IOTA','BTC'), 'BUY', '0.00000756', '19000'),
                            (('IOTA','BTC'), 'BUY', '0.00000775', '9500.00')]
        dummy_bitfinex.set_expected_orders(expected_orders)
        controller = ControllerTest(dummy_bitfinex,
                                        {"BTC": 0.17053, "IOTA": 20000},
                                        {"IOTA_BTC":{"bids":[Order(0.00000775, 10000)],"asks":[Order(0.00000776, 20000)]}})
        controller.submit_order(('IOTA','BTC'), 'BUY', '0.00000756', '19000')
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(dummy_bitfinex.count, 1)
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(dummy_bitfinex.count, 2)

if __name__ == "__main__":
    unittest.main()