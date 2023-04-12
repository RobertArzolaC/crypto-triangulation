from constants import ETHBTC
from binance_orders import TradingClient
from storage import LastPriceStorage
from strategy_triangulation import RightTriangleStrategy, LeftTriangleStrategy


class PriceObserver:
    def __init__(self, pair):
        self.pair = pair
        self.strategies = []
        self.last_price_storage = LastPriceStorage()

    def add_strategy(self, strategy):
        self.strategies.append(strategy)

    def execute(self):
        for strategy in self.strategies:
            if strategy.is_profitable():
                trading_client = TradingClient(strategy)
                trading_client.load_commands()
                trading_client.execute_commands()

    def update(self, data):
        pair = data["s"]
        last_price_pair = self.last_price_storage.get_last_price(pair)
        if last_price_pair != data:
            self.last_price_storage.update_last_price(pair, data)
            if pair == ETHBTC:
                data = self.last_price_storage.get_state()
                right_triangle_strategy = RightTriangleStrategy(data)
                left_triangle_strategy = LeftTriangleStrategy(data)

                self.add_strategy(right_triangle_strategy)
                self.add_strategy(left_triangle_strategy)

                self.execute()
