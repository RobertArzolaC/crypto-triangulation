from binance_orders import TradingClient
from constants import THIRD_PAIR, PAIRS_COUNT
from storage import LastPriceStorage
from strategy_triangulation import RightTriangleStrategy, LeftTriangleStrategy


class PriceObserver:
    def __init__(self, pair):
        self.pair = pair
        self.storage = LastPriceStorage()

    def update(self, data):
        last_price_pair = self.storage.get_last_price(data["s"])
        if last_price_pair != data:
            self.storage.update_last_price(data["s"], data)
            current_state = self.storage.get_state()

            if THIRD_PAIR in self.storage and len(current_state) == PAIRS_COUNT:
                strategies = [
                    RightTriangleStrategy(current_state),
                    LeftTriangleStrategy(current_state)
                ]

                for strategy in strategies:
                    if strategy.is_profitable:
                        strategy.show_profit()
                        # trading_client = TradingClient(strategy)
                        # trading_client.start()

                self.storage.clear()
