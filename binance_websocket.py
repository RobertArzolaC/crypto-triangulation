import json

import websocket

from constants import BINANCE_WEBSOCKET_URL
from logger import CryptoLogger


logger = CryptoLogger(__name__)


class BinanceWebSocket:
    def __init__(self, pairs):
        self.pairs = pairs
        self.socket = None
        self.observers = []
        self.url = BINANCE_WEBSOCKET_URL

    def register_observer(self, observer):
        self.observers.append(observer)

    def unregister_observer(self, observer):
        self.observers.remove(observer)

    def notify_observers(self, data):
        for observer in self.observers:
            observer.update(data)

    def _get_pairs_uri(self):
        params = [f"{pair.lower()}@bookTicker" for pair in self.pairs]
        return "/".join(params)

    def start(self):
        pairs_uri = self._get_pairs_uri()
        self.url += pairs_uri
        self.socket = websocket.WebSocketApp(
            self.url, on_message=self.on_message, on_error=self.on_error
        )
        logger.info("Starting handle for websocket ...")
        self.socket.run_forever(reconnect=15)

    def on_message(self, ws, message):
        data = json.loads(message)
        self.notify_observers(data)

    def on_error(self, ws, error):
        logger.error(f"Error on websocket: {error}")
