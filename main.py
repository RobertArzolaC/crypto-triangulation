from dotenv import load_dotenv

from binance_websocket import BinanceWebSocket
from constants import BTCUSDT, ETHUSDT, ETHBTC, PAIRS_CRIPTO
from observers import PriceObserver


load_dotenv()


def main():
    binance_websocket = BinanceWebSocket(PAIRS_CRIPTO)

    btcusdt_price_observer = PriceObserver(BTCUSDT)
    ethusdt_price_observer = PriceObserver(ETHUSDT)
    ethbtc_price_observer = PriceObserver(ETHBTC)

    binance_websocket.register_observer(btcusdt_price_observer)
    binance_websocket.register_observer(ethusdt_price_observer)
    binance_websocket.register_observer(ethbtc_price_observer)

    binance_websocket.start()


if __name__ == "__main__":
    main()
