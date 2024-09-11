from typing import Dict, Any
from threading import Lock


class LastPriceStorage:
    _instance = None
    _lock: Lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._last_prices: Dict[str, Any] = {}
        return cls._instance

    def update_last_price(self, pair: str, last_price: Dict[str, Any]) -> None:
        with self._lock:
            self._last_prices[pair] = last_price

    def get_last_price(self, pair: str) -> Dict[str, Any]:
        with self._lock:
            return self._last_prices.get(pair)

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return self._last_prices.copy()

    def clear(self) -> None:
        with self._lock:
            self._last_prices.clear()

    def __len__(self) -> int:
        return len(self._last_prices)

    def __contains__(self, pair: str) -> bool:
        return pair in self._last_prices
