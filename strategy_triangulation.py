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
        first_pair = pairs_data[FIRST_PAIR]
        second_pair = pairs_data[SECOND_PAIR]
        third_pair = pairs_data[THIRD_PAIR]

        first_pair_bid = float(first_pair["b"])
        first_pair_volume = float(first_pair.get('B'))
        fp_sc_quantity = round(float(first_pair_bid * self.fees), 8)
        self._last_prices[FIRST_PAIR] = dict(
            bid=first_pair_bid, volume=first_pair_volume,
            quantity=fp_sc_quantity
        )

        second_pair_ask = float(second_pair.get('a'))
        second_pair_volume = float(second_pair.get('A'))
        sp_fc_quantity = round(
            float((fp_sc_quantity/second_pair_ask) * self.fees), 8
        )
        self._last_prices[SECOND_PAIR] = dict(
            ask=second_pair_ask, volume=second_pair_volume,
            quantity=sp_fc_quantity
        )

        third_pair_bid = float(third_pair.get('b'))
        third_pair_volume = float(third_pair.get('B'))
        tp_sc_quantity = round(
            float(third_pair_bid * sp_fc_quantity * self.fees), 8
        )
        self._last_prices[THIRD_PAIR] = dict(
            bid=third_pair_bid, volume=third_pair_volume,
            quantity=tp_sc_quantity
        )

    def is_profitable(self):
        third_pair_quantity = self._last_prices[THIRD_PAIR]['quantity']
        self.profit = round((third_pair_quantity - 1) * 100, 2)
        return self.profit > self.min_profit


class LeftTriangleStrategy(Strategy):

    def __init__(self, pairs_data):
        super().__init__(pairs_data, LEFT_TRIANGLE_STRATEGY)

    def parsed_pairs_data(self, pairs_data):
        third_pair = pairs_data[THIRD_PAIR]
        second_pair = pairs_data[SECOND_PAIR]
        first_pair = pairs_data[FIRST_PAIR]

        third_pair_ask = float(third_pair.get('a'))
        third_pair_volume = float(third_pair.get('A'))
        tp_fc_quantity = round(float(self.fees/third_pair_ask), 8)
        self._last_prices[THIRD_PAIR] = dict(
            ask=third_pair_ask, volume=third_pair_volume,
            quantity=tp_fc_quantity
        )

        second_pair_bid = float(second_pair.get('b'))
        second_pair_volume = float(second_pair.get('B'))
        sp_sc_quantity = round(
            float(second_pair_bid * tp_fc_quantity * self.fees), 8
        )
        self._last_prices[SECOND_PAIR] = dict(
            bid=second_pair_bid, volume=second_pair_volume,
            quantity=sp_sc_quantity
        )

        first_pair_ask = float(first_pair.get('a'))
        first_pair_volume = float(first_pair.get('A'))
        fp_fc_quantity = round(
            float((sp_sc_quantity/first_pair_ask) * self.fees), 8
        )
        self._last_prices[FIRST_PAIR] = dict(
            ask=second_pair_bid, volume=first_pair_volume,
            quantity=fp_fc_quantity
        )

    def is_profitable(self):
        third_pair_quantity = self._last_prices[FIRST_PAIR]['quantity']
        self.profit = round((third_pair_quantity - 1) * 100, 2)
        return self.profit > self.min_profit
