#!/usr/bin/env python
from setuptools import setup

setup(
    name='gemini',
    version='0.6.8',
    packages=['gemini'],
    description='Gemini is a crypto-currency exchange arbitrage algorithm',
    author='Jonathan Betser',
    license='AGPLv3',
    author_email='jonathan.betser@gmail.com',
    install_requires=['cryptography', 'requests', 'colorama', 'aiohttp', 'sortedcontainers', 'websockets', 'autobahn', 'wmi', 'signalr-client', 'cfscrape', 'events'],
    keywords='binance hitbtc bitfinex cexio exchange arbitrage bitcoin ethereum ripple btc eth xrp',
    classifiers=[
          'Intended Audience :: Developers',
          'License :: OSI Approved :: AGPLv3 License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)

setup(name='gemini-binance',
    version='0.1',
    packages=['gemini.binance'])

setup(name='gemini-bitfinex',
    version='0.1',
    packages=['gemini.bitfinex'])

setup(name='gemini-hitbtc',
    version='0.1',
    packages=['gemini.hitbtc'])

setup(name='gemini-cexio',
    version='0.1',
    packages=['gemini.cexio'])

setup(name='gemini-bittrex',
    version='0.1',
    packages=['gemini.bittrex'])