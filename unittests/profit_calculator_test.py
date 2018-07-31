from gemini.profit_calculator import ProfitCalculator
from gemini.order import Order
from gemini.controller import ControllerTest
from gemini.exchange import DummyExchange
from gemini import config
from geminitest import GeminiTest
import unittest

class TestMethods(GeminiTest):
    def __init__(self, *args, **kwargs):
        super(TestMethods, self).__init__(*args, **kwargs)

    def test_profit_calc(self):
        config.MAX_BIDASK_SPREAD_PCT['DEFAULT']['BTC'] = 1.0
        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.17053, "XRP": 2000}, {"XRP_BTC":{"bids":[Order(0.000105, 5000)],"asks":[Order(0.0001055714286, 6000)]}})
        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.25, "XRP": 2000}, {"XRP_BTC":{"bids":[Order(0.000108428571, 1650)],"asks":[Order(0.000109, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XRP", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['rebalancing'], False)
        self.assertEqual(profit_obj['profit'], 0.003891082841596217)
        self.assertEqual(profit_obj['profit_pct'], 2.2920925914551407)
        self.assertEqual(profit_obj['bidder_order'].p, 0.00010842714242879999)
        self.assertEqual(profit_obj['bidder_order'].v, 1604.0)
        self.assertEqual(profit_obj['asker_order'].p, 0.0001055728571712)
        self.assertEqual(profit_obj['asker_order'].v, 1608.0)
        self.assertTrue(profit_obj['asker_order'].p * profit_obj['asker_order'].v < 0.17053)

        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.17053, "XRP": 1600}, {"XRP_BTC":{"bids":[Order(0.000105, 5000)],"asks":[Order(0.0001055714286, 6000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XRP", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['profit'], 0.003891082841596217)
        self.assertEqual(profit_obj['profit_pct'], 2.2920925914551407)
        self.assertEqual(profit_obj['bidder_order'].p, 0.00010842714242879999)
        self.assertEqual(profit_obj['bidder_order'].v, 1604.0)
        self.assertEqual(profit_obj['asker_order'].p, 0.0001055728571712)
        self.assertEqual(profit_obj['asker_order'].v, 1608.0)
        self.assertTrue(profit_obj['asker_order'].p * profit_obj['asker_order'].v < 0.17053)

        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.25, "XRP": 1600}, {"XRP_BTC":{"bids":[Order(0.000108428571, 1650)],"asks":[Order(0.000109, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XRP", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['profit'], 0.0038643983582685617)
        self.assertEqual(profit_obj['profit_pct'], 2.293489344107763)
        self.assertEqual(profit_obj['bidder_order'].p, 0.00010842714242879999)
        self.assertEqual(profit_obj['bidder_order'].v, 1593.0)
        self.assertEqual(profit_obj['asker_order'].p, 0.0001055728571712)
        self.assertEqual(profit_obj['asker_order'].v, 1596.0)
        self.assertTrue(profit_obj['asker_order'].p * profit_obj['asker_order'].v < 0.17053)

        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.16553, "XRP": 1600}, {"XRP_BTC":{"bids":[Order(0.000105, 5000)],"asks":[Order(0.0001055714286, 6000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XRP", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['profit'], 0.00377706732192351)
        self.assertEqual(profit_obj['profit_pct'], 2.2933896705161025)
        self.assertEqual(profit_obj['bidder_order'].p, 0.00010842714242879999)
        self.assertEqual(profit_obj['bidder_order'].v, 1557.0)
        self.assertEqual(profit_obj['asker_order'].p, 0.0001055728571712)
        self.assertEqual(profit_obj['asker_order'].v, 1560.0)
        self.assertTrue(profit_obj['asker_order'].p * profit_obj['asker_order'].v < 0.16553)

        config.MAX_VOL['XRP'] = 2000
        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.46553, "XRP": 3000}, {"XRP_BTC":{"bids":[Order(0.000105, 5000)],"asks":[Order(0.0001055714286, 6000)]}})
        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.75, "XRP": 4000}, {"XRP_BTC":{"bids":[Order(0.000108428571, 3650)],"asks":[Order(0.000109, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XRP", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['profit'], 0.004849298379271096)
        self.assertEqual(profit_obj['profit_pct'], 2.293219799114506)
        self.assertEqual(profit_obj['bidder_order'].p, 0.00010842714242879999)
        self.assertEqual(profit_obj['bidder_order'].v, 1999.0)
        self.assertEqual(profit_obj['asker_order'].p, 0.0001055728571712)
        self.assertEqual(profit_obj['asker_order'].v, 2003.0)
        self.assertTrue(profit_obj['asker_order'].p * profit_obj['asker_order'].v < 0.46553)

    def test_max_vol(self):
        config.MAX_VOL = {
             'BTC':0.2,
             'XRP':1000,
             'DASH':3
             }
        config.MAX_BIDASK_SPREAD_PCT['DEFAULT']['BTC'] = 1.0
        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.17053, "XRP": 2000, "ETH": 1.7}, {"XRP_BTC":{"bids":[Order(0.000105, 5000)],"asks":[Order(0.0001055714286, 6000)]},
                                                                                "XRP_ETH":{"bids":[Order(0.00105, 5000)],"asks":[Order(0.001055714286, 6000)]}})
        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.25, "XRP": 2000, "ETH": 2.5}, {"XRP_BTC":{"bids":[Order(0.000108428571, 1650)],"asks":[Order(0.000109, 4000)]},
                                                                            "XRP_ETH":{"bids":[Order(0.00108428571, 1650)],"asks":[Order(0.00109, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XRP", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['profit'], 0.0024234362585752)
        self.assertEqual(profit_obj['profit_pct'], 2.293217507039598)
        self.assertEqual(profit_obj['bidder_order'].p, 0.00010842714242879999)
        self.assertEqual(profit_obj['bidder_order'].v, 999.0)
        self.assertEqual(profit_obj['asker_order'].p, 0.0001055728571712)
        self.assertEqual(profit_obj['asker_order'].v, 1001.0)
        self.assertTrue(profit_obj['asker_order'].p * profit_obj['asker_order'].v < 0.17053)

        pc = ProfitCalculator([controller1, controller2], ("XRP", "ETH"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['profit'], 0.024234362585751835)
        self.assertEqual(profit_obj['profit_pct'], 2.293217507039582)
        self.assertEqual(profit_obj['bidder_order'].p, 0.0010842714242879998)
        self.assertEqual(profit_obj['bidder_order'].v, 999.0)
        self.assertEqual(profit_obj['asker_order'].p, 0.0010557285717120001)
        self.assertEqual(profit_obj['asker_order'].v, 1001.0)

        config.MAX_BIDASK_SPREAD_PCT['DEFAULT']['ETH'] = 0.2
        pc = ProfitCalculator([controller1, controller2], ("XRP", "ETH"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertNotEqual(profit_obj, None)

    def test_price_rounding(self):
        config.MAX_VOL = {
             'BTC':0.2,
             'XRP':1000,
             'ETH':3.0,
             'DASH':3,
             'XVG':10000
             }
        config.MAX_BIDASK_SPREAD_PCT['DEFAULT']['BTC'] = 1.0
        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.17053, "ETH": 2}, {"ETH_BTC":{"bids":[Order(0.105, 5)],"asks":[Order(0.1055714286, 6)]}})
        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.25, "ETH": 2}, {"ETH_BTC":{"bids":[Order(0.108428571, 1.65)],"asks":[Order(0.109, 4)]}})
        pc = ProfitCalculator([controller1, controller2], ("ETH", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(controller1.format_price(("ETH", "BTC"), profit_obj['bidder_order'].p), '0.108427')
        self.assertEqual(controller2.format_price(("ETH", "BTC"), profit_obj['asker_order'].p), '0.105573')
        self.assertEqual(controller1.format_volume(("ETH", "BTC"), profit_obj['bidder_order'].v), '1.604')
        self.assertEqual(controller2.format_volume(("ETH", "BTC"), profit_obj['asker_order'].v), '1.608')

        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.37, "XRP": 1257.75}, {"XRP_BTC":{"bids":[Order(0.00105, 5000)],"asks":[Order(0.001055714286, 6000)]}})
        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.25, "XRP": 1258.37}, {"XRP_BTC":{"bids":[Order(0.00108828571, 1650)],"asks":[Order(0.00109, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XRP", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['bidder_order'].p, 0.001088269424288)
        self.assertEqual(profit_obj['asker_order'].p, 0.0010557305717120002)
        self.assertEqual(controller1.format_volume(("XRP", "BTC"), profit_obj['bidder_order'].v), '349.00')
        self.assertEqual(controller2.format_volume(("XRP", "BTC"), profit_obj['asker_order'].v), '349.00')

        controller1 = ControllerTest(DummyExchange("TEST1"), {"ETH": 1.17053, "DASH": 2}, {"DASH_ETH":{"bids":[Order(0.7105, 5)],"asks":[Order(0.71055714286, 6)]}})
        controller2 = ControllerTest(DummyExchange("BINANCE"), {"ETH": 1.25, "DASH": 2}, {"DASH_ETH":{"bids":[Order(0.7412428571, 1.65)],"asks":[Order(0.741243, 4)]}})
        pc = ProfitCalculator([controller1, controller2], ("DASH", "ETH"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(controller1.format_price(("DASH", "ETH"), profit_obj['bidder_order'].p), '0.741228')
        self.assertEqual(controller2.format_price(("DASH", "ETH"), profit_obj['asker_order'].p), '0.71057')
        self.assertEqual(controller1.format_volume(("DASH", "ETH"), profit_obj['bidder_order'].v), '1.62')
        self.assertEqual(controller2.format_volume(("DASH", "ETH"), profit_obj['asker_order'].v), '1.63')

        # too poor to trade test
        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.13183, "XVG": 3500}, {"XVG_BTC":{"bids":[Order(0.0000105, 5000)],"asks":[Order(0.00001055714286, 6000)]}})
        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.75, "XVG": 2900}, {"XVG_BTC":{"bids":[Order(0.0000108428571, 8000)],"asks":[Order(0.0000109, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XVG", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj, None)

        # 2 important tests. the balances should never be negative
        config.MIN_VOL["XVG"] = 2000
        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.13183, "XVG": 3500}, {"XVG_BTC":{"bids":[Order(0.0000105, 5000)],"asks":[Order(0.00001055714286, 6000)]}})
        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.75, "XVG": 3900}, {"XVG_BTC":{"bids":[Order(0.0000108428571, 8000)],"asks":[Order(0.0000109, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XVG", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertTrue(profit_obj['bidder_order'].v < controller2.balances['XVG'])
        self.assertTrue(profit_obj['asker_order'].v * profit_obj['asker_order'].p * (1.0 + controller1.xchg.trading_fee) < controller1.balances['BTC'])
        self.assertEqual(profit_obj['profit'], 0.0007277586362087727)
        self.assertEqual(profit_obj['profit_pct'], 2.29780853307973)
        self.assertEqual(profit_obj['bidder_order'].p, 1.084271424288e-05)
        self.assertEqual(profit_obj['bidder_order'].v, 3000.0)
        self.assertEqual(profit_obj['asker_order'].p, 1.055728571712e-05)
        self.assertEqual(profit_obj['asker_order'].v, 3000.0)

    def test_usdt_rounding(self):
        bittrex = DummyExchange("TEST1")
        bittrex.trading_fee = 0.0025
        binance = DummyExchange("TEST2")
        binance.trading_fee = 0.001
        controller1 = ControllerTest(bittrex, {"USDT": 142.28802552, "NEO": 0}, {"NEO_USDT":{"bids":[Order(63, 5000)],"asks":[Order(64.02374, 6000)]}})
        controller2 = ControllerTest(binance, {"USDT": 0, "NEO": 2.22}, {"NEO_USDT":{"bids":[Order(64.34625, 8000)],"asks":[Order(65, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("NEO", "USDT"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertEqual(profit_obj['profit'], 0.20742045616904434)
        self.assertEqual(profit_obj['profit_pct'], 0.15138947316240772)
        self.assertEqual(profit_obj['bidder_order'].p, 64.346088745)
        self.assertEqual(profit_obj['bidder_order'].v, 2.13)
        self.assertEqual(profit_obj['asker_order'].p, 64.023901255)
        self.assertEqual(profit_obj['asker_order'].v, 2.14)

    def test_max_bidask_spread(self):
        controller1 = ControllerTest(DummyExchange("TEST1"), {"BTC": 0.17053, "XRP": 2000}, {"XRP_BTC":{"bids":[Order(0.000105, 5000)],"asks":[Order(0.0001075714286, 6000)]}})
        controller2 = ControllerTest(DummyExchange("TEST2"), {"BTC": 0.05, "XRP": 4000}, {"XRP_BTC":{"bids":[Order(0.000108428571, 1650)],"asks":[Order(0.000109, 4000)]}})
        pc = ProfitCalculator([controller1, controller2], ("XRP", "BTC"))
        pc.check_profits()
        (bidder, asker, profit_obj) = pc.get_best_trade()
        self.assertNotEqual(profit_obj, None)

if __name__ == "__main__":
    unittest.main()
