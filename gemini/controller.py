# class for Controller
from .logger import Logger as log
from .order import Order
from . import config
from .exchange import Exchange
from .profit_calculator import ProfitCalculator
import sys, asyncio, logging, math, time, copy, threading, traceback
from datetime import datetime, timedelta

# wrapper for the controller multithreaded functions
# it used as a decorator
def multithreaded(func):
    def func_wrapper(controller, loop, control_state, *kargs, **kwargs):
       res = func(controller, *kargs, **kwargs)
       control_state[0] = control_state[0] - 1
       if control_state[0] == 0:
           loop.stop()
       return res
    return func_wrapper

class Controller(object):
    ticker_lock = threading.Lock()

    def __init__(self, xchg):
        super(Controller, self).__init__()
        self.xchg = xchg

        # stores live balances
        self.balances = {}
        self.previous_balances = {}
        self.new_balance_detected = False
        self.connection_lost_detected = False
        self.reconnecting = False

        # our own balance tracking to detect exchange synchronization problems
        self.offline_balances = {}
        self.initial_balances = {}

        # the exchange order book
        self.depth = {}
        self.orders = {} # outstanding orders by id
        self.has_active_orders = False
        self.to_resubmit_orders = []
        self.bad_prices = {pair:0 for pair in xchg.get_tradeable_pairs()}

    def submit_order(self, pair, side, price, volume):
        order = self.xchg.submit_order(pair, side, price, volume)
        self.orders[order.id] = order
        if side == 'BUY':
            self.balances[pair[1]] = self.balances.get(pair[1],0.0) - float(volume) * float(price) * (1.0 + self.xchg.trading_fee)
            self.offline_balances[pair[0]] = self.offline_balances.get(pair[0],0.0) + float(volume)
            self.offline_balances[pair[1]] = self.offline_balances.get(pair[1],0.0) - float(volume) * float(price) * (1.0 + self.xchg.trading_fee)
        else:
            self.balances[pair[0]] = self.balances.get(pair[0],0.0) - float(volume)
            self.offline_balances[pair[0]] = self.offline_balances.get(pair[0],0.0) - float(volume)
            self.offline_balances[pair[1]] = self.offline_balances.get(pair[1],0.0) + float(volume) * float(price) * (1.0 - self.xchg.trading_fee)
        log.info('%s Offline balances: %s' % (self.xchg.name, str({key:val for key, val in self.offline_balances.items() if val != 0})))
        return order

    @multithreaded
    def async_submit_order(self, pair, side, price, volume):
        base, alt = pair
        try:
            order = self.submit_order(pair, side, self.format_price(pair,price), self.format_volume(pair,volume))
            log.ok("%s %s Trade submitted: %f %s/%s at %.8g" % (self.xchg.name, side, volume, base, alt, price))
        except Exception as exc:
            log.error("%s failed to process a %s order: %f %s/%s at %.8g. %s" % (self.xchg.name, side, volume, base, alt, price, traceback.format_exc()))

    def cancel_order(self, order):
        if order.id in self.orders:
            self.xchg.cancel_orders([order])
            if order.type == 'SELL':
                self.balances[order.pair[0]] += order.v
                self.offline_balances[order.pair[0]] += order.v
                self.offline_balances[order.pair[1]] -= order.v * order.p * (1.0 - self.xchg.trading_fee)
            else:
                self.balances[order.pair[1]] += order.v * order.p * (1.0 + self.xchg.trading_fee)
                self.offline_balances[order.pair[0]] -= order.v
                self.offline_balances[order.pair[1]] += order.v * order.p * (1.0 + self.xchg.trading_fee)
            log.info('%s Offline balances: %s' % (self.xchg.name, str({key:val for key, val in self.offline_balances.items() if val != 0})))
            return self.orders.pop(order.id)
        return None

    def check_active_orders(self):
        if not self.has_active_orders:
            self.xchg.pending_order_timestamp = datetime.now() - timedelta(seconds=60)
        if self.has_active_orders:
            if self.has_active_orders:
                last_time = self.xchg.pending_order_timestamp
                if datetime.now() > last_time + timedelta(seconds=60):
                    self.xchg.pending_order_timestamp = datetime.now()
                    log.info("Trade aborted: %s has a pending order" % (self.xchg.name,))
            return True
        return False

    def format_price(self, pair, price):
        pairstr = pair[0] + '_' + pair[1]
        price_dec = config.NB_PRICE_DECIMALS['DEFAULT']
        if pairstr in config.NB_PRICE_DECIMALS:
            pair_config = config.NB_PRICE_DECIMALS[pairstr]
            price_dec = pair_config[self.xchg.name] if self.xchg.name in pair_config else pair_config['DEFAULT']
        return ('{:.' + str(price_dec) + 'f}').format(price)

    def format_volume(self, pair, volume):
        pairstr = pair[0] + '_' + pair[1]
        if pairstr not in config.NB_VOLUME_DECIMALS:
            pairstr = 'DEFAULT'
        return ('{:.' + str(config.NB_VOLUME_DECIMALS[pairstr]) + 'f}').format(ProfitCalculator.floor_volume(pair, volume))

    def get_highest_bid(self, pair):
        base, alt = pair
        pairstr = base + "_" + alt
        if pairstr in self.depth and len(self.depth[pairstr]['bids']) > 0:
            return self.depth[pairstr]['bids'][0].p
        return None

    def get_lowest_ask(self, pair):
        base, alt = pair
        pairstr = base + "_" + alt
        if pairstr in self.depth and len(self.depth[pairstr]['asks']) > 0:
            return self.depth[pairstr]['asks'][0].p
        return None

    def get_best_bid_min_vol(self, pair):
        base, alt = pair
        pairstr = base + "_" + alt
        volume = 0
        order = Order(0, 0)
        if pairstr in self.depth and len(self.depth[pairstr]['bids']) > 0:
            for o in self.depth[pairstr]['bids']:
                order = Order(o.p, order.v + o.v)
                if order.v >= config.MIN_VOL[base]:
                    break
        return order

    def get_best_ask_min_vol(self, pair):
        base, alt = pair
        pairstr = base + "_" + alt
        volume = 0
        order = Order(0, 0)
        if pairstr in self.depth and len(self.depth[pairstr]['asks']) > 0:
            for o in self.depth[pairstr]['asks']:
                order = Order(o.p, order.v + o.v)
                if order.v >= config.MIN_VOL[base]:
                    break
        return order

    @multithreaded
    def update_depth(self, pair):
        base, alt = pair
        pairstr = base + "_" + alt
        try:
            if self.xchg.has_error[0]:
                self.depth[pairstr] = {'bids':[],'asks':[]}
            else:
                self.depth[pairstr] = self.xchg.get_depth(base, alt)
        except:
            # clear the book in case of an error
            self.depth[pairstr] = {'bids':[],'asks':[]}

    @multithreaded
    def update_all_balances(self):
        self.clear()
        self.reconnecting = False
        try:
            if self.xchg.has_error[0]:
                self.balances = None
            else:
                self.balances = self.xchg.get_all_balances()
        except Exception as exc:
            log.error("%s: error during update_all_balances. details: %s" % (self.xchg.name, traceback.format_exc()))
            self.balances = None
        connection_lost_detected = False
        if self.balances is None or len(self.balances) == 0:
            connection_lost_detected = True
            if not self.connection_lost_detected:
                log.warning("%s: connection lost (api method: update_all_balances)" % (self.xchg.name,))
        else:
            new_balance_detected = False
            balance_diff = {}
            for ccy, vol in self.balances.items():
                if ccy in self.previous_balances:
                    if self.balances[ccy] != self.previous_balances[ccy]:
                        new_balance_detected = True
                        balance_diff[ccy] = self.balances[ccy] - self.previous_balances[ccy]
                else:
                    if self.balances[ccy] > 0:
                        new_balance_detected = True
                        balance_diff[ccy] = self.balances[ccy]
            if new_balance_detected:
                for ccy, vol in balance_diff.items():
                    if len(self.to_resubmit_orders) == 0:
                        log.ok("%s new balance: %f%s" % (self.xchg.name, vol, ccy))
                    log.info("%s updated online balance: %f%s Diff: %f" % (self.xchg.name, self.balances[ccy], ccy, vol))
            self.previous_balances = self.balances.copy()
            # initialize offline balances
            if len(self.offline_balances) == 0:
                self.offline_balances = self.balances.copy()
                self.initial_balances = self.balances.copy()
                if new_balance_detected:
                    log.info("%s offline balance: %s" % (self.xchg.name, str({ccy: bal for ccy, bal in self.offline_balances.items() if bal != 0.0})))
            else:
                for ccy, balance in self.balances.items():
                    if ccy not in self.offline_balances:
                        self.offline_balances[ccy] = self.balances[ccy]
                        self.initial_balances[ccy] = self.balances[ccy]
                        if new_balance_detected and self.offline_balances[ccy] != 0.0:
                            log.info("%s offline balance: %f%s" % (self.xchg.name, self.offline_balances[ccy], ccy))
            self.new_balance_detected = new_balance_detected
        self.connection_lost_detected = connection_lost_detected

    @multithreaded
    def query_active_orders(self):
        connection_lost_detected = False
        try:
            if self.xchg.has_error[0]:
                connection_lost_detected = True
            else:
                if len(self.to_resubmit_orders) == 0:
                    orders = self.xchg.query_active_orders()
                    if len(orders) > 0:
                        self.has_active_orders = True
                        # cancel orders when the price is too far from mid-spread
                        # place them in the to_resubmit_orders list for next tick to process them
                        self.to_resubmit_orders = []
                        for order in orders:
                            if order.id not in self.orders:
                                log.error('%s detected a trade %s which is not in the registry' % (self.xchg.name, self.xchg.format_pair(order.pair)))
                                continue
                            pair = order.pair
                            pairstr = pair[0] + '_' + pair[1]
                            if self.depth[pairstr] is None or len(self.depth[pairstr]['bids']) == 0 or len(self.depth[pairstr]['asks']) == 0:
                                log.error('%s %s Cannot read order book while updating active orders' % (self.xchg.name, pairstr))
                            else:
                                mid_price = (self.depth[pairstr]['bids'][0].p + self.depth[pairstr]['asks'][0].p) / 2
                                if ((order.type == 'BUY' and mid_price > (order.p + self.depth[pairstr]['asks'][0].p) / 2) or
                                    (order.type == 'SELL' and mid_price < (order.p + self.depth[pairstr]['bids'][0].p) / 2)):
                                    order_orig = self.cancel_order(order)
                                    success = order_orig is not None
                                    status = 'SUCCESS' if success else 'FAILURE'
                                    msg = '%s %s PRICE UPDATE %s. cancelled order: %s' % (self.xchg.name, pairstr, status, str(order_orig))
                                    if success:
                                        log.warning(msg)
                                    else:
                                        log.error(msg)
                                    order_orig.v = order.v
                                    self.to_resubmit_orders.append(order_orig)
                    else:
                        self.has_active_orders = False
                else:
                    # update the order price to mid-spread
                    for order in self.to_resubmit_orders:
                        pair = order.pair
                        pairstr = pair[0] + '_' + pair[1]
                        if self.depth[pairstr] is None or len(self.depth[pairstr]['bids']) == 0 or len(self.depth[pairstr]['asks']) == 0:
                            log.error('%s %s Cannot read order book while updating active orders' % (self.xchg.name, pairstr))
                        else:
                            # caldulate mid-spread price
                            mid_price = (self.depth[pairstr]['bids'][0].p + self.depth[pairstr]['asks'][0].p) / 2.0
                            # adjust the volume according to the new price and available amount in the wallet
                            if order.type == 'BUY':
                                xcgh_balance = self.balances[pair[1]]
                                volume = order.v * mid_price * (1.0 + self.xchg.trading_fee)
                                residual = config.RESIDUAL_AMOUNT[pair[1]]
                                if xcgh_balance - volume < residual:
                                    volume = (xcgh_balance - residual) / (mid_price * (1.0 + self.xchg.trading_fee))
                                    log.warning('%s %s/%s PRICE UPDATE. updated order volume from %f to %f' % (self.xchg.name, pair[0], pair[1], order.v, volume))
                                    order.v = volume
                            new_order = self.submit_order(pair, order.type, self.format_price(pair,mid_price), self.format_volume(pair,order.v))
                            log.warning('%s %s/%s PRICE UPDATE. updated order: %s' % (self.xchg.name, pair[0], pair[1], str(new_order)))
                    self.to_resubmit_orders = []
        except Exception as exc:
            connection_lost_detected = True
            self.to_resubmit_orders = []
            if not self.connection_lost_detected:
                log.warning("%s: connection lost (api method: query_active_orders). Exception: %s" % (self.xchg.name, traceback.format_exc()))
        self.connection_lost_detected = connection_lost_detected

    @multithreaded
    def get_tickers(self, tickers):
        connection_lost_detected = False
        try:
            xchg_tickers = self.xchg.get_ticker()
            for pair, xchg_ticker in xchg_tickers.items():
                tickers[pair] = xchg_ticker
        except Exception as exc:
            connection_lost_detected = True
            if not self.connection_lost_detected:
                log.warning("%s: connection lost (api method: get_tickers). Exception: %s" % (self.xchg.name, traceback.format_exc()))
        self.connection_lost_detected = connection_lost_detected

    @multithreaded
    def validate_order_book(self, pair, tickers):
        connection_lost_detected = False
        try:
            if not self.reconnecting and not self.connection_lost_detected and pair in tickers:
                ticker = tickers[pair]
                order_book = self.xchg.get_depth(pair[0], pair[1])
                if (order_book['bids'][0].p - ticker) > 0.01 * order_book['bids'][0].p or (ticker - order_book['asks'][0].p) > 0.01 * order_book['asks'][0].p:
                    pairstr = pair[0] + '_' + pair[1]
                    if self.bad_prices[pair] == 3:
                        log.error('%s %s Bad price detected: %.8g not within (%.8g, %.8g)' % (self.xchg.name, pairstr, ticker, order_book['bids'][0].p, order_book['asks'][0].p))
                    elif self.bad_prices[pair] < 3:
                        log.warning('%s %s price %.8g not within (%.8g, %.8g)' % (self.xchg.name, pairstr, ticker, order_book['bids'][0].p, order_book['asks'][0].p))
                    self.bad_prices[pair] += 1
                else:
                    self.bad_prices[pair] = 0
        except Exception as exc:
            connection_lost_detected = True
            if not self.connection_lost_detected:
                log.warning("%s: connection lost (api method: validate_order_book) pair %s. Exception: %s" % (self.xchg.name, pair[0] + pair[1], traceback.format_exc()))
        self.connection_lost_detected = connection_lost_detected

    def reconnect(self):
        if self.reconnecting:
            return
        self.reconnecting = True
        for pair in self.bad_prices.keys():
            self.bad_prices[pair] = 0
        self.clear()
        self.xchg.stop()
        self.xchg.start()
        self.xchg.reconnect()

    def clear(self):
        self.balances = {}
        self.depth = {}

    def shutdown(self):
        self.clear()
        self.xchg.stop()

