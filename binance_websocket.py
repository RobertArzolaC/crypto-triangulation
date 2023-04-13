import json

import websocket


class BinanceWebSocket:
    def __init__(self, pairs):
        self.pairs = pairs
        self.socket = None
        self.observers = []

    def register_observer(self, observer):
        self.observers.append(observer)

    def unregister_observer(self, observer):
        self.observers.remove(observer)

    def notify_observers(self, data):
        for observer in self.observers:
            observer.update(data)

    def get_pairs_path(self):
        params = []
        for pair in self.pairs:
            params.append(pair.lower() + "@bookTicker")
        return "/".join(params)

    def start(self):
        url = "wss://stream.binance.com:9443/ws/"
        pairs_path = self.get_pairs_path()
        url += pairs_path
        self.socket = websocket.WebSocketApp(
            url, on_message=self.on_message, on_error=self.on_error
        )
        self.socket.run_forever(reconnect=15)

    def on_message(self, ws, message):
        data = json.loads(message)
        self.notify_observers(data)

    def on_error(self, ws, error):
        print("error: ", error)
