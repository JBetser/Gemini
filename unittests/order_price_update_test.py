from gemini.profit_calculator import ProfitCalculator
from gemini.order import Order
from gemini.controller import ControllerTest
from gemini.exchange import DummyExchange
from gemini import config
from geminitest import GeminiTest
from copy import deepcopy
import unittest, asyncio

class DummyExchangePriceUpdate(DummyExchange):
    def __init__(self, name, scaling_factor = 0.5):
        super(DummyExchangePriceUpdate, self).__init__(name)
        self._scaling_factor = scaling_factor

    def query_active_orders(self):
        # partially filled trades
        return [Order(orderID=order.id, price=order.p, volume=self._scaling_factor * order.v, type=order.type, pair=order.pair) for order in self.orders]

class BrokerTestPriceUpdate(ControllerTest):
    def __init__(self, exchg, balances, depth, test_case, expected_orders):
        super(BrokerTestPriceUpdate, self).__init__(exchg, balances, depth)
        self.test_case = test_case
        self.expected_orders = expected_orders
        self.count = 0

    def submit_order(self, pair, side, price, volume):
        self.test_case.assertEqual(self.expected_orders[self.count], (pair, side, price, volume))
        ord = super(BrokerTestPriceUpdate, self).submit_order(pair, side, price, volume)
        if ord is not None:
            self.count += 1
        return ord

class TestOrderPriceUpdate(GeminiTest):
    def __init__(self, *args, **kwargs):
        super(TestOrderPriceUpdate, self).__init__(*args, **kwargs)

    def test_price_update(self):
        expected_orders = [(('XVG','BTC'), 'BUY', '0.00000756', '19000'),
                            (('XVG','BTC'), 'BUY', '0.00000775', '9000.00')]
        controller = BrokerTestPriceUpdate(DummyExchangePriceUpdate("TEST1"),
                                        {"BTC": 0.17053, "XVG": 20000},
                                        {"XVG_BTC":{"bids":[Order(0.00000775, 10000)],"asks":[Order(0.00000776, 20000)]}},
                                        self,
                                        expected_orders)
        controller.submit_order(('XVG','BTC'), 'BUY', '0.00000756', '19000')
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 1)
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 2)

    def test_volume_update(self):
        expected_orders = [(('XVG','BTC'), 'BUY', '0.00000756', '19000'),
                            (('XVG','BTC'), 'BUY', '0.00000876', '8000.00')]
        controller = BrokerTestPriceUpdate(DummyExchangePriceUpdate("TEST1"),
                                        {"BTC": 0.1438, "XVG": 20000},
                                        {"XVG_BTC":{"bids":[Order(0.00000875, 10000)],"asks":[Order(0.00000876, 20000)]}},
                                        self,
                                        expected_orders)
        controller.submit_order(('XVG','BTC'), 'BUY', '0.00000756', '19000')
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 1)
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 2)

    def test_price_update_chain(self):
        # one-sided sell as XVG keeps rocketing up and we are broke, from a shortfall of 9500XVG price update saves 4000+1000XVG
        # we end up losing over 4000XVG
        expected_orders = [(('XVG','BTC'), 'BUY', '0.00000756', '19000'),
                            (('XVG','BTC'), 'BUY', '0.00000876', '8000.00'),
                            (('XVG','BTC'), 'BUY', '0.00001876', '1000.00')]
        order_book = {"XVG_BTC":{"bids":[Order(0.00000875, 10000)],"asks":[Order(0.00000876, 20000)]}}
        controller = BrokerTestPriceUpdate(DummyExchangePriceUpdate("TEST1"),
                                        {"BTC": 19000 * 0.00000756 * 1.001, "XVG": 0.0},
                                        order_book,
                                        self,
                                        expected_orders)
        controller.submit_order(('XVG','BTC'), 'BUY', '0.00000756', '19000')
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 1)
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 2)
        order_book["XVG_BTC"] = {"bids":[Order(0.00001875, 10000)],"asks":[Order(0.00001877, 20000)]}
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 2)
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 3)

        # same situation, except that we are BTC rich. so we can save the XVG, and take the loss in BTC
        # we still get a 1000XVG shortfall because of the 2 * 500XVG roundings
        expected_orders = [(('XVG','BTC'), 'BUY', '0.00000756', '19000'),
                            (('XVG','BTC'), 'BUY', '0.00000876', '9000.00'),
                            (('XVG','BTC'), 'BUY', '0.00001876', '4000.00')]
        order_book = {"XVG_BTC":{"bids":[Order(0.00000875, 10000)],"asks":[Order(0.00000876, 20000)]}}
        controller = BrokerTestPriceUpdate(DummyExchangePriceUpdate("TEST1"),
                                        {"BTC": 1.0, "XVG": 20000},
                                        order_book,
                                        self,
                                        expected_orders)
        controller.submit_order(('XVG','BTC'), 'BUY', '0.00000756', '19000')
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 1)
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 2)
        order_book["XVG_BTC"] = {"bids":[Order(0.00001875, 10000)],"asks":[Order(0.00001877, 20000)]}
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 2)
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 3)

        expected_orders = [(('IOTA','BTC'), 'BUY', '0.0001486225', '781.00'),
                            (('IOTA','BTC'), 'BUY', '0.00014960', '775.00')]
        order_book = {"IOTA_BTC":{"bids":[Order(0.00014861, 1000)],"asks":[Order(0.0001486225, 1000)]}}
        controller = BrokerTestPriceUpdate(DummyExchangePriceUpdate("TEST1", 1.0),
                                        {"BTC": 0.11633054, "IOTA": 0},
                                        order_book,
                                        self,
                                        expected_orders)
        controller.submit_order(('IOTA','BTC'), 'BUY', '0.0001486225', '781.00')
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 1)
        order_book["IOTA_BTC"] = {"bids":[Order(0.000149, 1000)],"asks":[Order(0.0001502, 1000)]}
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 1)

    def test_offline_balances(self):
        expected_orders = [(('XVG','BTC'), 'BUY', '0.00000756', '19000'),
                            (('XVG','BTC'), 'BUY', '0.00000775', '9000.00'),
                            (('XVG','BTC'), 'BUY', '0.00000756', '19000')]
        controller = BrokerTestPriceUpdate(DummyExchangePriceUpdate("TEST1"),
                                        {"BTC": 0.17053, "XVG": 20000},
                                        {"XVG_BTC":{"bids":[Order(0.00000775, 10000)],"asks":[Order(0.00000776, 20000)]}},
                                        self,
                                        expected_orders)
        controller.submit_order(('XVG','BTC'), 'BUY', '0.00000756', '19000')
        self.assertEqual(controller.offline_balances, {'BTC': 0.026602719999999996, 'XVG': 39000.0})
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 1)
        self.assertEqual(controller.offline_balances, {'BTC': 0.09856635999999999, 'XVG': 29500.0})
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.count, 2)
        self.assertEqual(controller.offline_balances, {'BTC': 0.028676859999999985, 'XVG': 38500.0})
        controller.submit_order(('XVG','BTC'), 'BUY', '0.00000756', '19000')
        self.assertEqual(controller.offline_balances, {'BTC': -0.11525042, 'XVG': 57500.0})
        controller.query_active_orders(asyncio.new_event_loop(), [False])
        self.assertEqual(controller.offline_balances, {'BTC': -0.04328678000000001, 'XVG': 48000.0})
        self.assertEqual(controller.count, 3)

if __name__ == "__main__":
    unittest.main()
