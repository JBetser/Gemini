# HitBtc API Class
# Developed by jmarcolan in Python 3.5.4 64 bit
# https://github.com/jmarcolan/HitBTC_Api
# if you like
# donate ETH: 0xb641e28C20574E968EB18dadd5060c33083a6b45
# donate BTC: 17tzJPnyJMsW2TRSi4TCTQ4YSawB6JkZU7

'''
API Documentation:
 * Public API v1 (https://hitbtc.com/api#marketrestful)
 * Trade API v2 (https://github.com/hitbtc-com/hitbtc-api/blob/master/APIv2.md)
'''
import json
import requests
import datetime
import hashlib
import hmac
import random
import string
import time
import http.client
import urllib.parse
import urllib.request


# class public api from hitBtc
class public_api(object):
    def __init__(self):
        self.url = 'http://api.hitbtc.com'
        self.conn = http.client.HTTPSConnection('api.hitbtc.com')

    # function to return serv time
    def time(self):
        response = requests.get(self.url + "/api/1/public/time")
        # print(response.content)
        return response.json()

    def symbols(self):
        response = requests.get(self.url + "/api/1/public/symbols")
        print(response.content)
        return response.json()

    # function to return ticker information
    # @pair = Trading symbol (e.g. ETHUSD)
    def ticker(self, tpair):
        response = requests.get(self.url + "/api/1/public/" + tpair + "/ticker")
        #print(response.content)
        return response.json()

    # function to return all ticker information
    def tickers(self):
        response = requests.get(self.url + "/api/1/public/ticker")
        #print(response.content)
        return response.json()

    # function to return orderbook
    # @pair = Trading symbol (e.g. ETHUSD)
    def orderbook(self, tpair):
        response = requests.get(self.url + "/api/1/public/" + tpair + "/orderbook")
        #print(response.content)
        return response.json()

    # function to get lasts trades
    # @pair = Trading symbol (e.g. ETHUSD)
    def trades(self, tpair):
        response = requests.get(self.url + "/api/1/public/" + tpair + "/trades")
        #print(response.content)
        return response.json()


# class trade api from hitBtc
class trade_api:
    def __init__(self, apiKey, apiSecret):
        self.key = apiKey
        self.secret = apiSecret
        self.nonce = self.rand()
        self.url = "https://api.hitbtc.com"

    # function to create a unique value
    def rand(self):
        return str(int(time.mktime(datetime.datetime.now().timetuple()) * 1000 + datetime.datetime.now().microsecond / 1000))

    #function return balance from all coins
    def balance(self):
        response = requests.get(self.url+'/api/2/trading/balance', auth=(self.key, self.secret))
        #print(r.json())
        return response.json()

    #function to set new order
    #@pair = Trading symbol
    #@transaction = tipe of transaction (sell or buy)
    #@price = trade price
    #@quantity = trade quantity
    def new_order(self,tpair,transaction, quantity, price):
        orderData = {'symbol': tpair, 'side': transaction.lower(), 'quantity': quantity, 'price': price }
        response = requests.post(self.url+'/api/2/order', data = orderData, auth=(self.key, self.secret))
        #print(r.json())
        return response.json()

    #function to cancel orders
    #@pair = Trading symbol
    def cancel_orders(self, tpair=None):
        orderData = {'symbol': tpair}
        response = requests.delete(self.url+'/api/2/order', data = orderData, auth=(self.key, self.secret))
        #print(r.json())
        return response.json()

    #function to cancel an order
    #@pair = Trading symbol
    def cancel_order(self, order_id):
        orderData = {'id': order_id}
        response = requests.delete(self.url+'/api/2/order', data = orderData, auth=(self.key, self.secret))
        #print(r.json())
        return response.json()

    #function to cancel orders
    #@pair = Trading symbol
    def active_orders(self, tpair=None):
        orderData = {'symbol': tpair}
        response = requests.get(self.url+'/api/2/order', data = orderData, auth=(self.key, self.secret))
        #print(r.json())
        return response.json()
