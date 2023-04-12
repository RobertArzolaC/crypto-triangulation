from abc import ABC, abstractmethod
import os

from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET, SIDE_BUY, SIDE_SELL

from constants import BTCUSDT, ETHUSDT, ETHBTC, RIGHT_TRIANGLE_STRATEGY


class TradingOrder(ABC):

    def __init__(self, pair, quantity):
        self.pair = pair
        self.quantity = quantity
        self.client = Client(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_API_SECRET'),
        )

    @abstractmethod
    def execute(self):
        pass


class BuyOrder(TradingOrder):

    def execute(self):
        self.client.create_order(
            symbol=self.pair, side=SIDE_BUY,
            type=ORDER_TYPE_MARKET, quantity=self.quantity
        )

    def __repr__(self):
        return f"Buy {self.quantity} {self.pair}"


class SellOrder(TradingOrder):

    def execute(self):
        self.client.create_order(
            symbol=self.pair, side=SIDE_SELL,
            type=ORDER_TYPE_MARKET, quantity=self.quantity
        )

    def __repr__(self):
        return f"Sell {self.quantity} {self.pair}"


class TradingBatch:
    def __init__(self, commands):
        self.commands = commands

    def execute(self):
        for command in self.commands:
            command.execute()


class TradingClient:
    def __init__(self, strategy):
        self.strategy = strategy
        self.commands = []

    def add_order(self, command):
        self.commands.append(command)

    def execute_orders(self):
        batch = TradingBatch(self.commands)
        batch.execute()

    def load_orders(self, base_quantity=1):
        last_prices = self.strategy.get_last_prices()

        if self.strategy.name == RIGHT_TRIANGLE_STRATEGY:
            btc_quantity = float(
                (last_prices[ETHUSDT]['ask'] * base_quantity) /
                last_prices[BTCUSDT]['bid']
            )
            btc_quantity = round(btc_quantity, 5)

            self.add_order(SellOrder(BTCUSDT, btc_quantity))
            self.add_order(BuyOrder(ETHUSDT, base_quantity))
            self.add_order(SellOrder(ETHBTC, base_quantity))
        else:
            btc_quantity = float(
                last_prices[ETHBTC]['ask'] * base_quantity
            )
            btc_quantity = round(btc_quantity, 5)

            self.add_order(BuyOrder(ETHBTC, base_quantity))
            self.add_order(SellOrder(ETHUSDT, base_quantity))
            self.add_order(BuyOrder(BTCUSDT, btc_quantity))
