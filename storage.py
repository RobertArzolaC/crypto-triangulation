class LastPriceStorage:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._last_prices = {}
        return cls._instance

    def update_last_price(self, pair, last_price):
        self._last_prices[pair] = last_price

    def get_last_price(self, pair):
        return self._last_prices.get(pair)

    def get_state(self):
        return self._last_prices

    def clear(self):
        self._last_prices = {}
