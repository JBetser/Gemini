
from .exchange import Exchange, ExchangeLogHandler
from .keyhandler import KeyHandler
from .order import Order
from .bittrex.bittrex import Bittrex as BittrexClient
from .bittrex.websocket_client import BittrexSocket
from functools import partial
from sortedcontainers import SortedDict
import logging, time, threading

class BittrexSocketClient(BittrexSocket):
    TY_ADD = 0
    TY_REMOVE = 1
    TY_UPDATE = 2
    def __init__(self):
        super(BittrexSocketClient, self).__init__()
        self.depths = {}
        self.indexed_depths = {}
        self.updatelock = threading.Lock()
    def subscribe_to_orderbook(self, depths, tickers):
        self.depths = depths
        for ticker in tickers:
            self.indexed_depths[ticker] = {'bids': SortedDict(), 'asks': SortedDict()}
        super(BittrexSocketClient, self).subscribe_to_exchange_deltas(tickers)
    def on_public(self, msg):
        with self.updatelock:
            for o in msg['Z']:
                if o['TY'] == BittrexSocketClient.TY_ADD or o['TY'] == BittrexSocketClient.TY_UPDATE:
                    self.indexed_depths[msg['M']]['bids'][o['R']] = o['Q']
                elif o['TY'] == BittrexSocketClient.TY_REMOVE:
                    self.indexed_depths[msg['M']]['bids'].pop(o['R'], None)
            for o in msg['S']:
                if o['TY'] == BittrexSocketClient.TY_ADD or o['TY'] == BittrexSocketClient.TY_UPDATE:
                    self.indexed_depths[msg['M']]['asks'][o['R']] = o['Q']
                elif o['TY'] == BittrexSocketClient.TY_REMOVE:
                    self.indexed_depths[msg['M']]['asks'].pop(o['R'], None)
            self.depths[msg['M']] = {'bids': [Order(key, val) for key, val in reversed(self.indexed_depths[msg['M']]['bids'].items())],
                                    'asks': [Order(key, val) for key, val in self.indexed_depths[msg['M']]['asks'].items()]}

class Bittrex(Exchange):
    all_pairs = ("eth_btc", "xrp_btc", "ltc_btc", "xvg_btc", "dash_btc", "xlm_btc", "neo_btc", "trx_btc", "xmr_btc",
                            "xrp_eth", "ltc_eth",            "dash_eth", "xlm_eth", "neo_eth", "trx_eth", "xmr_eth",
      "btc_usdt","eth_usdt","xrp_usdt",           "xvg_usdt",                       "neo_usdt")# "ltc_usdt", dash_usdt", "xmr_usdt"

    def __init__(self, keyfile, loop, has_error):
        super(Bittrex, self).__init__(Bittrex.all_pairs, keyfile, loop, has_error)
        log = logging.getLogger("gemini.bittrex")
        log_handler = ExchangeLogHandler(self)
        log_handler.setLevel(logging.INFO)
        log.addHandler(log_handler)
        self.api = None
        if self.keyhandler is not None:
            key = list(self.keyhandler.getKeys())[0]
            api_secret = self.keyhandler.getSecret(key)
            self.api = BittrexClient(key, api_secret)
        self.name = 'BITTREX'
        self.trading_fee = 0.0025
        self.tickers = []
        self.bm = BittrexSocketClient()
        self.bm.enable_log()
        self.start()

    def format_pair(self, pair):
        return pair[1].upper() + '-' + pair[0].upper()

    def pair_from_symbol(self, symbol):
        mkt = symbol[0:3].upper()
        ccy = symbol[4:].upper()
        if ccy not in self.ccies:
            mkt = symbol[0:4].upper()
            ccy = symbol[5:].upper()
        return (ccy, mkt)

    def get_depth(self, base, alt):
        pairstr = self.format_pair((base, alt))
        # DEBUG - show best bid ask for each ccy pair
        # if len(self.depths[pairstr]['bids']) > 0 and len(self.depths[pairstr]['asks']) > 0:
        #    self.log.info("%s %s Highest bid: %.8g, Lowest ask: %.8g" % (self.name, pairstr, self.depths[pairstr]['bids'][0].p, self.depths[pairstr]['asks'][0].p))
        return self.depths[pairstr]

    def get_ticker(self):
        tickers = {}
        for pair in self.get_tradeable_pairs():
            ticker = self.api.get_ticker(self.format_pair(pair))['result']
            tickers[pair] = (ticker['Ask'] + ticker['Bid']) / 2.0
        return tickers

    def get_balance(self):
        data = self.api.get_balances()
        return {c["Currency"].upper() : float(c["Available"]) for c in data['result']}

    def submit_order(self, pair, side, price, volume):
        pairstr = self.format_pair(pair)
        order = None
        if side == "SELL":
            order = self.api.sell_limit(market=pairstr, quantity=volume, rate=price)
        elif side == "BUY":
            order = self.api.buy_limit(market=pairstr, quantity=volume, rate=price)
        else:
            raise RuntimeError("Unsupported order type: %s" % (side,))
        self.log_order(side, order)
        return Order(orderID=order['result']['uuid'], price=price, volume=volume, type=side, pair=pair)

    def query_active_orders(self):
        return [Order(orderID=order['OrderUuid'],
                        price=float(order['Limit']),
                        volume=float(order['QuantityRemaining']),
                        type='SELL' if order['OrderType'] == 'LIMIT_SELL' else 'BUY',
                        pair=self.pair_from_symbol(order['Exchange'])) for order in self.api.get_open_orders()['result']]

    def cancel_orders(self, orders = None):
        if orders is None:
            orders = self.query_active_orders()
        for order in orders:
            self.api.cancel(uuid=order.id)

    def start(self):
        self.reconnect()

    def stop(self):
        self.bm.disconnect()
        self.depths = {}

    def reconnect(self):
        self.tickers = []
        for pair in self.get_tradeable_pairs():
            pairstr = self.format_pair(pair)
            self.tickers.append(pairstr)
            self.depths[pairstr] = {'bids': [], 'asks': []}
        self.bm.subscribe_to_orderbook(self.depths, self.tickers)