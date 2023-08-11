from binance_orders import TradingClient
from constants import ETHBTC, NUMBER_OF_PAIRS
from storage import LastPriceStorage
from strategy_triangulation import RightTriangleStrategy, LeftTriangleStrategy


class PriceObserver:
    def __init__(self, pair):
        self.pair = pair
        self.strategies = []
        self.last_price_storage = LastPriceStorage()

    def clear(self):
        self.strategies = []
        self.last_price_storage.clear()

    def add_strategy(self, strategy):
        self.strategies.append(strategy)

    def execute(self):
        for strategy in self.strategies:
            if strategy.is_profitable:
                strategy.show_profit()
                # trading_client = TradingClient(strategy)
                # trading_client.start()
        self.clear()

    def update(self, data):
        last_price_pair = self.last_price_storage.get_last_price(data["s"])
        if last_price_pair != data:
            price_info = self.last_price_storage.get_state()
            self.last_price_storage.update_last_price(data["s"], data)
            if data["s"] == ETHBTC and len(price_info) == NUMBER_OF_PAIRS:
                right_triangle_strategy = RightTriangleStrategy(price_info)
                left_triangle_strategy = LeftTriangleStrategy(price_info)

                self.add_strategy(right_triangle_strategy)
                self.add_strategy(left_triangle_strategy)

                self.execute()
