"""Entrypoint del bot de arbitraje triangular en Binance Spot."""

import asyncio
import logging
import signal

from dotenv import load_dotenv

from triangulation.config import Settings
from triangulation.engine import ArbitrageEngine
from triangulation.execution import (
    BinanceClient,
    OrderExecutor,
    load_symbol_filters,
)
from triangulation.logger import setup_logging
from triangulation.market_data import BookTickerStream
from triangulation.observer import ProfitabilityObserver

logger = logging.getLogger(__name__)

RECONNECT_DELAY_S = 5.0


def _sigterm_handler(signum: int, frame: object) -> None:
    """Convierte SIGTERM en KeyboardInterrupt para un apagado ordenado."""
    raise KeyboardInterrupt


async def _load_filters(client: BinanceClient, symbols: list[str]) -> dict:
    """Carga los filtros de exchangeInfo; si falla, continúa sin ellos."""
    try:
        return await load_symbol_filters(client, symbols)
    except Exception as exc:
        logger.warning("No se pudieron cargar filtros de exchangeInfo: %s", exc)
        return {}


async def async_main() -> None:
    """Ejecución principal asíncrona."""
    settings = Settings.from_env()
    setup_logging(settings.log_file)
    signal.signal(signal.SIGTERM, _sigterm_handler)

    client = BinanceClient(
        settings.api_key, settings.api_secret, settings.api_base_url
    )
    try:
        filters = await _load_filters(client, list(settings.pairs))
        executor = OrderExecutor(client, filters, dry_run=settings.dry_run)
        observer = ProfitabilityObserver(settings.min_profit_pct, settings.stats_interval_s)
        engine = ArbitrageEngine(settings, executor, observer)
        stream = BookTickerStream(settings.ws_base_url, settings.pairs, engine.on_tick)

        logger.info(
            "Iniciando bot: dry_run=%s fee=%.3f%% min_profit=%.3f%% monto=%.6f BTC",
            settings.dry_run,
            settings.fee_rate * 100,
            settings.min_profit_pct,
            settings.trade_amount,
        )

        stream_task = asyncio.create_task(stream.start())
        
        try:
            await stream_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Stream terminó por error")
    except KeyboardInterrupt:
        logger.info("Deteniendo bot...")
    finally:
        if 'stream' in locals():
            stream.stop()
        if 'observer' in locals():
            logger.info("%s", observer.summary())
        await client.close()


def main() -> None:
    load_dotenv()
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
