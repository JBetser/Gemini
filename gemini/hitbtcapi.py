from .exchange import Exchange
from .keyhandler import KeyHandler
from .hitbtc.trade_client import trade_api, public_api
from .hitbtc.client import HitBTC
from .hitbtc.connector import log as hitbtc_logger
from .order import Order
from .logger import Logger as log
from . import config
import time, queue, copy, threading, _thread, logging, uuid
from sortedcontainers import SortedDict

class HitbtcErrorHandler(logging.StreamHandler):
    """
    A handler class which allows the cursor to stay on
    one line for selected messages
    """
    on_same_line = False
    def __init__(self, exchg):
        super(HitbtcErrorHandler, self).__init__()
        self.exchg = exchg

    def emit(self, record):
        try:
            msg = self.format(record)
            if msg.startswith("Connection") or msg.startswith("Reconnection") or msg.startswith("Attempting"):
                log.info("HITBTC " + msg)
                if msg.startswith("Reconnection"):
                    self.exchg.reconnect()
            else:
                log.error("HITBTC " + msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            self.exchg.has_error[0] = True
            self.exchg.stop()
            raise
        except:
            self.exchg.has_error[0] = True
            self.exchg.stop()
            self.handleError(record)

class Hitbtc(Exchange):
    all_pairs = ("eth_btc", "xrp_btc", "ltc_btc", "xvg_btc", "trx_btc", "dash_btc", "neo_btc", "eos_btc", "xmr_btc",
                            "xrp_eth", "ltc_eth", "xvg_eth", "trx_eth", "dash_eth", "neo_eth", "eos_eth", "xmr_eth",
      "btc_usdt","eth_usdt","xrp_usdt",           "xvg_usdt",                       "neo_usdt") # "ltc_usdt","dash_usdt","trx_usdt" ,"eos_usdt","xmr_usdt"

    def __init__(self, keyfile, loop, has_error):
        super(Hitbtc, self).__init__(Hitbtc.all_pairs, keyfile, loop, has_error)
        self.stop_updatebook_thread = False
        self.updatelock = threading.Lock()
        self.exitlock = threading.Lock()
        self.xchg_logger = hitbtc_logger
        self.xchg_logger.addHandler(HitbtcErrorHandler(self))
        self.trade_api = None
        self.public_rest_api = public_api()
        if self.keyhandler is not None:
            key = list(self.keyhandler.getKeys())[0]
            secret = self.keyhandler.getSecret(key)
            self.public_api = HitBTC(key=key, secret=secret)
            self.trade_api = trade_api(key, secret)
        else:
            self.public_api = HitBTC()
        self.name = 'HITBTC'
        self.trading_fee = 0.001
        self.start()
        self.reconnect()
        self.update_depth_thread = threading.Thread(target = self.update_depth)
        self.update_depth_thread.start()
        self.init = True

    def format_pair(self, pair):
        return pair[0].upper() + ('USD' if pair[1].upper() == 'USDT' else pair[1].upper())

    def update_depth(self):
        if self.stop_updatebook_thread:
            return
        with self.exitlock:
            while True:
                if self.stop_updatebook_thread:
                    break
                book = self.public_api.recv()
                pairstr = book[1]
                if pairstr not in self.trading_pairs:
                    continue
                if book[0] == "snapshotOrderbook":
                    bids = [{'price':float(bid['price']),'size':float(bid['size'])} for bid in book[2]['bid']]
                    asks = [{'price':float(ask['price']),'size':float(ask['size'])} for ask in book[2]['ask']]
                    with self.updatelock:
                        self.depths[pairstr]['bids'] = [Order(bid['price'], bid['size']) for bid in bids][:10]
                        self.depths[pairstr]['asks'] = [Order(ask['price'], ask['size']) for ask in asks][:10]
                        self.indexed_depths[pairstr]['bids'] = SortedDict({order.p: order for order in self.depths[pairstr]['bids']})
                        self.indexed_depths[pairstr]['asks'] = SortedDict({order.p: order for order in self.depths[pairstr]['asks']})
                elif book[0] == "updateOrderbook":
                    for bid in book[2]['bid']:
                        bid_price = float(bid['price'])
                        bid_size = float(bid['size'])
                        if bid_size < config.MIN_ORDERBOOK_VOLUME:
                            self.indexed_depths[pairstr]['bids'].pop(bid_price, None)
                        else:
                            self.indexed_depths[pairstr]['bids'][bid_price] = Order(bid_price,bid_size)
                    for ask in book[2]['ask']:
                        ask_price = float(ask['price'])
                        ask_size = float(ask['size'])
                        if ask_size < config.MIN_ORDERBOOK_VOLUME:
                            self.indexed_depths[pairstr]['asks'].pop(ask_price, None)
                        else:
                            self.indexed_depths[pairstr]['asks'][ask_price] = Order(ask_price,ask_size)
                else:
                    err = "HitBTC unknown update %s" % (str(book[0]),)
                    log.error(err)
                    raise RuntimeError(err)
                with self.updatelock:
                    self.depths[pairstr]['bids'] = list(reversed(self.indexed_depths[pairstr]['bids'].values()))[:10]
                    self.depths[pairstr]['asks'] = list(self.indexed_depths[pairstr]['asks'].values())[:10]

    def get_depth(self, base, alt):
        if self.stop_updatebook_thread:
            return {'bids':[], 'asks':[]}
        pairstr = self.format_pair((base, alt))
        with self.updatelock:
            if pairstr not in self.depths:
                return {'bids':[], 'asks':[]}
            bids = self.depths[pairstr]['bids']
            asks = self.depths[pairstr]['asks']
            # DEBUG - show best bid ask for each ccy pair
            if self.init and len(self.depths[pairstr]['bids']) > 0 and len(self.depths[pairstr]['asks']) > 0 and pairstr == 'XRPBTC':
                self.init = False
                log.info("%s %s Highest bid: %.8g, Lowest ask: %.8g" % (self.name, pairstr, self.depths[pairstr]['bids'][0].p, self.depths[pairstr]['asks'][0].p))
            return copy.copy(self.depths[pairstr])

    def get_ticker(self):
        tickers = {}
        for pairstr, ticker in self.public_rest_api.tickers().items():
            if pairstr in self.trading_pairs:
                tickers[self.pair_from_symbol(pairstr)] = (float(ticker['bid']) + float(ticker['ask'])) / 2.0
        return tickers

    def get_balance(self):
        data = self.trade_api.balance()
        return {'USDT' if c["currency"].upper() == 'USD' else c["currency"].upper() : float(c["available"]) for c in data}

    def xchg_log_handler(self, data):
        log.warning(data)

    def submit_order(self, pair, side, price, volume):
        pairstr = self.format_pair(pair)
        order = None
        if side == "SELL":
            order = self.trade_api.new_order(pairstr, "Sell", volume, price)
        elif side == "BUY":
            order = self.trade_api.new_order(pairstr, "Buy", volume, price)
        else:
            raise RuntimeError("Unsupported order type: %s" % (side,))
        self.log_order(side, order)
        return Order(orderID=order['id'], price=price, volume=volume, type=side, pair=pair)

    def query_active_orders(self):
        return [Order(orderID=order['id'],
                    price=float(order['price']),
                    volume=float(order['quantity']) - float(order['cumQuantity']),
                    type=order['side'].upper(),
                    pair=self.pair_from_symbol(order['symbol'])) for order in self.trade_api.active_orders()]

    def cancel_orders(self, orders = None):
        if orders is None:
            self.trade_api.cancel_orders()
        else:
            for order in orders:
                self.trade_api.cancel_order(order.id)

    def start(self):
        self.public_api.start()  # start the websocket connection

    def stop(self):
        self.stop_updatebook_thread = True
        self.public_api.stop()
        log.info("Closed Hitbtc websocket")

    def reconnect(self):
        self.trading_pairs = []
        self.indexed_depths = {}
        for pair in self.get_tradeable_pairs():
            pair = self.get_validated_pair(pair)
            if pair is None:
                continue
            pairstr = self.format_pair(pair)
            self.trading_pairs = self.trading_pairs + [pairstr]
            self.depths[pairstr] = {'bids': [], 'asks': []}
            self.indexed_depths[pairstr] = {'bids': {}, 'asks': {}}
            self.public_api.subscribe_book(symbol=pairstr)