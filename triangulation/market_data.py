"""Feed de mercado en tiempo real vía WebSocket (streams bookTicker)."""

import json
import logging
from collections.abc import Callable

import websocket

from triangulation.models import BookTicker

logger = logging.getLogger(__name__)


class BookTickerStream:
    """Conecta al stream combinado bookTicker y emite cada tick a un callback."""

    def __init__(
        self,
        base_url: str,
        symbols: tuple[str, ...] | list[str],
        on_tick: Callable[[BookTicker], None],
    ) -> None:
        streams = "/".join(f"{symbol.lower()}@bookTicker" for symbol in symbols)
        self._url = base_url + streams
        self._on_tick = on_tick
        self._ws: websocket.WebSocketApp | None = None

    def start(self) -> None:
        """Inicia el loop del WebSocket (bloqueante, con reconexión)."""
        self._ws = websocket.WebSocketApp(
            self._url,
            on_message=self._handle_message,
            on_error=self._handle_error,
        )
        logger.info("Conectando al stream: %s", self._url)
        self._ws.run_forever(reconnect=15, ping_interval=180)

    def stop(self) -> None:
        """Cierra la conexión del WebSocket."""
        if self._ws is not None:
            self._ws.close()

    def _handle_message(self, _ws: websocket.WebSocket, message: str) -> None:
        """Parsea cada mensaje y lo entrega al callback; ignora los inválidos.

        Nunca propaga excepciones: un fallo en el callback no debe tumbar el
        stream (defensa en profundidad; el motor también se autoprotege).
        """
        try:
            ticker = BookTicker.from_ws(json.loads(message))
        except (KeyError, ValueError) as exc:
            logger.warning("Mensaje inválido ignorado: %s", exc)
            return
        try:
            self._on_tick(ticker)
        except Exception:
            logger.exception("Error en el callback de tick (%s)", ticker.symbol)

    def _handle_error(self, _ws: websocket.WebSocket, error: object) -> None:
        logger.error("Error en websocket: %s", error)
