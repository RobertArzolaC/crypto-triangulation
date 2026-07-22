"""Modelos de datos de mercado."""

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BookTicker:
    """Mejor bid/ask de un símbolo con sus cantidades (stream bookTicker).

    Attributes:
        symbol: Símbolo del par (ej. "BTCUSDT").
        bid: Mejor precio de compra.
        ask: Mejor precio de venta.
        bid_qty: Cantidad disponible en el mejor bid.
        ask_qty: Cantidad disponible en el mejor ask.
        ts: Timestamp local de recepción (time.time()).
    """

    symbol: str
    bid: float
    ask: float
    bid_qty: float
    ask_qty: float
    ts: float

    @classmethod
    def from_ws(cls, data: dict[str, Any]) -> "BookTicker":
        """Parsea el payload JSON del stream bookTicker de Binance.

        Args:
            data: Diccionario con claves 's', 'b', 'a', 'B', 'A'.

        Returns:
            Instancia de BookTicker con timestamp local de recepción.

        Raises:
            KeyError: Si falta alguna clave requerida.
            ValueError: Si algún valor numérico es inválido.
        """
        return cls(
            symbol=data["s"],
            bid=float(data["b"]),
            ask=float(data["a"]),
            bid_qty=float(data["B"]),
            ask_qty=float(data["A"]),
            ts=time.time(),
        )

    def age_ms(self) -> float:
        """Retorna la edad del tick en milisegundos."""
        return (time.time() - self.ts) * 1000
