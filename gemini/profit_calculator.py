from .utils import total_base_volume
from .order import Order
from .logger import Logger as log
from . import config
from datetime import datetime, timedelta
import math

class ProfitCalculator(object):
    """
    class for computing a profit matrix from a given set of controllers
    and their orderbooks
    """
    def __init__(self, controllers, pair):
        self.controllers = controllers
        self.pair = pair
        self.prices = {}        # maintains hi_bids and lo_asks for each controller
        self.balances = {}      # base and alt balances for each exchange
        self.profit_spread = {} # price spreads with transaction fees applied
        self.profits = {}       # actual ALT profits, accounting for balances and volumes

        self.update_balances()
        self.update_profit_spread() # automatically perform calculations upon initialization
        self.error = False

    def update_profit_spread(self):
        """
        computes the net profit spread, trading fees are included, but not the deposit/withdraw fees
        """
        self.profit_spread = {b.xchg.name:{a.xchg.name : 0 for a in self.controllers} for b in self.controllers}
        self.prices = {b.xchg.name : {"bid": b.get_highest_bid(self.pair),
                                      "ask": b.get_lowest_ask(self.pair)}  for b in self.controllers}
        for bidder in self.controllers: # bidder names
            for asker in self.controllers: # asker names
                if bidder == asker:
                    continue
                (b,a) = (bidder.xchg.name, asker.xchg.name)
                hi_bid = self.prices[b]['bid']
                lo_ask = self.prices[a]['ask']
                if hi_bid is None or lo_ask is None:
                    self.profit_spread[b][a] = None
                else:
                    # ALT profit with fees applied
                    self.profit_spread[b][a] = self.get_profit_spread(bidder.xchg.trading_fee,hi_bid,asker.xchg.trading_fee,lo_ask)

    def update_balances(self):
        base, alt = self.pair
        for controller in self.controllers:
            if controller.balances is not None:
                self.balances[controller.xchg.name] = { "base" : controller.balances.get(base,0),
                                                   "alt" : controller.balances.get(alt,0) }

    def check_profits(self):
        # examine each pair for profits. A number of trivial reject tests are performed:
        # 0) needs to have a positive profit spread to begin with that exceeds 0.01 USD
        # 1) account needs to have sufficient balance to fill the minimum order volume
        # 2) after computing the max tradeable volume (limited by my balance),
        base, alt = self.pair
        success = False
        self.profits = {b.xchg.name:{a.xchg.name : None for a in self.controllers} for b in self.controllers}
        for bidder in self.controllers:
            for asker in self.controllers:
                slug = base + "_" + alt
                if bidder == asker or slug not in bidder.depth or slug not in asker.depth:
                    continue
                (b,a) = (bidder.xchg.name, asker.xchg.name)
                spread = self.profit_spread[b][a]
                bidder_bids = bidder.depth[slug]['bids']
                bidder_asks = bidder.depth[slug]['asks']
                asker_bids = asker.depth[slug]['bids']
                asker_asks = asker.depth[slug]['asks']
                if len(bidder_bids) == 0 or len(bidder_asks) == 0 or len(asker_bids) == 0 or len(asker_asks) == 0:
                    continue
                if bidder.xchg.name in config.MAX_BIDASK_SPREAD_PCT:
                    xchg_spds = config.MAX_BIDASK_SPREAD_PCT[bidder.xchg.name]
                    max_bidask_spd = xchg_spds[slug] if slug in xchg_spds else xchg_spds['DEFAULT']
                else:
                    max_bidask_spd = config.MAX_BIDASK_SPREAD_PCT['DEFAULT'][alt]
                max_bidask_spd /= 100.0
                if (bidder.depth[slug]['asks'][0].p - bidder_bids[0].p) / bidder_bids[0].p > max_bidask_spd:
                    last_time = bidder.xchg.bidask_spd_timestamps[slug]
                    if datetime.now() > last_time + timedelta(seconds=300):
                        bidder.xchg.bidask_spd_timestamps[slug] = datetime.now()
                        log.info("Bid-Ask spread too high on %s pair %s: highest bid %.8g, lowest ask %.8g" % (bidder.xchg.name, slug, bidder_bids[0].p, bidder.depth[slug]['asks'][0].p))
                if asker.xchg.name in config.MAX_BIDASK_SPREAD_PCT:
                    xchg_spds = config.MAX_BIDASK_SPREAD_PCT[asker.xchg.name]
                    max_bidask_spd = xchg_spds[slug] if slug in xchg_spds else xchg_spds['DEFAULT']
                else:
                    max_bidask_spd = config.MAX_BIDASK_SPREAD_PCT['DEFAULT'][alt]
                max_bidask_spd /= 100.0
                if (asker_asks[0].p - asker.depth[slug]['bids'][0].p) / asker.depth[slug]['bids'][0].p > max_bidask_spd:
                    last_time = asker.xchg.bidask_spd_timestamps[slug]
                    if datetime.now() > last_time + timedelta(seconds=300):
                        asker.xchg.bidask_spd_timestamps[slug] = datetime.now()
                        log.info("Bid-Ask spread too high on %s pair %s: highest bid %.8g, lowest ask %.8g" % (asker.xchg.name, slug, asker.depth[slug]['bids'][0].p, asker_asks[0].p))
                if bidder_bids[0].p > bidder.depth[slug]['asks'][0].p:
                    log.error("Corrupted order book on %s pair %s: highest bid %f > lowest ask %f" % (bidder.xchg.name, slug, bidder_bids[0].p, bidder.depth[slug]['asks'][0].p))
                    self.error = True
                    return False
                if asker.depth[slug]['bids'][0].p > asker_asks[0].p:
                    log.error("Corrupted order book on %s pair %s: highest bid %f > lowest ask %f" % (asker.xchg.name, slug, asker.depth[slug]['bids'][0].p, asker_asks[0].p))
                    self.error = True
                    return False
                profit_obj = self.calculate_order(bidder, bidder_bids, asker, asker_asks)
                if profit_obj is not None:
                    self.profits[b][a] = profit_obj
                    success = True

        return success # return True if there are any profits at all

    def floor_volume(pair, volume):
        base, alt = pair
        unit = config.TRADING_UNIT[base]
        floored_vol = math.floor(volume/unit)*unit
        return floored_vol

    def ceil_volume(pair, volume):
        base, alt = pair
        unit = config.TRADING_UNIT[base]
        ceil_vol = math.ceil(volume/unit)*unit
        return ceil_vol

    def calc_profits(self, bidder, asker, best_bid, best_ask, bidder_base_balance, asker_alt_balance, min_base_vol, profit_adj, vol_adj):
        base, alt = self.pair
        bidder_base_balance = max(bidder_base_balance - config.RESIDUAL_AMOUNT[alt] / best_bid.p, 0)
        asker_alt_balance = max(asker_alt_balance - config.RESIDUAL_AMOUNT[alt], 0)

        asker_base_afford = (asker_alt_balance / self.prices[asker.xchg.name]['ask']) * (1 - (vol_adj / best_ask.p)) # check how much base we can afford to buy from asker
        poor = False
        if (bidder_base_balance < min_base_vol):
            poor = True

        if (asker_base_afford < min_base_vol):
            poor = True

        if poor:
            return None

        """
        calculate the arbitrage volume from the exchange order books
        """
        # maximum volume from the exchange order books
        max_base_xchg = min(best_bid.v, best_ask.v * (1.0 - asker.xchg.trading_fee))
        # maximum volume from the wallet balances
        max_base_balance = min(bidder_base_balance, asker_base_afford)
        # volume for the arbitrage
        base_vol = min(max_base_xchg, max_base_balance)
        # apply the volume limits per ccy from the config
        base_vol = min(base_vol, config.MAX_VOL[base]) if config.MAX_VOL[base] is not None else base_vol
        # apply a volume adjustment to reflect the price adjusment (increased for the asker, decreased for bidder)
        base_vol *= 1 - (vol_adj / best_ask.p)
        # allow for ccies with large trading units to trade with a loss of coins
        # if we are dealing with large units, the bidder should take the charge of all trading fees
        # otherwise the profit threshold would never be reached
        asker_tx = 1.0 - asker.xchg.trading_fee
        if base in config.LARGE_UNIT:
            base_vol *= asker_tx
            base_vol = ProfitCalculator.floor_volume(self.pair, base_vol)
            if base_vol > asker_base_afford:
                base_vol -= config.TRADING_UNIT[base]
            bidder_order = Order(best_bid.p, base_vol)
            asker_order = Order(best_ask.p, base_vol)
        else:
            if base_vol / asker_tx > asker_base_afford:
                bidder_order = Order(best_bid.p, ProfitCalculator.floor_volume(self.pair, base_vol * asker_tx))
                asker_order = Order(best_ask.p, ProfitCalculator.floor_volume(self.pair, base_vol))
            else:
                bidder_order = Order(best_bid.p, ProfitCalculator.floor_volume(self.pair, base_vol))
                asker_order = Order(best_ask.p, ProfitCalculator.floor_volume(self.pair, base_vol / asker_tx))
        if asker_order.v == 0 or bidder_order.v == 0:
            return None
        profit = bidder_order.v *  (bidder_order.p * (1.0 - bidder.xchg.trading_fee) - asker_order.p / (1.0 - asker.xchg.trading_fee))
        return {
                "bidder_order":bidder_order,
                "asker_order":asker_order,
                "profit":profit,
                "profit_rel":profit/(asker_order.p * asker_order.v)
                }


    def calculate_order(self, bidder, bids, asker, asks):
        if len(bids) == 0 or len(asks) == 0 or bidder.xchg.name not in self.balances or asker.xchg.name not in self.balances:
            return None
        base, alt = self.pair
        """
        check minimal volume condition
        """
        min_base_vol = config.MIN_VOL[base]
        best_bid, best_ask = bids[0], asks[0]
        if (best_bid.v < min_base_vol):
            #print('%s insufficient best bid volume to satisfy min trade: %f %s at %s' % (bidder.xchg.name, best_bid.v, base, best_bid.p))
            best_bid = bidder.get_best_bid_min_vol(self.pair)
            #print('adjusted bid: %f %s at %s' % (best_bid.v, base, best_bid.p))
        if (best_ask.v < min_base_vol):
            #print('%s insufficient best ask volume to satisfy min trade: %f %s at %s' % (asker.xchg.name, best_ask.v, base, best_ask.p))
            best_ask = asker.get_best_ask_min_vol(self.pair)
            #print('adjusted ask: %f %s at %s' % (best_ask.v, base, best_ask.p))
        # vol adjustment to increase chances to get the deal instantaneously (profit cut)
        profit_adj = config.PROFIT_ADJUSTMENT / 2
        vol_adj = (best_bid.p - best_ask.p) * profit_adj
        min_best_trade_vol = min(best_bid.v, best_ask.v)
        best_bid = Order(best_bid.p - vol_adj, min_best_trade_vol)
        best_ask = Order(best_ask.p + vol_adj, min_best_trade_vol)

        """
        check profit threshold
        """
        bidder_base_balance = self.balances[bidder.xchg.name]['base'] # check how much base we can afford to sell to bidder
        asker_alt_balance = self.balances[asker.xchg.name]['alt']

        profit_obj = self.calc_profits(bidder, asker, best_bid, best_ask, bidder_base_balance, asker_alt_balance, min_base_vol, profit_adj, vol_adj)
        profit_rel = 0.0 if profit_obj is None else profit_obj['profit_rel']
        #log.info('%s/%s %s/%s profit : %s pct' % (asker.xchg.name, bidder.xchg.name, base, alt, profit_rel*100))
        do_arbitrage = False
        rebalancing = False
        if profit_rel >= config.MIN_PROFIT:
            return {
                "bidder_order":profit_obj['bidder_order'],
                "asker_order":profit_obj['asker_order'],
                "profit":profit_obj['profit'],
                "profit_pct":profit_rel*100,
                "rebalancing":rebalancing
                }
        return None

    def get_best_trade(self):
        """
        only the the best deal is executed for each tick
        """
        best_profit = 0.0
        best_profit_obj = None
        hi_bidder = None
        lo_asker = None
        for bidder in self.controllers:
            for asker in self.controllers:
                (b,a) = (bidder.xchg.name, asker.xchg.name)
                profit_obj = self.profits[b][a]
                if profit_obj is not None:
                    if profit_obj["profit_pct"] > best_profit:
                        best_profit = profit_obj["profit_pct"]
                        best_profit_obj = profit_obj
                        hi_bidder = bidder
                        lo_asker = asker

        return (hi_bidder, lo_asker, best_profit_obj)


    def get_profit_spread(self, bidder_fee, bid_price, asker_fee, ask_price):
        # simple formula
        # explanation: if hi_bid = 110 and lo_ask = 100
        # then lo_ask will only return 0.998 units per 1 paid
        # I am selling base to the bidder at a rate of 110 per unit given
        # but i actually want to only sell 0.998 units (to match ask recv volume) < -- wait what???
        # so I scale by 0.998
        # finally, the bid order itself has an exchange fee so I only see 0.998 of *that*
        # NOTE: this does not take actual order volumes into account, so this is not
        # representative of what actual profits would be
        return bid_price * (1.0 - asker_fee) * (1.0 - bidder_fee) - ask_price
