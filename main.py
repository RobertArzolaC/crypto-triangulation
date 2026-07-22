"""Entrypoint del bot de arbitraje triangular en Binance Spot."""

import logging
import signal
import time

from dotenv import load_dotenv

from triangulation.config import Settings
from triangulation.engine import ArbitrageEngine
from triangulation.execution import (
    BinanceClient,
    OrderExecutor,
    SymbolFilters,
    load_symbol_filters,
)
from triangulation.logger import setup_logging
from triangulation.market_data import BookTickerStream
from triangulation.observer import ProfitabilityObserver
from triangulation.storage import PriceStorage

logger = logging.getLogger(__name__)

RECONNECT_DELAY_S = 5.0


def _sigterm_handler(signum: int, frame: object) -> None:
    """Convierte SIGTERM en KeyboardInterrupt para un apagado ordenado.

    systemd detiene servicios con SIGTERM; así el bot loguea el resumen final
    también al detenerse como servicio (no solo con Ctrl+C).
    """
    raise KeyboardInterrupt


def _load_filters(client: BinanceClient, symbols: list[str]) -> dict[str, SymbolFilters]:
    """Carga los filtros de exchangeInfo; si falla, continúa sin ellos.

    En modo real el executor abortará cualquier ciclo sin filtros, por lo que
    operar sin ellos es seguro (no se envían órdenes inválidas).
    """
    try:
        return load_symbol_filters(client, symbols)
    except Exception as exc:
        logger.warning("No se pudieron cargar filtros de exchangeInfo: %s", exc)
        return {}


def main() -> None:
    """Carga configuración, cablea dependencias e inicia el stream."""
    load_dotenv()
    settings = Settings.from_env()
    setup_logging(settings.log_file)
    signal.signal(signal.SIGTERM, _sigterm_handler)

    client = BinanceClient(
        settings.api_key, settings.api_secret, settings.api_base_url
    )
    filters = _load_filters(client, list(settings.pairs))
    executor = OrderExecutor(client, filters, dry_run=settings.dry_run)
    observer = ProfitabilityObserver(settings.min_profit_pct, settings.stats_interval_s)
    engine = ArbitrageEngine(settings, PriceStorage(), executor, observer)
    stream = BookTickerStream(settings.ws_base_url, settings.pairs, engine.on_tick)

    logger.info(
        "Iniciando bot: dry_run=%s fee=%.3f%% min_profit=%.3f%% monto=%.6f BTC",
        settings.dry_run,
        settings.fee_rate * 100,
        settings.min_profit_pct,
        settings.trade_amount,
    )
    try:
        while True:
            try:
                stream.start()
                break  # cierre limpio: stop() fue invocado
            except Exception:
                logger.exception(
                    "Stream terminó por error; reintentando en %.0f s...",
                    RECONNECT_DELAY_S,
                )
                time.sleep(RECONNECT_DELAY_S)
    except KeyboardInterrupt:
        logger.info("Deteniendo bot...")
        stream.stop()
    logger.info("%s", observer.summary())


if __name__ == "__main__":
    main()
