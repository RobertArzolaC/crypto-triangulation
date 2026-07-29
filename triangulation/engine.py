"""Orquestación: ticks de mercado -> evaluación de estrategia -> ejecución."""

import logging
import time

from triangulation.config import Settings
from triangulation.execution import OrderExecutor
from triangulation.models import BookTicker
from triangulation.observer import ProfitabilityObserver
from triangulation.strategy import find_best_cycle

logger = logging.getLogger(__name__)


class ArbitrageEngine:
    """Evalúa el triángulo en cada tick fresco y mide la proximidad a rentabilidad.

    La medición (observer) es continua: el cooldown solo bloquea la ejecución,
    nunca la evaluación, para no perder visibilidad del mercado.
    """

    def __init__(
        self,
        settings: Settings,
        executor: OrderExecutor,
        observer: ProfitabilityObserver | None = None,
    ) -> None:
        self._settings = settings
        self._executor = executor
        self._observer = observer or ProfitabilityObserver(
            settings.min_profit_pct, settings.stats_interval_s
        )
        self._last_execution_ts = 0.0
        self._tickers: dict[str, BookTicker] = {}

    def on_tick(self, ticker: BookTicker) -> None:
        """Procesa un tick: actualiza precios, mide y evalúa el triángulo.

        Nunca propaga excepciones: un tick problemático no debe tumbar el stream.
        """
        try:
            self._process_tick(ticker)
        except Exception:
            logger.exception("Error procesando tick de %s", ticker.symbol)

    def _process_tick(self, ticker: BookTicker) -> None:
        """Lógica del tick: frescura -> medición -> decisión de ejecución."""
        self._tickers[ticker.symbol] = ticker

        if not self._all_fresh():
            return

        cycle = find_best_cycle(
            self._tickers,
            pairs=self._settings.pairs,
            amount=self._settings.trade_amount,
            fee_rate=self._settings.fee_rate,
        )
        self._observer.record(cycle)
        self._observer.maybe_log()

        if cycle is None or cycle.profit_pct <= self._settings.min_profit_pct:
            return
        if not self._cooldown_elapsed():
            return

        logger.info(
            "Oportunidad %s: profit neto %.4f%% (%.8f BTC -> %.8f BTC)",
            cycle.direction,
            cycle.profit_pct,
            self._settings.trade_amount,
            cycle.final_amount,
        )
        if self._executor.execute(cycle):
            self._last_execution_ts = time.time()

    def _all_fresh(self) -> bool:
        """True solo si los 3 pares tienen precio y ninguno está obsoleto."""
        max_age = self._settings.max_price_age_ms
        return all(
            pair in self._tickers and self._tickers[pair].age_ms() <= max_age
            for pair in self._settings.pairs
        )

    def _cooldown_elapsed(self) -> bool:
        """True si ya pasó el tiempo mínimo desde la última ejecución."""
        return (time.time() - self._last_execution_ts) >= self._settings.cooldown_s
