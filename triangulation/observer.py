"""Observabilidad de la proximidad a la rentabilidad del arbitraje.

Registra cada ciclo evaluado por el motor y emite periódicamente un resumen
con el mejor profit neto observado, su distancia al umbral de ejecución y
percentiles recientes. Permite responder con datos "qué tan cerca está el
bot de la rentabilidad" sin operar con dinero real.
"""

import logging
import time
from collections import deque
from collections.abc import Callable

from triangulation.strategy import CycleResult

logger = logging.getLogger(__name__)


class ProfitabilityObserver:
    """Mide y loguea la proximidad del mejor ciclo al umbral de profit.

    La medición es solo de mercado: contabiliza los ciclos cuyo profit supera
    el umbral aunque el cooldown del motor impida ejecutarlos.

    Attributes:
        min_profit_pct: Umbral de ejecución (%) contra el que se mide.
        stats_interval_s: Intervalo entre resúmenes periódicos (segundos).
    """

    def __init__(
        self,
        min_profit_pct: float,
        stats_interval_s: float = 60.0,
        window_size: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Inicializa el observador.

        Args:
            min_profit_pct: Umbral de profit neto (%) para considerar ejecución.
            stats_interval_s: Segundos entre líneas STATS.
            window_size: Tamaño de la ventana reciente para percentiles.
            clock: Reloj monotónico (inyectable para tests).
        """
        self.min_profit_pct = min_profit_pct
        self.stats_interval_s = stats_interval_s
        self._clock = clock
        self._start = clock()
        self._last_log = self._start
        self._evaluations = 0
        self._skipped = 0
        self._opportunities = 0
        self._best_profit = float("-inf")
        self._best_direction = "-"
        self._recent: deque[float] = deque(maxlen=window_size)

    @property
    def evaluations(self) -> int:
        """Total de ciclos evaluados con liquidez suficiente."""
        return self._evaluations

    @property
    def skipped(self) -> int:
        """Evaluaciones descartadas por falta de liquidez top-of-book."""
        return self._skipped

    @property
    def opportunities(self) -> int:
        """Ciclos con profit neto por encima del umbral."""
        return self._opportunities

    @property
    def best_profit_pct(self) -> float:
        """Mejor profit neto observado (-inf si aún no hay evaluaciones)."""
        return self._best_profit

    def record(self, cycle: CycleResult | None) -> None:
        """Registra el mejor ciclo de una evaluación.

        Args:
            cycle: Mejor ciclo del tick, o None si faltó liquidez top-of-book.
        """
        if cycle is None:
            self._skipped += 1
            return
        self._evaluations += 1
        self._recent.append(cycle.profit_pct)
        if cycle.profit_pct > self.min_profit_pct:
            self._opportunities += 1
        if cycle.profit_pct > self._best_profit:
            self._best_profit = cycle.profit_pct
            self._best_direction = cycle.direction
            logger.info(
                "Nuevo mejor ciclo: %+.4f%% (%s) | %s",
                cycle.profit_pct,
                cycle.direction,
                self._distance_text(cycle.profit_pct),
            )

    def maybe_log(self) -> bool:
        """Emite la línea STATS si ya venció el intervalo configurado.

        Returns:
            True si se logueó el resumen periódico.
        """
        now = self._clock()
        if now - self._last_log < self.stats_interval_s:
            return False
        self._last_log = now
        logger.info("STATS %s", self._format_stats())
        return True

    def summary(self) -> str:
        """Resumen final de la sesión (para loguear al detener el bot)."""
        return f"RESUMEN {self._format_stats()}"

    def _format_stats(self) -> str:
        """Formatea la línea de estadísticas periódica/final."""
        uptime = _format_duration(self._clock() - self._start)
        if self._evaluations == 0:
            return (
                f"{uptime} | sin evaluaciones aún "
                f"(precios no frescos o sin liquidez; saltadas={self._skipped})"
            )
        p50 = _percentile(list(self._recent), 50)
        p95 = _percentile(list(self._recent), 95)
        return (
            f"{uptime} | evals={self._evaluations} saltadas={self._skipped} | "
            f"mejor={self._best_profit:+.4f}% ({self._best_direction}) | "
            f"{self._distance_text(self._best_profit)} | "
            f"p50={p50:+.4f}% p95={p95:+.4f}% | sobre_umbral={self._opportunities}"
        )

    def _distance_text(self, profit_pct: float) -> str:
        """Texto de distancia del profit dado al umbral de ejecución."""
        gap = self.min_profit_pct - profit_pct
        if gap > 0:
            return f"faltan {gap:.4f}pp al umbral {self.min_profit_pct:.3f}%"
        return f"supera el umbral por {-gap:.4f}pp"


def _percentile(values: list[float], pct: float) -> float:
    """Percentil por interpolación lineal sobre la muestra dada."""
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    position = pct / 100 * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _format_duration(seconds: float) -> str:
    """Formatea una duración como '2h14m', '3d05h' o '45s'."""
    total = int(seconds)
    days, rem = divmod(total, 86_400)
    hours, rem = divmod(rem, 3_600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d{hours:02d}h"
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"
