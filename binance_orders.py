from abc import ABC, abstractmethod
import os

from binance_client import BinanceClient

from constants import (
    BTCUSDT, ETHUSDT, ETHBTC, RIGHT_TRIANGLE_STRATEGY, LOG_FILE_PATH,
    ORDER_TYPE_MARKET, SIDE_BUY, SIDE_SELL
)
from logger import CryptoLogger


logger = CryptoLogger(__name__, file_path=LOG_FILE_PATH)


class TradingOrder(ABC):

    def __init__(self, pair, quantity):
        self.pair = pair
        self.quantity = quantity
        self.client = BinanceClient(
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
        logger.info(f"Bought {self.quantity} {self.pair}")


class SellOrder(TradingOrder):

    def execute(self):
        self.client.create_order(
            symbol=self.pair, side=SIDE_SELL,
            type=ORDER_TYPE_MARKET, quantity=self.quantity
        )
        logger.info(f"Sold {self.quantity} {self.pair}")


class TradingBatch:
    def __init__(self, order_batch):
        self.order_batch = order_batch

    def execute(self):
        for order in self.order_batch:
            order.execute()


class TradingClient:
    def __init__(self, strategy):
        self.strategy = strategy
        self.orders = []

    def start(self):
        self.load_orders()
        self.execute_orders()

    def add_order(self, order):
        self.orders.append(order)

    def execute_orders(self):
        batch = TradingBatch(self.orders)
        batch.execute()
        logger.info(f"Orders executed for {self.strategy.name} strategy")

    def load_orders(self, base_quantity=0.009):
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
