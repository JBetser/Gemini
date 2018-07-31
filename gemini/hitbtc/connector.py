"""HitBTC Connector which pre-formats incoming data to the CTS standard."""

import logging
import time
import json
import hmac
import hashlib
from threading import Timer
from collections import defaultdict

from .wss import WebSocketConnectorThread
from .utils import response_types

log = logging.getLogger(__name__)


class HitBTCConnector(WebSocketConnectorThread):
    """Class to pre-process HitBTC data, before putting it on the internal queue.

    Data on the queue is available as a 3-item-tuple by default.

    Response items on the queue are formatted as:
        ('Response', 'Success' or 'Failure', (request, response))

    'Success' indicates a successful response and 'Failure' a failed one.
    ``request`` is the original payload sent by the
    client and ``response`` the related response object from the server.

    Stream items on the queue are formatted as:
        (method, symbol, params)

    You can disable extraction and handling by passing 'raw=True' on instantiation. Note that this
    will also turn off recording of sent requests, as well all logging activity.
    """

    def __init__(self, url=None, raw=None, stdout_only=False, silent=False, **conn_ops):
        """Initialize a HitBTCConnector instance."""
        url = url or 'wss://api.hitbtc.com/api/2/ws'
        super(HitBTCConnector, self).__init__(url, **conn_ops)
        self.books = defaultdict(dict)
        self.requests = {}
        self.raw = raw
        self.logged_in = False
        self.silent = silent
        self.stdout_only = stdout_only

    def put(self, item, block=False, timeout=None):
        """Place the given item on the internal q."""
        if not self.stdout_only:
            self.q.put(item, block, timeout)

    def echo(self, msg):
        """Print message to stdout if ``silent`` isn't True."""
        if not self.silent:
            print(msg)

    def _start_timers(self):
        """Reset and start timers for API connection."""
        self._stop_timers()

        # Automatically reconnect if we didnt receive data
        self.connection_timer = Timer(self.connection_timeout,
                                      self._connection_timed_out)
        self.connection_timer.start()

    def _stop_timers(self):
        """Stop connection timer."""
        if self.connection_timer:
            self.connection_timer.cancel()

    def _on_message(self, ws, message):
        """Handle and pass received data to the appropriate handlers."""

        self._stop_timer()
        if not self.raw:
            decoded_message = json.loads(message)
            if 'jsonrpc' in decoded_message:
                if 'result' in decoded_message or 'error' in decoded_message:
                    self._handle_response(decoded_message)
                else:
                    try:
                        method = decoded_message['method']
                        symbol = decoded_message['params'].pop('symbol')
                        params = decoded_message.pop('params')
                    except Exception as e:
                        self.log.exception(e)
                        self.log.error(decoded_message)
                        return
                    self._handle_stream(method, symbol, params)
        else:
            self.put(message)

    def _handle_response(self, response):
        """
        Handle JSONRPC response objects.

        Acts as a pre-sorting function and determines whether or not the response is an error
        message, or a response to a succesful request.
        """
        try:
            i_d = response['id']
        except KeyError as e:
            self.log.exception(e)
            self.log.error("An expected Response ID was not found in %s", response)
            raise

        try:
            if i_d not in self.requests:
                return
            request = self.requests.pop(i_d)
        except KeyError as e:
            log.exception(e)
            log.error("Could not find Request relating to Response object %s", response)
            raise

        if 'result' in response:
            self.put(('Response', 'Success', (request, response)))
        elif 'error' in response:
            self._handle_error(request, response)

    def _handle_error(self, request, response):
        """
        Handle Error messages.

        Logs the corresponding requests and the error code and error messages, and prints them to
        the screen.

        Finally, we'll put the response and its corresponding request on the internal queue for
        retrieval by the client.
        """
        err_message = "{code} - {message} - {description}!".format(**response['error'])
        err_message += " Related Request: %r" % request
        self.log.error(err_message)
        self.echo(err_message)
        self.put(('Response', 'Failure', (request, response)))

    def _handle_stream(self, method, symbol, params):
        """Handle streamed data."""
        self.put((method, symbol, params))

    def send(self, method, custom_id=None, **params):
        """
        Send the given Payload to the API via the websocket connection.

        :param method: JSONRPC method to call
        :param custom_id: custom ID to identify response messages relating to this request
        :param kwargs: payload parameters as key=value pairs
        """
        if not self._is_connected:
            self.echo("Cannot Send payload - Connection not established!")
            return
        payload = {'method': method, 'params': params, 'id': custom_id or int(10000 * time.time())}
        if not self.raw:
            self.requests[payload['id']] = payload
        self.log.debug("Sending: %s", payload)
        self.conn.send(json.dumps(payload))

    def authenticate(self, key, secret, basic=False, custom_nonce=None):
        """Login to the HitBTC Websocket API using the given public and secret API keys."""
        if basic:
            algo = 'BASIC'
            skey = secret
            payload = {'sKey': skey}
        else:
            algo = 'HS256'
            nonce = custom_nonce or str(round(time.time() * 1000))
            signature = hmac.new(secret.encode('UTF-8'), nonce.encode('UTF-8'), hashlib.sha256).hexdigest()
            payload = {'nonce': nonce, 'signature': signature}

        payload['algo'] = algo
        payload['pKey'] = key
        self.send('login', **payload)





