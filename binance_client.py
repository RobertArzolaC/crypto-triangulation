import json
import os

from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET, SIDE_BUY

from constants import BTCUSDT


client = Client(
    testnet=True,
    api_key=os.getenv('BINANCE_TESTNET_API_KEY'),
    api_secret=os.getenv('BINANCE_TESTNET_API_SECRET'),
)

# info = client.get_order_book(symbol=BTCUSDT)
# print(json.dumps(info, sort_keys=True, indent=4))

created_order = client.create_order(
    symbol=BTCUSDT, side=SIDE_BUY,
    type=ORDER_TYPE_MARKET, quantity=10
)
print(json.dumps(created_order, sort_keys=True, indent=4))

# orders = client.get_all_orders(symbol=BTCUSDT)
# print(json.dumps(orders, sort_keys=True, indent=4))

orders_pending = client.get_open_orders(symbol=BTCUSDT)
print(json.dumps(orders_pending, sort_keys=True, indent=4))
