from .exchange import Exchange, ExchangeLogHandler
from .order import Order
from .logger import Logger as log
from .binance.client import Client
from .binance.websockets import BinanceSocketManager, BinanceClientDefaultFactory
from functools import partial
import logging

class BinanceCustomFactory(BinanceClientDefaultFactory):

    def __init__(self, xchg, symbol):
        super(BinanceCustomFactory, self).__init__(symbol)
        self.xchg = xchg

    def clientConnectionFailed(self, connector, reason):
        log.error('Binance connection failed')
        self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        # check if closed cleanly
        log.error('Binance connection lost: ' + reason.getErrorMessage())
        self.xchg.reconnect()
        if reason.getErrorMessage() != 'Connection was closed cleanly.':
            self.retry(connector)

class Binance(Exchange):
    all_pairs = ("eth_btc", "xrp_btc", "ltc_btc", "xvg_btc", "iota_btc", "trx_btc", "neo_btc", "dash_btc", "eos_btc", "xlm_btc", "xmr_btc",
                            "xrp_eth", "ltc_eth", "xvg_eth", "iota_eth", "trx_eth", "neo_eth", "dash_eth", "eos_eth", "xlm_eth", "xmr_eth",
      "btc_usdt","eth_usdt",           "ltc_usdt",                                  "neo_usdt")

    def __init__(self, keyfile, loop, has_error):
        super(Binance, self).__init__(Binance.all_pairs, keyfile, loop, has_error)
        binance_logger = logging.getLogger("gemini.binance")
        log_handler = ExchangeLogHandler(self)
        log_handler.setLevel(logging.INFO)
        binance_logger.addHandler(log_handler)
        self.api = None
        if self.keyhandler is not None:
            key = list(self.keyhandler.getKeys())[0]
            api_secret = self.keyhandler.getSecret(key)
            self.api = Client(key, api_secret)
        self.name = 'BINANCE'
        self.trading_fee = 0.001
        self.bm = BinanceSocketManager(self.api)
        self.reconnect()
        self.start()

    def format_pair(self, pair):
        return pair[0].upper() + pair[1].upper()

    def process_message(self, pairstr, msg):
        self.depths[pairstr] = { 'bids' : [Order(float(o[0]), float(o[1])) for o in msg['bids']],
                                    'asks' : [Order(float(o[0]), float(o[1])) for o in msg['asks']]}

    def get_depth(self, base, alt):
        pairstr = self.format_pair((base, alt))
        # DEBUG - show best bid ask for each ccy pair
        #if len(self.depths[pairstr]['bids']) > 0 and len(self.depths[pairstr]['asks']) > 0:
        #    log.info("%s %s Highest bid: %.8g, Lowest ask: %.8g" % (self.name, pairstr, self.depths[pairstr]['bids'][0].p, self.depths[pairstr]['asks'][0].p))
        return self.depths[pairstr]

    def get_ticker(self):
        pairs = {self.format_pair(pair):pair for pair in self.get_tradeable_pairs()}
        tickers = {}
        for ticker in self.api.get_orderbook_ticker():
            if ticker['symbol'] in pairs:
                tickers[pairs[ticker['symbol']]] = (float(ticker['bidPrice']) + float(ticker['askPrice'])) / 2.0
        return tickers

    def get_balance(self):
        data = self.api.get_account()
        return {c["asset"].upper() : float(c["free"]) for c in data['balances']}

    def submit_order(self, pair, side, price, volume):
        pairstr = self.format_pair(pair)
        order = None
        if side == "SELL":
            order = self.api.create_order(symbol=pairstr, side=Client.SIDE_SELL, type=Client.ORDER_TYPE_LIMIT, price=price, quantity=volume, timeInForce=Client.TIME_IN_FORCE_GTC)
        elif side == "BUY":
            order = self.api.create_order(symbol=pairstr, side=Client.SIDE_BUY, type=Client.ORDER_TYPE_LIMIT, price=price, quantity=volume, timeInForce=Client.TIME_IN_FORCE_GTC)
        else:
            raise RuntimeError("Unsupported order type: %s" % (side,))
        self.log_order(side, order)
        return Order(orderID=order['orderId'], price=price, volume=volume, type=side, pair=pair)

    def query_active_orders(self):
        return [Order(orderID=order['orderId'],
                        price=float(order['price']),
                        volume=float(order['origQty']) - float(order['executedQty']),
                        type=order['side'],
                        pair=self.pair_from_symbol(order['symbol'])) for order in self.api.get_open_orders()]

    def cancel_orders(self, orders = None):
        if orders is None:
            for order in self.query_active_orders():
                self.api.cancel_order(order.id)
        else:
            for order in orders:
                self.api.cancel_order(orderId=str(order.id), symbol=self.format_pair(order.pair))

    def start(self):
        self.socket_key = self.bm.start()

    def stop(self):
        self.bm.stop_socket(self.socket_key)
        self.depths = {}
        log.info("Closed Binance websocket")

    def reconnect(self):
        for pair in self.get_tradeable_pairs():
            pairstr = self.format_pair(pair)
            self.depths[pairstr] = {'bids': [], 'asks': []}
            self.bm.start_depth_socket(symbol=pairstr, callback=partial(self.process_message, pairstr), depth=10, custom_factory=BinanceCustomFactory(self, pairstr))
        log.info("Connected to Binance websocket")