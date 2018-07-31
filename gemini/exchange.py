# The abstract class to interface with an exchange
from .order import Order
from .logger import Logger as log
from .keyhandler import KeyHandler
from . import config
import abc, asyncio, concurrent, logging, os
from datetime import datetime, timedelta

class ExchangeLogHandler(logging.StreamHandler):
    def __init__(self, xchg):
        super(ExchangeLogHandler, self).__init__()
        self.xchg = xchg
    def emit(self, record):
        try:
            msg = self.format(record)
            log.info("%s: %s" % (self.xchg.name, msg))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

class Exchange(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, pairs, keyfile, loop, has_error):
        super(Exchange, self).__init__()
        self.all_pairs = pairs
        self.name = None
        self.keyhandler = KeyHandler(os.path.abspath(keyfile)) if config.MODE == 'LIVE' else None
        self.loop = loop
        self.has_error = has_error
        self.trading_fee = None
        self.tradeable_pairs = self.get_tradeable_pairs()
        self.set_tradeable_currencies()
        self.depths = {}
        self.poor_ccy = {}
        self.low_profits = {}
        self.bidask_spd_timestamps = {}
        self.pending_order_timestamp = datetime.now() - timedelta(seconds=60)
        self.trading_pairs = []
        for base, alt in self.get_tradeable_pairs():
            self.trading_pairs = self.trading_pairs + [(base, alt)]
            self.low_profits[base + '_' + alt] = datetime.now() - timedelta(seconds=60), 0.0
            self.bidask_spd_timestamps[base + '_' + alt] = datetime.now() - timedelta(seconds=60)
        self.ccies = [pair[0] for pair in self.trading_pairs] + ['BTC']

    def get_tradeable_pairs(self):
        tradeable_pairs = []
        for pair in self.all_pairs:
            a, b = pair.split("_")
            tradeable_pairs.append((a.upper(), b.upper()))
        return tradeable_pairs

    def pair_from_symbol(self, symbol):
        ccy = symbol[0:3].upper()
        mkt = symbol[3:].upper()
        if ccy not in self.ccies:
            ccy = symbol[0:4].upper()
            mkt = symbol[4:].upper()
        return (ccy, mkt)

    @abc.abstractmethod
    def format_pair(self, pair):
        return NotImplemented

    @abc.abstractmethod
    def get_depth(self, base, alt):
        '''
        returns all bids (someone wants to buy Base from you)
        and asks (someone offering to sell base to you).
        If exchange does not support the base_alt market but supports
        the alt_base market instead, it is up to the exchange to convert
        retrieved data to the desired format.
        '''
        return NotImplemented

    @abc.abstractmethod
    def get_ticker(self):
        return NotImplemented

    @abc.abstractmethod
    def get_balance(self):
        '''
        internal method
        returns dictionary of all balances
        '''
        return NotImplemented

    def get_all_balances(self):
        '''
        returns dictionary of all balances
        '''
        balances = self.get_balance()
        for ccy, bal in balances.items():
            if ccy not in config.MAX_VOL:
                continue
            required_vol = config.MAX_VOL[ccy] if config.MAX_VOL[ccy] is not None else config.MIN_VOL[ccy]
            if bal < required_vol:
                if ccy not in self.poor_ccy:
                    self.poor_ccy[ccy] = 0.0
                rel_vol_missing = (required_vol - bal) / required_vol
                if self.poor_ccy[ccy] != rel_vol_missing:
                    log.info('%s: Insufficient balance! Need +%f %s' % (self.name, required_vol - bal, ccy))
                    self.poor_ccy[ccy] = rel_vol_missing
            else:
                self.poor_ccy[ccy] = 0.0
        return balances

    @abc.abstractmethod
    def submit_order(self, pair, side, price, volume):
        return NotImplemented

    @abc.abstractmethod
    def query_active_orders(self):
        pass

    @abc.abstractmethod
    def cancel_orders(self, order_ids = None):
        pass

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def reconnect(self):
        pass

    def get_validated_pair(self, pair):
        """
        use this to check for existence of a supported
        pair for the exchagne
        returns (true_pair, swapped)
        else if pair isn't even traded, return None
        """
        if pair in self.tradeable_pairs:
            return pair
        else:
            # pair is not even traded
            return None

    def set_tradeable_currencies(self):
        """
        once tradeable pairs initialized, build list of all tradeable currencies.
        will be needed for triangular arb strategy.
        """
        C = {}
        for (base, alt) in self.tradeable_pairs:
            C[base] = ''
            C[alt] = ''
        self.tradeable_currencies = C.keys()

    def log_order(self, side, order):
        log.info('%s %s order: %s' % (self.name, side, str(order)))

# for unit-testing only
class DummyExchange(Exchange):
    all_pairs = ("eth_btc", "xrp_btc", "xrp_eth", "dash_eth", "xvg_btc", "xvg_eth", "trx_btc", "neo_usdt")

    def __init__(self, name, balances=None):
        super(DummyExchange, self).__init__(DummyExchange.all_pairs, None, None, [False])
        self.name = name
        self.trading_fee = 0.002
        self.orders = []
        self.balances = balances

    def simulate_order(self, loop, control_state, pair, side, price, volume):
        base, alt = pair
        log.ok("%s %s Trade submitted: %s/%s price %s size %s" % (self.name, side, base, alt, price, volume))
        control_state[0] = control_state[0] - 1
        if control_state[0] == 0:
            loop.stop()

    def get_depth(self, base, alt):
        return NotImplemented

    def get_ticker(self):
        return NotImplemented

    def get_balance(self, currency):
        return NotImplemented

    def get_all_balances(self):
        return NotImplemented

    def submit_order(self, pair, side, price, volume):
        if self.balances is None:
            raise RuntimeError("no funds")
        neword = Order(orderID='DUMMYORD' + str(len(self.orders)), price=price, volume=volume, type=side, pair=pair)
        self.orders.append(neword)
        return neword

    def query_active_orders(self):
        return self.orders

    def stop(self):
        return NotImplemented

    def reconnect(self):
        return NotImplemented