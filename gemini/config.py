import tempfile

def setDefaultConfig():
    global MODE, IS_SERVICE, EXCHANGES, BLACKLIST, PAIRS, APIKEY_DIR, LOG_DIR, LOG_FILENAME, TICK_TIME, TARGET_FILE, CRASH_FILE, STATE_FILE
    global MAX_BIDASK_SPREAD_PCT, NB_PRICE_DECIMALS, NB_VOLUME_DECIMALS, MIN_VOL, MAX_VOL, TRADING_UNIT, RESIDUAL_AMOUNT, LARGE_UNIT, MIN_PROFIT
    global MIN_REBALANCING_PROFIT, MIN_ORDERBOOK_VOLUME, PROFIT_ADJUSTMENT, PROFIT_ADJUSTMENT_REBALANCING
    global NO_REBALANCING_EXCHANGES, SIMULATION_BALANCES
    global BINANCE_KEYFILE, HITBTC_KEYFILE, BITFINEX_KEYFILE, CEX_KEYFILE, BITTREX_KEYFILE

    MODE = 'TEST' # exchange and strategy configuration: LIVE or TEST
    IS_SERVICE = True
    EXCHANGES = ['BITFINEX', 'BINANCE', 'HITBTC', 'BITTREX']
    BLACKLIST = []
    PAIRS = [               ("ETH","BTC"),  ("XRP", "BTC"), ("LTC", "BTC"), ("XVG", "BTC"), ("IOTA", "BTC"), ("TRX", "BTC"), ("NEO", "BTC"), ("DASH", "BTC"), ("EOS", "BTC"), ("XLM", "BTC"), ("XMR", "BTC"),
                                            ("XRP", "ETH"), ("LTC", "ETH"), ("XVG", "ETH"), ("IOTA", "ETH"), ("TRX", "ETH"), ("NEO", "ETH"), ("DASH", "ETH"), ("EOS", "ETH"), ("XLM", "ETH"), ("XMR", "ETH"),
             ("BTC","USDT"),("ETH","USDT"),("XRP", "USDT"), ("LTC", "USDT"),("XVG", "USDT"),("IOTA", "USDT"),("TRX", "USDT"),("NEO", "USDT"),("DASH", "USDT"),("EOS", "USDT"),("XLM", "USDT"),("XMR", "USDT")]
    APIKEY_DIR = "C:\\Keys"
    LOG_DIR = tempfile.gettempdir()
    LOG_FILENAME = "cryptobot_session.txt"
    TICK_TIME = 1 # waiting time between two scans (sec)
    TARGET_FILE = "C:\\inetpub\\midax\\target.json"
    CRASH_FILE = "C:\\inetpub\\midax\\crash.json"
    STATE_FILE = "C:\\inetpub\\midax\\state.json"
    MAX_BIDASK_SPREAD_PCT ={
                 'BINANCE':{'DEFAULT': 0.5, 'XVG_BTC': 1.0},
                 'HITBTC':{'DEFAULT': 0.75, 'XVG_BTC': 5.0, 'XRP_ETH': 2.5, 'TRX_BTC': 1.5, 'XRP_BTC': 1.5},
                 'CEX':{'DEFAULT': 1.5},
                 'DEFAULT':{'BTC': 0.5, 'ETH': 1.0, 'USDT': 0.75},
                 }

    NB_PRICE_DECIMALS ={
                 'DEFAULT':8,
                 'ETH_BTC':{'DEFAULT':6, 'BITTREX':8},
                 'LTC_BTC':{'DEFAULT':5, 'BINANCE':6, 'BITTREX':8},
                 'NEO_BTC':{'DEFAULT':6, 'BITTREX':8},
                 'DASH_BTC':{'DEFAULT':6, 'BITTREX':8},
                 'XMR_BTC':{'DEFAULT':6, 'BITTREX':8, 'HITBTC':8},
                 'EOS_BTC':{'DEFAULT':8, 'BINANCE':7},
                 'DASH_ETH':{'DEFAULT':6, 'BINANCE':5, 'BITTREX':8},
                 'LTC_ETH':{'DEFAULT':5, 'HITBTC':3, 'BITTREX':8},
                 'EOS_ETH':{'DEFAULT':6, 'BITTREX':8},
                 'NEO_ETH':{'DEFAULT':6, 'BITFINEX':4, 'HITBTC':4, 'BITTREX':8},
                 'XVG_ETH':{'DEFAULT':8, 'BITTREX':8, 'HITBTC':7},
                 'XMR_ETH':{'DEFAULT':8, 'BINANCE':5},
                 'BTC_USDT':{'DEFAULT':2, 'BITTREX':8},
                 'ETH_USDT':{'DEFAULT':2, 'BITTREX':8},
                 'XRP_USDT':{'DEFAULT':4, 'BITTREX':8},
                 'LTC_USDT':{'DEFAULT':2, 'HITBTC':3, 'BITFINEX':1, 'BITTREX':8},
                 'XVG_USDT':{'DEFAULT':6, 'BITTREX':8},
                 'IOTA_USDT':{'DEFAULT':3, 'BITTREX':8},
                 'TRX_USDT':{'DEFAULT':6, 'BITTREX':8, 'HITBTC':5},
                 'NEO_USDT':{'DEFAULT':3, 'BITFINEX':2, 'BITTREX':8, 'HITBTC':2},
                 'DASH_USDT':{'DEFAULT':1, 'BITTREX':8, 'HITBTC':2},
                 'EOS_USDT':{'DEFAULT':3, 'BITTREX':8, 'HITBTC':5},
                 'XMR_USDT':{'DEFAULT':2}
                 }

    NB_VOLUME_DECIMALS = {
                 'DEFAULT':2,
                 'ETH_BTC':3,
                 'LTC_BTC':1,
                 'XMR_BTC':3,
                 'XMR_ETH':3,
                 'BTC_USDT':6,
                 'ETH_USDT':5,
                 'LTC_USDT':1,
                 'XMR_USDT':3}

    # minimum volume to trigger a transaction
    MIN_VOL = {
                 'BTC':0.03,
                 'ETH':0.3,
                 'LTC':0.5,
                 'USDT':200,
                 'XVG':3000,
                 'XRP':300,
                 'IOTA':200,
                 'TRX':3000,
                 'NEO':2.0,
                 'DASH':0.5,
                 'EOS':30,
                 'XLM':500,
                 'XMR':0.7
                 }
    # transaction volume cap, uncapped if None
    MAX_VOL = {
                 'BTC':0.3,
                 'ETH':4.0,
                 'LTC':3.0,
                 'USDT':2000,
                 'XVG':22000,
                 'XRP':3000,
                 'IOTA':2000,
                 'TRX':22000,
                 'NEO':20,
                 'DASH':3,
                 'EOS':300,
                 'XLM':2000,
                 'XMR':4
                 }
    # trading quantities have to be rounded to certain units
    TRADING_UNIT = {
                 'BTC': 0.0001,
                 'ETH': 0.001,
                 'LTC': 0.1,
                 'USDT': 1,
                 'XVG': 1000,
                 'XRP': 1,
                 'IOTA': 1,
                 'TRX': 1000,
                 'NEO': 0.01,
                 'DASH': 0.01,
                 'EOS': 1,
                 'XLM': 1,
                 'XMR': 0.01
                 }

    # to make sure we do not require too much balance because some exchanges charge the fee on the ccy, others on the market
    # we always keep max fee (currently 0.25%) * MAX_VOL
    MAX_FEE = 0.0025
    RESIDUAL_AMOUNT = {'BTC': MAX_FEE * MAX_VOL['BTC'],
                        'ETH': MAX_FEE * MAX_VOL['ETH'],
                        'USDT': MAX_FEE * MAX_VOL['USDT']}

    # in large unit ccy trading we distibute all the profits into BTC/ETH
    LARGE_UNIT = ['XVG', 'TRX', 'LTC']

    # Minimum profit target
    MIN_PROFIT = 0.0000002
    MIN_REBALANCING_PROFIT = 0.0000001

    # Minimum volume for orders in the order book
    MIN_ORDERBOOK_VOLUME = 0.00001

    # Reduce profit to raise the chances of an instantaneous deal
    PROFIT_ADJUSTMENT = 0.001
    PROFIT_ADJUSTMENT_REBALANCING = 2.0

    # list of exchanges where withdraw is not supported by the API. we therefore exclude them from trade reabalancing
    NO_REBALANCING_EXCHANGES = ['CEX']

    # simulation portfolio. each exchange starts with this balance
    SIMULATION_BALANCES = {
                 'BTC':1.0,
                 'ETH':10.0,
                 'LTC':50.0,
                 'USDT':10000.0,
                 'XVG':50000,
                 'XRP':5000,
                 'IOTA':3000,
                 'TRX':50000,
                 'NEO':50,
                 'DASH':5,
                 'EOS':500,
                 'XLM':2000,
                 'XMR':10
                 }

    # API key files
    BINANCE_KEYFILE = "binance_key.txt"
    HITBTC_KEYFILE = "hitbtc_key.txt"
    BITFINEX_KEYFILE = "bitfinex_key.txt"
    CEX_KEYFILE = "cex_key.txt"
    BITTREX_KEYFILE = "bittrex_key.txt"

setDefaultConfig()