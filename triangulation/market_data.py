"""Feed de mercado en tiempo real vía WebSocket asíncrono (streams bookTicker)."""

import asyncio
import json
import logging
from collections.abc import Callable

import websockets
from websockets.exceptions import ConnectionClosed

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
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Inicia el loop del WebSocket (asíncrono, con reconexión manual)."""
        logger.info("Conectando al stream: %s", self._url)
        
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self._url) as ws:
                    logger.info("Websocket conectado")
                    while not self._stop_event.is_set():
                        message = await ws.recv()
                        await self._handle_message(message)
            except ConnectionClosed:
                logger.warning("Conexión cerrada, reconectando en 5s...")
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error en websocket: %s", exc)
                await asyncio.sleep(5)

    def stop(self) -> None:
        """Cierra la conexión del WebSocket de forma ordenada."""
        self._stop_event.set()

    async def _handle_message(self, message: str) -> None:
        """Parsea cada mensaje y lo entrega al callback; ignora los inválidos."""
        try:
            ticker = BookTicker.from_ws(json.loads(message))
        except (KeyError, ValueError) as exc:
            logger.warning("Mensaje inválido ignorado: %s", exc)
            return
        try:
            if asyncio.iscoroutinefunction(self._on_tick):
                await self._on_tick(ticker)
            else:
                self._on_tick(ticker)
        except Exception:
            logger.exception("Error en el callback de tick (%s)", ticker.symbol)

