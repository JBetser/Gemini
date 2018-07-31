from .exchange import Exchange, ExchangeLogHandler
from .keyhandler import KeyHandler
from .order import Order
from .logger import Logger as log
from . import config
from .bitfinex.trade_client import TradeClient, Client
from .bitfinex.client import BtfxWss
from sortedcontainers import SortedDict
import time, logging, threading

BITFINEX_MAPPING_TABLE = {"IOTA":"IOT",
           "DASH":"DSH",
           "USDT":"USD" }
BITFINEX_REVERSE_MAPPING_TABLE = dict((v,k) for k,v in BITFINEX_MAPPING_TABLE.items())

class BitfinexLogHandler(ExchangeLogHandler):
    def __init__(self, xchg):
        super(BitfinexLogHandler, self).__init__(xchg)
    def emit(self, record):
        msg = self.format(record)
        if msg.startswith('Connection opened'):
            self.xchg.reconnect()
        super(BitfinexLogHandler, self).emit(record)

class Bitfinex(Exchange):
    all_pairs = ("eth_btc", "xrp_btc", "ltc_btc", "neo_btc", "iota_btc", "trx_btc", "dash_btc", "eos_btc", "xmr_btc",
#                                                  "neo_eth", "iota_eth", "trx_eth",             "eos_eth",
      "btc_usdt","eth_usdt","xrp_usdt")#,"ltc_usdt","neo_usdt","iota_usdt","trx_usdt","dash_usdt","eos_usdt","xmr_usdt")
    # must maintain this mapping table as Bitfinex uses trigrams in its API. we need to keep track which coins we support in both formats

    def __init__(self, keyfile, loop, has_error):
        super(Bitfinex, self).__init__(Bitfinex.all_pairs, keyfile, loop, has_error)
        bitfinex_logger = logging.getLogger("gemini.bitfinex")
        log_handler = BitfinexLogHandler(self)
        log_handler.setLevel(logging.INFO)
        bitfinex_logger.addHandler(log_handler)
        self.public_api = BtfxWss()
        self.public_rest_api = Client()
        self.trade_api = None
        self.updatelock = threading.Lock()
        if self.keyhandler is not None:
            key = list(self.keyhandler.getKeys())[0]
            secret = self.keyhandler.getSecret(key)
            self.trade_api = TradeClient(key, secret)
        self.name = 'BITFINEX'
        self.trading_fee = 0.002
        self.tick_count = 0
        self.indexed_depths = {}
        self.trading_pairs = [self.format_pair(pair) for pair in self.get_tradeable_pairs()]
        self.start()
        self.reconnect()

    def mapping(pair):
        ccy, mkt = pair
        ccy = ccy.upper()
        mkt = mkt.upper()
        return (BITFINEX_MAPPING_TABLE[ccy] if ccy in BITFINEX_MAPPING_TABLE else ccy) + (BITFINEX_MAPPING_TABLE[mkt] if mkt in BITFINEX_MAPPING_TABLE else mkt)

    def reverse_mapping(pair):
        ccy, mkt = pair
        ccy = ccy.upper()
        mkt = mkt.upper()
        return (BITFINEX_REVERSE_MAPPING_TABLE[ccy] if ccy in BITFINEX_REVERSE_MAPPING_TABLE else ccy) + (BITFINEX_REVERSE_MAPPING_TABLE[mkt] if mkt in BITFINEX_REVERSE_MAPPING_TABLE else mkt)

    def format_pair(self, pair):
        return Bitfinex.mapping(pair)

    def pair_from_symbol(self, symbol):
        ccy = symbol[0:3].upper()
        mkt = symbol[3:].upper()
        return (BITFINEX_REVERSE_MAPPING_TABLE[ccy] if ccy in BITFINEX_REVERSE_MAPPING_TABLE else ccy, BITFINEX_REVERSE_MAPPING_TABLE[mkt] if mkt in BITFINEX_REVERSE_MAPPING_TABLE else mkt)

    def get_depth(self, ccy, mkt):
        pairstr = self.format_pair((ccy, mkt))
        book = self.public_api.books(pairstr)
        while not book.empty():
            entry = book.get()
            if len(entry) == 0:
                continue
            entry = entry[0]
            if len(entry) == 0:
                continue
            entry = entry[0]
            if len(entry) == 0:
                continue
            if type(entry[0]) is not list:
                entry = [entry]
