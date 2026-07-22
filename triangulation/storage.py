"""Almacén thread-safe de los últimos precios por símbolo."""

import threading

from triangulation.models import BookTicker


class PriceStorage:
    """Guarda el último BookTicker recibido por símbolo.

    No descarta los precios tras cada evaluación: la frescura la controla el
    motor con `max_price_age_ms`.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tickers: dict[str, BookTicker] = {}

    def update(self, ticker: BookTicker) -> None:
        """Actualiza el último tick conocido de un símbolo."""
        with self._lock:
            self._tickers[ticker.symbol] = ticker

    def snapshot(self) -> dict[str, BookTicker]:
        """Retorna una copia del estado actual (símbolo -> último tick)."""
        with self._lock:
            return dict(self._tickers)
