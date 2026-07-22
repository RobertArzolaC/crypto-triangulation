"""Orquestación: ticks de mercado -> evaluación de estrategia -> ejecución."""

import logging
import time

from triangulation.config import Settings
from triangulation.execution import OrderExecutor
from triangulation.models import BookTicker
from triangulation.storage import PriceStorage
from triangulation.strategy import find_opportunity

logger = logging.getLogger(__name__)


class ArbitrageEngine:
    """Evalúa el triángulo en cada tick, solo con precios frescos y cooldown."""

    def __init__(
        self,
        settings: Settings,
        storage: PriceStorage,
        executor: OrderExecutor,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._executor = executor
        self._last_execution_ts = 0.0

    def on_tick(self, ticker: BookTicker) -> None:
        """Procesa un tick: actualiza precios y evalúa el triángulo si procede."""
        self._storage.update(ticker)
        tickers = self._storage.snapshot()

        if not self._all_fresh(tickers):
            return
        if not self._cooldown_elapsed():
            return

        opportunity = find_opportunity(
            tickers,
            pairs=self._settings.pairs,
            amount=self._settings.trade_amount,
            fee_rate=self._settings.fee_rate,
            min_profit_pct=self._settings.min_profit_pct,
        )
        if opportunity is None:
            return

        logger.info(
            "Oportunidad %s: profit neto %.4f%% (%.8f BTC -> %.8f BTC)",
            opportunity.direction,
            opportunity.profit_pct,
            self._settings.trade_amount,
            opportunity.final_amount,
        )
        if self._executor.execute(opportunity):
            self._last_execution_ts = time.time()

    def _all_fresh(self, tickers: dict[str, BookTicker]) -> bool:
        """True solo si los 3 pares tienen precio y ninguno está obsoleto."""
        max_age = self._settings.max_price_age_ms
        return all(
            pair in tickers and tickers[pair].age_ms() <= max_age
            for pair in self._settings.pairs
        )

    def _cooldown_elapsed(self) -> bool:
        """True si ya pasó el tiempo mínimo desde la última ejecución."""
        return (time.time() - self._last_execution_ts) >= self._settings.cooldown_s
