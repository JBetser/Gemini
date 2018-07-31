# generic class for trading/market-watching bots

# here is where the pair arbitrage strategy is implemented
# along with the application loop for watching exchanges

from .logger import Logger as log
from .profit_calculator import ProfitCalculator
from .order import Order # Order class needs to be present for de-serialization of orders
from .controller import Controller
from .binanceapi import Binance
from .bitfinexapi import Bitfinex, BitfinexLogHandler
from .hitbtcapi import Hitbtc
from .cexioapi import CEX
from .bittrexapi import Bittrex
from .exchange import ExchangeLogHandler
import threading, os, time, asyncio, json, abc
from concurrent.futures import ThreadPoolExecutor
if os.name == 'nt':
    import wmi
import _pickle as pickle
from os.path import abspath
import logging, traceback

class Scheduler(object):
    trading_lock = threading.Lock()
    executor = ThreadPoolExecutor(max_workers=8)

    def __init__(self, config, name):
        """
        config = configuration file
        controllers = array of controller objects
        """
        super(Scheduler, self).__init__()
        self.config = config
        self.name = name
        self.error = [False]
        self.tick_count = 0
        self.read_target_file()
        self.loop = asyncio.new_event_loop()
        self.controllers = self.create_exchanges()
        # extra security. we make sure there is no zombie process running
        if os.name == 'nt':
            c = wmi.WMI ()
            for process in c.Win32_Process():
                if process.ProcessId is None:
                    continue
                if process.ProcessId == os.getpid():
                    continue
                if process.Name.lower() == 'python.exe':
                    err = "Another instance of Python is already running"
                    log.error(err)
                    raise RuntimeError(err)

    def create_exchanges(self):
        # returns an array of Controller objects
        try:
            controllers = []
            for name in self.config.EXCHANGES:
                if name in self.config.BLACKLIST:
                    log.ok('Exchange ' + name + ' is blacklisted!')
                    continue
                if (name == 'BINANCE'):
                    xchg = Binance(os.path.abspath(os.path.join(self.config.APIKEY_DIR, self.config.BINANCE_KEYFILE)), self.loop, self.error)
                elif (name == 'BITFINEX'):
                    xchg = Bitfinex(os.path.abspath(os.path.join(self.config.APIKEY_DIR, self.config.BITFINEX_KEYFILE)), self.loop, self.error)
                elif (name == 'HITBTC'):
                    xchg = Hitbtc(os.path.abspath(os.path.join(self.config.APIKEY_DIR, self.config.HITBTC_KEYFILE)), self.loop, self.error)
                elif (name == 'CEX'):
                    xchg = CEX(os.path.abspath(os.path.join(self.config.APIKEY_DIR, self.config.CEX_KEYFILE)), self.loop, self.error)
                elif (name == 'BITTREX'):
                    xchg = Bittrex(os.path.abspath(os.path.join(self.config.APIKEY_DIR, self.config.BITTREX_KEYFILE)), self.loop, self.error)
                else:
                    log.error('Exchange ' + name + ' not supported!')
                    continue
                log.ok('%s initialized' % (xchg.name))
                controllers.append(Controller(xchg))
            return controllers
        except Exception as exc:
            log.error(traceback.format_exc())
            self.error[0] = True
        return []

    def get_balances(self, label = 'balances'):
        # retrieves specified balances held across all controllers
        assets = {}
        for controller in self.controllers:
            if getattr(controller, label) is None:
                continue
            for currency, balance in getattr(controller, label).items():
                if currency in assets:
                    assets[currency] += balance
                elif balance != 0.0:
                    assets[currency] = balance
        return assets

    def read_target_file(self):
        try:
            with open(self.config.TARGET_FILE, "r") as f:
                tgt_dict = json.loads(f.readline())
                if tgt_dict["target"] != "DEFAULT":
                    self.config.MIN_PROFIT = float(tgt_dict["target"]) / 100.0
                    log.ok("New target: %.4g pct" % (self.config.MIN_PROFIT * 100,))
                if "exclude" in tgt_dict:
                    self.config.BLACKLIST = [xcgh.upper() for xcgh in tgt_dict["exclude"].split(',')]
                    log.ok("Blacklisted exchanges: %s" % (tgt_dict["exclude"],))
            os.remove(self.config.TARGET_FILE)
        except FileNotFoundError:
            pass
        except Exception as exc:
            log.error(traceback.format_exc())

    def log_assets(self):
        log.ok("Portfolio balances: %s" % (str(self.get_balances()),))

    def start(self):
        sleep = self.config.TICK_TIME
        self.pairs = {}
        self.nb_pairs = 0
        self.init = False
        try:
            if os.path.isfile(self.config.STATE_FILE):
                # gemini is recovering from a crash, there might be a state to recover
                state_json = {}
                with open(self.config.STATE_FILE, "r") as fs:
                    contents = json.load(fs)
                    if contents and len(contents) > 0:
                        state_json = contents
                for controller in self.controllers:
                    if controller.xchg.name in state_json:
                        for key, value in state_json[controller.xchg.name].items():
                            if key == 'orders':
                                trades = {order['id']: Order(order['p'],order['v'],order['type'],order['pair'].split('_'),order['id']) for order in value}
                                for trade in trades.values():
                                    log.info('Recovering a trade from previous crash: %s' % (str(trade),))
                                setattr(controller, key, trades)
                            elif key == 'to_resubmit_orders':
                                trades = [Order(order['p'],order['v'],order['type'],order['pair'].split('_'),order['id']) for order in value]
                                for trade in trades:
                                    log.ok('Recovering a pending trade from previous crash: %s' % (str(trade),))
                                setattr(controller, key, trades)
                            else:
                                log.info('Recovering %s state from previous crash: %s = %s' % (controller.xchg.name, key, str(value)))
                                setattr(controller, key, value)
                os.remove(self.config.STATE_FILE)
        except Exception as exc:
            log.error(traceback.format_exc())

        try:
            # initialization
            for controller in self.controllers:
                self.pairs[controller] = []
                for pair in self.config.PAIRS:
                    if controller.xchg.get_validated_pair(pair) is not None:
                        self.pairs[controller].append(pair)
                        self.nb_pairs = self.nb_pairs + 1

            # run
            asyncio.set_event_loop(self.loop)
            start = time.time()
            last_tick = start - sleep
            while not self.error[0]:
                delta = time.time() - last_tick
                if (delta < sleep):
                    # sleep for the remaining seconds
                    time.sleep(sleep-delta)
                self.tick()
                last_tick = time.time()

            # crash
            log.error('Gemini stopped due to a critical error')

            # dump a crash file for the observer
            # pass the error the state of balances to restore the session
            with open(self.config.CRASH_FILE, "w") as f:
                state = {}
                for controller in self.controllers:
                    state[controller.xchg.name] = {'offline_balances':{}, 'initial_balances':{}}
                    for key, value in controller.offline_balances.items():
                        state[controller.xchg.name]['offline_balances'][key] = value
                    for key, value in controller.initial_balances.items():
                        state[controller.xchg.name]['initial_balances'][key] = value
                    if len(controller.orders) > 0:
                        state[controller.xchg.name]['orders'] = []
                        for order in controller.orders.values():
                            state[controller.xchg.name]['orders'].append(order.to_dict())
                    if len(controller.to_resubmit_orders) > 0:
                        state[controller.xchg.name]['to_resubmit_orders'] = []
                        for order in controller.to_resubmit_orders:
                            state[controller.xchg.name]['to_resubmit_orders'].append(order.to_dict())
                json.dump({'error': log.last_error, 'state': state}, f)
        except FileNotFoundError:
            log.error('Cannot write crash file. Path not found: ' + self.config.CRASH_FILE)
        except Exception as exc:
            log.error(traceback.format_exc())
        finally:
            self.stop()
            for controller in self.controllers:
                controller.shutdown()

    def stop(self):
        self.loop.close()

    def check_active_orders(self, bidder, asker):
        if asker.check_active_orders() or bidder.check_active_orders():
            return True
        return False

    def get_calculator(self, pair):
        return ProfitCalculator(self.controllers, pair)

    def trade_pair(self, pair, control_state):
        if self.error[0]:
            return
        base, alt = pair
        pc = self.get_calculator(pair)
        if pc.check_profits():
            (bidder, asker, profit_obj) = pc.get_best_trade()
            if profit_obj is not None:
                bidder_order = profit_obj["bidder_order"]
                asker_order = profit_obj["asker_order"]
                trade_type = 'Rebalancing' if profit_obj["rebalancing"] else 'Arbitrage'
                if not self.check_active_orders(bidder, asker):
                    with Scheduler.trading_lock:
                        if not self.check_active_orders(bidder, asker):
                            bidder.has_active_orders = True
                            asker.has_active_orders = True
                            self.perform_arbitrage(control_state, pair, bidder, asker, bidder_order, asker_order)
                            log.ok('%s %s: Bought %f %s for %.8g %s from %s and sell %f %s for %.8g %s at %s. Profit : %.8g%s (%fpct)' %
                                      (self.name, trade_type, asker_order.v,base,asker_order.p* asker_order.v,alt,asker.xchg.name,
                                       bidder_order.v,base,bidder_order.p * bidder_order.v,alt,bidder.xchg.name,profit_obj["profit"],alt,profit_obj["profit_pct"]))
                            log.info('%s Updated balances: %s' % (bidder.xchg.name, str({key:val for key, val in bidder.balances.items() if val != 0})))
                            log.info('%s Offline balances: %s' % (bidder.xchg.name, str({key:val for key, val in bidder.offline_balances.items() if val != 0})))
                            log.info('%s Updated balances: %s' % (asker.xchg.name, str({key:val for key, val in asker.balances.items() if val != 0})))
                            log.info('%s Offline balances: %s' % (asker.xchg.name, str({key:val for key, val in asker.offline_balances.items() if val != 0})))
        else:
            if pc.error:
                self.error[0] = True
        control_state[0] = control_state[0] - 1
        if control_state[0] == 0:
            self.loop.stop()

    def tick(self):
        try:
            # new cycle
            if self.tick_count == 5000:
                log.info('5000 ticks')
                self.tick_count = 0

            # update the order books
            if self.tick_count > 5 or self.init:
                control_state = [self.nb_pairs]
                for controller in self.controllers:
                    for pair in self.pairs[controller]:
                        asyncio.ensure_future(self.loop.run_in_executor(Scheduler.executor, controller.update_depth, self.loop, control_state, pair))
                self.loop.run_forever()
                if self.error[0]:
                    return

            # look for trade opportunities
            if self.tick_count > 10 or self.init:
                if not self.init:
                    self.init = True
                    log.info("Gemini is initialized")
                control_state = [len(self.config.PAIRS)]
                for pair in self.config.PAIRS:
                    asyncio.ensure_future(self.loop.run_in_executor(Scheduler.executor, self.trade_pair, pair, control_state))
                self.loop.run_forever()
                if self.error[0]:
                    return

            # update balances and active orders
            if self.init and self.tick_count % 25 == 0:
                for controller in self.controllers:
                    for pair in self.pairs[controller]:
                        if controller.bad_prices[pair] >= 3:
                            self.error[0] = True
                            return
                check_order_book = self.tick_count % 100 == 0
                control_state = [len(self.controllers)]
                if check_order_book:
                    tickers = {}
                    for controller in self.controllers:
                        tickers[controller.xchg.name] = {}
                        asyncio.ensure_future(self.loop.run_in_executor(Scheduler.executor, controller.get_tickers, self.loop, control_state, tickers[controller.xchg.name]))
                    self.loop.run_forever()
                    control_state = [self.nb_pairs]
                    for controller in self.controllers:
                        for pair in self.pairs[controller]:
                            asyncio.ensure_future(self.loop.run_in_executor(Scheduler.executor, controller.validate_order_book, self.loop, control_state, pair, tickers[controller.xchg.name]))
                else:
                    check_balances = self.tick_count % 50 == 0
                    for controller in self.controllers:
                        if check_balances:
                            asyncio.ensure_future(self.loop.run_in_executor(Scheduler.executor, controller.update_all_balances, self.loop, control_state))
                        else:
                            asyncio.ensure_future(self.loop.run_in_executor(Scheduler.executor, controller.query_active_orders, self.loop, control_state))
                self.loop.run_forever()
                if self.error[0]:
                    return
                new_balance_detected = False
                for controller in self.controllers:
                    if controller.new_balance_detected:
                        new_balance_detected = True
                        controller.new_balance_detected = False
                if new_balance_detected:
                    self.log_assets()
        finally:
            self.loop.call_soon(self.read_target_file)
            self.tick_count = self.tick_count + 1

    def perform_arbitrage(self, control_state, pair, bidder, asker, bidder_order, asker_order):
        base, alt = pair
        # sanity check: negative balances
        if bidder.balances[base] - bidder_order.v < 0 or asker.balances[alt] - asker_order.p * asker_order.v < 0:
            if bidder.balances[base] - bidder_order.v < 0:
                log.error('%s arbitrage aborted due to negative balance: %.8g%s' % (bidder.xchg.name, bidder.balances[base] - bidder_order.v, base))
            else:
                log.error('%s arbitrage aborted due to negative balance: %.8g%s' % (asker.xchg.name, asker.balances[alt] - asker_order.p * asker_order.v, alt))
            return
        # sanity check: ALT coins +-10%, BTC/ETH +-15% their initial amounts
        initial_balances = self.get_balances('initial_balances')
        offline_balances = self.get_balances('offline_balances')
        if offline_balances[base] < 0.9 * initial_balances[base]:
            log.error('%s low balance: %.8g%s initial balance: %.8g' % (bidder.xchg.name, offline_balances[base], base, initial_balances[base]))
            return
        if offline_balances[alt] > 1.15 * initial_balances[alt]:
            log.error('%s high balance: %.8g%s initial balance: %.8g' % (asker.xchg.name, offline_balances[alt], alt, initial_balances[alt]))
            return
        if offline_balances[alt] < 0.85 * initial_balances[alt]:
            log.error('%s low balance: %.8g%s initial balance: %.8g' % (asker.xchg.name, offline_balances[alt], alt, initial_balances[alt]))
            return
        if offline_balances[base] > 1.1 * initial_balances[base]:
            log.error('%s high balance: %.8g%s initial balance: %.8g' % (bidder.xchg.name, offline_balances[base], base, initial_balances[base]))
            return
        bidder.balances[base] -= bidder_order.v
        asker.balances[alt] -= asker_order.p * asker_order.v
        control_state[0] = control_state[0] + 2
        asyncio.ensure_future(self.loop.run_in_executor(Scheduler.executor, asker.async_submit_order, self.loop, control_state, pair, "BUY", asker_order.p, asker_order.v))
        asyncio.ensure_future(self.loop.run_in_executor(Scheduler.executor, bidder.async_submit_order, self.loop, control_state, pair, "SELL", bidder_order.p, bidder_order.v))
