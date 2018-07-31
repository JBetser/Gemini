Gemini is a cryptocurrency arbitrage trading algorithm. 

How it works?

It scans exchange order books via websockets. Each exchange communication is handled in a dedicated thread.

Everytime there is an arbitrage opportunity between two order books, it fires a BUY and a SELL order simultaneously.

If an order is not fully executed it will attempt to clear the trade at mid-spread price. It can potentially make a significant loss if the market moves very quickly.

By default it simulates trades. If you wish to trade live (mode "LIVE"), trade at your own risks. There is no guarantee whatsoever that you will not make losses either because of a bug in the code or if the execution is too slow. In fact, you should always monitor the trading activity carefully, and adjust your profit target depending on the lags with the exchanges.

To trade live you need to provide api key files in APIKEY_DIR. The format is two lines:
- First line is the API key
- Second line is the secret key

Instructions for Windows (could be easily made compatible with Linux. TODO: test on Linux)
- Install or upgrade to Python 3.6.5+
- Install or upgrade to NodeJs 8.10.0+
- Make sure python 3.6 and nodejs are in your PATH. the following commands should return the right folders

where node

where python
- Install the following wheels:

pip install utils\wheels\pypiwin32-220-cp36-none-win_amd64.whl

pip install utils\wheels\Twisted-17.9.0-cp36-cp36m-win_amd64.whl
- Install the following certificates to the corresponding repository:

utils\cert\geotrust_primary_g3.crt -> Root CA

utils\cert\geotrust_intermediate_sha256.crt -> Intermediate CA
- Install the command prompt ansi support:

utils\ansi\ansicon.exe --i
- Install openssl for python:

pip install pyopenssl
- run install.cmd
- (optional) run run_tests.cmd
- run launch.cmd

Happy Trading! :-)

P.S.
Gemini is part of a broader project to achieve large scale high frequency trading in the crypto space. If you are interested in contributing please email me at jonathan.betser@gmail.com.