class ControllerTest(Controller):
    def __init__(self, exchg, balances = None, depth = None):
        super(ControllerTest, self).__init__(exchg)
        self.name = "DUMMY " + exchg.name
        if balances is not None:
            self.balances = balances
            self.previous_balances = balances
            self.offline_balances = copy.copy(balances)
            self.initial_balances = copy.copy(balances)
            exchg.balances = balances
        if depth is not None:
            self.depth = depth

class ControllerSimulator(ControllerTest):
    def __init__(self, exchg):
        super(ControllerSimulator, self).__init__(exchg, config.SIMULATION_BALANCES)
        self.trade_num = 0

    def submit_order(self, pair, side, price, volume):
        try:
            # it is expected that the exchange cannot trade when simulating, however we still call the function so unittests can mock exchanges
            order = super(ControllerSimulator, self).submit_order(pair, side, price, volume)
        except:
            order = Order(float(price), float(volume), side, pair, "SIMUL" + str(self.trade_num))
            self.trade_num += 1
        finally:
            if side == 'BUY':
                self.offline_balances[pair[0]] += float(volume)
                self.offline_balances[pair[1]] -= float(volume) * float(price)
            else:
                self.offline_balances[pair[0]] -= float(volume)
                self.offline_balances[pair[1]] += float(volume) * float(price)
        return order

    @multithreaded
    def update_all_balances(self):
        pass

    @multithreaded
    def query_active_orders(self):
        self.has_active_orders = False

    @multithreaded
    def get_tickers(self, tickers):
        pass

    @multithreaded
    def validate_order_book(self, pair, tickers):
        pass
