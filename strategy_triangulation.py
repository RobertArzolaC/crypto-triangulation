from abc import ABC, abstractmethod

from constants import (
    BTCUSDT, ETHUSDT, ETHBTC, RIGHT_TRIANGLE_STRATEGY,
    LEFT_TRIANGLE_STRATEGY, LOG_FILE_PATH
)
from logger import CryptoLogger


logger = CryptoLogger(__name__, file_path=LOG_FILE_PATH)


class Strategy(ABC):

    def __init__(self, pairs_data, name, fees=0.999, min_profit=0.05):
        self.name = name
        self.fees = fees
        self.profit = 0.0
        self._last_prices = {}
        self.min_profit = min_profit
        self.parsed_pairs_data(pairs_data)
        self.is_profitable = self.is_profitable()

    @abstractmethod
    def parsed_pairs_data(self, pairs_data):
        pass

    @abstractmethod
    def is_profitable(self):
        pass

    def get_last_prices(self):
        return self._last_prices

    def show_profit(self):
        base_message = f"Profit[{self.name}]"
        logger.info(f"{base_message}: {self.profit}% > {self.min_profit}%")


class RightTriangleStrategy(Strategy):

    def __init__(self, pairs_data):
        super().__init__(pairs_data, RIGHT_TRIANGLE_STRATEGY)

    def parsed_pairs_data(self, pairs_data):
        btcusdt_bid = round(float(pairs_data[BTCUSDT]["b"]), 2)
        btcusdt_volume = round(float(pairs_data[BTCUSDT].get('B')), 5)
        usdt_quantity = round(float(btcusdt_bid * self.fees), 8)
        self._last_prices[BTCUSDT] = dict(
            bid=btcusdt_bid, volume=btcusdt_volume, quantity=usdt_quantity
        )

        ethusdt_ask = round(float(pairs_data[ETHUSDT].get('a')), 2)
        ethusdt_volume = round(float(pairs_data[ETHUSDT].get('A')), 4)
        eth_quantity = round(float((usdt_quantity/ethusdt_ask) * self.fees), 8)
        self._last_prices[ETHUSDT] = dict(
            ask=ethusdt_ask, volume=ethusdt_volume, quantity=eth_quantity
        )

        ethbtc_bid = round(float(pairs_data[ETHBTC].get('b')), 6)
        ethbtc_volume = round(float(pairs_data[ETHBTC].get('B')), 4)
        btc_quantity = round(float(ethbtc_bid * eth_quantity * self.fees), 8)
        self._last_prices[ETHBTC] = dict(
            bid=ethbtc_bid, volume=ethbtc_volume, quantity=btc_quantity
        )

    def is_profitable(self):
        ethbtc_quantity = self._last_prices[ETHBTC]['quantity']
        self.profit = round(float((ethbtc_quantity - 1) * 100), 2)
        return self.profit > self.min_profit


class LeftTriangleStrategy(Strategy):

    def __init__(self, pairs_data):
        super().__init__(pairs_data, LEFT_TRIANGLE_STRATEGY)

    def parsed_pairs_data(self, pairs_data):
        ethbtc_ask = round(float(pairs_data[ETHBTC].get('a')), 6)
        ethbtc_volume = round(float(pairs_data[ETHBTC].get('A')), 4)
        eth_quantity = round(float(self.fees/ethbtc_ask), 8)
        self._last_prices[ETHBTC] = dict(
            ask=ethbtc_ask, volume=ethbtc_volume, quantity=eth_quantity
        )

        ethusdt_bid = round(float(pairs_data[ETHUSDT].get('b')), 2)
        ethusdt_volume = round(float(pairs_data[ETHUSDT].get('B')), 4)
        usdt_quantity = round(float(ethusdt_bid * eth_quantity * self.fees), 8)
        self._last_prices[ETHUSDT] = dict(
            bid=ethusdt_bid, volume=ethusdt_volume, quantity=usdt_quantity
        )

        btcusdt_ask = round(float(pairs_data[BTCUSDT].get('a')), 2)
        btcusdt_volume = round(float(pairs_data[BTCUSDT].get('A')), 5)
        btc_quantity = round(float((usdt_quantity/btcusdt_ask) * self.fees), 8)
        self._last_prices[BTCUSDT] = dict(
            ask=ethusdt_bid, volume=btcusdt_volume, quantity=btc_quantity
        )

    def is_profitable(self):
        ethbtc_quantity = self._last_prices[BTCUSDT]['quantity']
        self.profit = round(float((ethbtc_quantity - 1) * 100), 2)
        return self.profit > self.min_profit
