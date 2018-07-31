from .exchange import Exchange, ExchangeLogHandler
from .keyhandler import KeyHandler
from .order import Order
from .logger import Logger as log
from .cexio.rest_client import CEXRestClient
from .cexio.ws_client import CommonWebSocketClient, WebSocketClientSingleCallback, MessageRouter
from .cexio.messaging import RequestResponseFutureResolver
from .cexio.exceptions import ErrorMessage, InvalidMessage
from .cexio.cexapi import API
from asyncio import sleep, run_coroutine_threadsafe
import time, queue, copy, threading, _thread, logging, random, asyncio

class CEXLogHandler(ExchangeLogHandler):
	def __init__(self, xchg):
		super(CEXLogHandler, self).__init__(xchg)
	def emit(self, record):
		msg = self.format(record)
		if msg.startswith('Exception'):
			log.error(msg)
		super(CEXLogHandler, self).emit(record)

class WebSocketClientPublicData(CommonWebSocketClient):
	def __init__(self, _config, depths):
		super().__init__(_config)
		self.depths = depths

		def validator(message):
			try:
				result = message['ok']
				if result == 'ok':
					return message['data']
				elif result == 'error':
					raise ErrorMessage(message['data']['error'])
				else:
					error = InvalidMessage(message)
			except KeyError:
				error = InvalidMessage(message)
			raise error

		resolver = RequestResponseFutureResolver(name='', op_name_get_path='e',
												 key_set_path='oid', key_get_path='oid')

		async def sink(message):
			event = message['e']
			return event

		special_message_map = (
				({	'e': 'connected', },										self._on_connected),
				({	'ok': 'error', 'data': {'error': 'Please Login'}, },		self._on_not_authenticated),
				({	'e': 'ping', },												self._on_ping),
				({	'e': 'disconnecting', },									self._on_disconnecting),
                ({  'e': 'md', },                                               self.on_md)
			)
		router = MessageRouter(special_message_map) + sink
		self.set_router(router)
		self.set_resolver(resolver)
		self.__notification_future = None

	async def on_md(self, message):
		#log.info(message)
		data = message['data']
		pairstr = data['pair'].replace(':','-')
		self.depths[pairstr]['bids'] = [Order(float(o[0]), float(o[1]) / 1000000.0) for o in data['buy'][:10]]
			#log.info('bids')
			#log.info(data['buy'][:10])
		self.depths[pairstr]['asks'] = [Order(float(o[0]), float(o[1]) / 1000000.0) for o in data['sell'][:10]]
			#log.info('asks')
			#log.info(data['sell'][:10])
		return message

class CEX(Exchange):
	all_pairs = ("eth_btc", "xrp_btc", "dash_btc", "xlm_btc")

	def __init__(self, keyfile, loop, has_error):
		super(CEX, self).__init__(CEX.all_pairs, keyfile, loop, has_error)
		self.stop_updatebook_thread = False
		cex_logger = logging.getLogger("gemini.cexio")
		log_handler = CEXLogHandler(self)
		log_handler.setLevel(logging.INFO)
		cex_logger.addHandler(log_handler)
		self.trade_api = None
		if self.keyhandler is not None:
			username_key = list(self.keyhandler.getKeys())[0]
			username, key = username_key.split(',')
			secret = self.keyhandler.getSecret(username_key)
			config = {
            	'ws': {
            		'uri':		'wss://ws.cex.io/ws/',
            	},
            	'rest': {
            		'uri':		'https://cex.io/api/',
            	},
            	'authorize': False,
            	'auth': {
            		'user_id':	username,
            		'key':		key,
            		'secret':	secret,
            	},
            }
			self.trade_api = API(username, key, bytearray(secret, 'utf8'))
			self.api = WebSocketClientPublicData(config, self.depths)
		else:
			config = {
            	'ws': {
            		'uri':		'wss://ws.cex.io/ws/',
            	},
            	'rest': {
            		'uri':		'https://cex.io/api/',
            	},
            	'authorize': False
            }
			self.api = WebSocketClientPublicData(config, self.depths)
		self.name = 'CEX'
		self.trading_fee = 0.0023 + 0.0002 # degrade the profit target on CEX.io due to less liquidity
		self.start()
		self.reconnect()

	async def _force_disconnect(self):
		try:
			await sleep(random.randrange(24, 64))
			await self.api.ws.close()
		except Exception as ex:
			log.error("CEX: Exception at closing connection: {}".format(ex))
		self.start()
		self.reconnect()

	def format_pair(self, pair):
		return pair[0].upper() + "-" + pair[1].upper()

	def reconnect(self):
		self.indexed_depths = {}
		for pair in self.get_tradeable_pairs():
			pair = self.get_validated_pair(pair)
			if pair is None:
				continue
			pairstr = self.format_pair(pair)
			self.depths[pairstr] = {'bids': [], 'asks': []}
			self.indexed_depths[pairstr] = {'bids': {}, 'asks': {}}
			self.loop.run_until_complete(self.api.send_subscribe({"e": "subscribe", "rooms": ["pair-%s" % pairstr]}))

	def get_depth(self, base, alt):
		pairstr = self.format_pair((base, alt))
		if pairstr not in self.depths:
			return {'bids':[], 'asks':[]}
		bids = self.depths[pairstr]['bids']
		asks = self.depths[pairstr]['asks']
		# DEBUG - show best bid ask for each ccy pair
		#if len(bids) > 0 and len(asks) > 0:
		#	log.info("%s %s Highest bid: %.8g(%f), Lowest ask: %.8g(%f)" % (self.name, pairstr, bids[0].p, bids[0].v, asks[0].p, asks[0].v))
		return copy.copy(self.depths[pairstr])

	def get_ticker(self):
		tickers = {}
		for pair in self.get_tradeable_pairs():
			ticker = self.trade_api.ticker(pair[0] + '/' + pair[1])
			tickers[pair] = (ticker['bid'] + ticker['ask']) / 2.0
		return tickers

	def get_balance(self):
		return { ccy.upper() : float(balance['available']) for ccy, balance in self.trade_api.balance().items() if ccy not in ('timestamp', 'username') }

	def submit_order(self, pair, side, price, volume):
		order = None
		if side == "SELL":
			order = self.trade_api.place_order('sell', volume, price, '%s/%s' % (pair[0], pair[1]))
		elif side == "BUY":
			order = self.trade_api.place_order('buy', volume, price, '%s/%s' % (pair[0], pair[1]))
		else:
			raise RuntimeError("Unsupported order type: %s" % (side,))
		self.log_order(side, order)
		return Order(orderID=order['id'], price=price, volume=volume, type=side, pair=pair)

	def query_active_orders(self):
		orders = []
		for pair in self.trading_pairs:
			orders = orders + [Order(orderID=order['id'],
                                price=float(order['price']),
                                volume=float(order['pending']),
                                type=order['type'].upper(),
                                pair=pair) for order in self.trade_api.current_orders(pair[0] + '/' + pair[1]) if 'error' not in order]
		return orders

	def cancel_orders(self, orders = None):
		if orders is None:
			for order in self.query_active_orders():
				self.trade_api.cancel_order(order.id)
		else:
			for order in orders:
				self.trade_api.cancel_order(order.id)

	def start(self):
		self.loop.run_until_complete(self.api.run())

	def stop(self):
		self.stop_updatebook_thread = True