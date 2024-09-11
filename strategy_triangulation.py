from abc import ABC, abstractmethod

from constants import (
    FIRST_PAIR, SECOND_PAIR, THIRD_PAIR,
    RIGHT_TRIANGLE_STRATEGY, LEFT_TRIANGLE_STRATEGY, LOG_FILE_PATH
)
from logger import CryptoLogger


logger = CryptoLogger(__name__, file_path=LOG_FILE_PATH)


class Strategy(ABC):

    def __init__(self, pairs_data, name, fees=0.99, min_profit=0.01):
        self.name = name
        self.fees = fees
        self.profit = 0.0
        self._last_prices = {}
        self.min_profit = min_profit
        self.parsed_pairs_data(pairs_data)
        self.is_profitable = self.calculate_profit()

    @abstractmethod
    def parsed_pairs_data(self, pairs_data):
        pass

    @abstractmethod
    def calculate_profit(self):
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
        first_pair = pairs_data[FIRST_PAIR]
        second_pair = pairs_data[SECOND_PAIR]
        third_pair = pairs_data[THIRD_PAIR]

        self._last_prices[FIRST_PAIR] = self._parse_pair(first_pair, 'b', 'B')
        self._last_prices[SECOND_PAIR] = self._parse_pair(second_pair, 'a', 'A')
        self._last_prices[THIRD_PAIR] = self._parse_pair(third_pair, 'b', 'B')

        self._calculate_quantities()

    def _parse_pair(self, pair_data, price_key, volume_key):
        return {
            'price': float(pair_data[price_key]),
            'volume': float(pair_data.get(volume_key, '0'))
        }

    def _calculate_quantities(self):
        fp = self._last_prices[FIRST_PAIR]
        sp = self._last_prices[SECOND_PAIR]
        tp = self._last_prices[THIRD_PAIR]

        fp['quantity'] = fp['price'] * self.fees
        sp['quantity'] = (fp['quantity'] / sp['price']) * self.fees
        tp['quantity'] = tp['price'] * sp['quantity'] * self.fees

    def calculate_profit(self):
        final_quantity = self._last_prices[THIRD_PAIR]['quantity']
        self.profit = round((final_quantity - 1) * 100, 2)
        return self.profit > self.min_profit


class LeftTriangleStrategy(Strategy):

    def __init__(self, pairs_data):
        super().__init__(pairs_data, LEFT_TRIANGLE_STRATEGY)

    def parsed_pairs_data(self, pairs_data):
        first_pair = pairs_data[FIRST_PAIR]
        second_pair = pairs_data[SECOND_PAIR]
        third_pair = pairs_data[THIRD_PAIR]

        self._last_prices[FIRST_PAIR] = self._parse_pair(first_pair, 'a', 'A')
        self._last_prices[SECOND_PAIR] = self._parse_pair(second_pair, 'b', 'B')
        self._last_prices[THIRD_PAIR] = self._parse_pair(third_pair, 'a', 'A')

        self._calculate_quantities()

    def _parse_pair(self, pair_data, price_key, volume_key):
        return {
            'price': float(pair_data[price_key]),
            'volume': float(pair_data.get(volume_key, '0'))
        }

    def _calculate_quantities(self):
        fp = self._last_prices[FIRST_PAIR]
        sp = self._last_prices[SECOND_PAIR]
        tp = self._last_prices[THIRD_PAIR]

        tp['quantity'] = self.fees / tp['price']
        sp['quantity'] = sp['price'] * tp['quantity'] * self.fees
        fp['quantity'] = (sp['quantity'] / fp['price']) * self.fees

    def calculate_profit(self):
        final_quantity = self._last_prices[FIRST_PAIR]['quantity']
        self.profit = round((final_quantity - 1) * 100, 2)
        return self.profit > self.min_profit