##            ask_update = False
##            bid_update = False
            with self.updatelock:
                for elt in entry:
                    if elt[1] == 0:
                        self.indexed_depths[pairstr]['bids'].pop(elt[0], None)
                        self.indexed_depths[pairstr]['asks'].pop(elt[0], None)
                    elif elt[2] > 0:
                        self.indexed_depths[pairstr]['bids'][elt[0]] = elt[2]
    ##                    ask_update = True
                    elif elt[2] < 0:
                        self.indexed_depths[pairstr]['asks'][elt[0]] = elt[2] * -1
    ##                    bid_update = True
                self.depths[pairstr] = {'bids': [Order(key, val) for key, val in reversed(self.indexed_depths[pairstr]['bids'].items())],
                                        'asks': [Order(key, val) for key, val in self.indexed_depths[pairstr]['asks'].items()]}
            # order book consistency adjustment
##            while self.depths[pairstr]['asks'][0].p <= self.depths[pairstr]['bids'][0].p:
##                if ask_update:
##                    self.depths[pairstr]['bids'].pop(0)
##                    if len(self.depths[pairstr]['bids']) == 0:
##                        break
##                elif bid_update:
##                    self.depths[pairstr]['asks'].pop(0)
##                    if len(self.depths[pairstr]['asks']) == 0:
##                        break
##                else:
##                    break
        # DEBUG - show best bid ask for each ccy pair
        #if len(self.depths[pairstr]['bids']) > 0 and len(self.depths[pairstr]['asks']) > 0:
        #    log.info("%s %s Highest bid: %.8g, Lowest ask: %.8g" % (self.name, pairstr, self.depths[pairstr]['bids'][0].p, self.depths[pairstr]['asks'][0].p))
        return self.depths[pairstr]

    def get_ticker(self):
        tickers = {}
        for ticker in self.public_rest_api.tickers():
            if ticker['pair'] in self.trading_pairs:
                tickers[self.pair_from_symbol(ticker['pair'])] = ticker['mid']
        return tickers

    def get_balance(self):
        data = self.trade_api.balances()
        if "error" in data:
            err = "Bitfinex connection lost: " + str(data["error"])
            log.error(err)
            raise RuntimeError(err)
        return {(BITFINEX_REVERSE_MAPPING_TABLE[c["currency"].upper()] if c["currency"].upper() in BITFINEX_REVERSE_MAPPING_TABLE else c["currency"].upper()) : float(c["available"]) for c in data}

    def submit_order(self, pair, side, price, volume):
        pairstr = Bitfinex.mapping(pair).lower()
        order = None
        if side == "SELL":
            order = self.trade_api.place_order(volume, price, "sell", "exchange limit", symbol=pairstr)
        elif side == "BUY":
            order = self.trade_api.place_order(volume, price, "buy", "exchange limit", symbol=pairstr)
        else:
            raise RuntimeError("Unsupported order type: %s" % (side,))
        self.log_order(side, order)
        return Order(orderID=order['id'], price=price, volume=volume, type=side, pair=pair)

    def query_active_orders(self):
        return [Order(orderID=order['id'],
                    price=float(order['price']),
                    volume=float(order['remaining_amount']),
                    type=order['side'].upper(),
                    pair=self.pair_from_symbol(order['symbol'])) for order in self.trade_api.active_orders()]

    def cancel_orders(self, orders = None):
        if orders is None:
            self.trade_api.delete_all_orders()
        else:
            for order in orders:
                self.trade_api.delete_order(int(order.id))

    def start(self):
        self.public_api.start()
        while not self.public_api.conn.connected.is_set():
            time.sleep(1)

    def stop(self):
        self.public_api.stop()
        self.depths = {}
        log.info("Closed Bitfinex websocket")

    def reconnect(self):
        for pair in self.get_tradeable_pairs():
            pair = self.get_validated_pair(pair)
            if pair is None:
                continue
            pairstr = self.format_pair(pair)
            self.depths[pairstr] = {'bids': [], 'asks': []}
            self.indexed_depths[pairstr] = {'bids': SortedDict(), 'asks': SortedDict()}
            self.public_api.subscribe_to_order_book(pairstr)
        log.info("Connected to Bitfinex websocket")