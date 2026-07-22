"""Tests del observador de proximidad a la rentabilidad."""

import logging

import pytest

from triangulation.observer import ProfitabilityObserver, _format_duration, _percentile
from triangulation.strategy import (
    DIRECTION_FORWARD,
    SIDE_SELL,
    CycleResult,
    PlannedOrder,
)

THRESHOLD = 0.1


def make_cycle(profit_pct: float) -> CycleResult:
    """CycleResult sintético con el profit dado (órdenes irrelevantes)."""
    orders = (PlannedOrder("BTCUSDT", SIDE_SELL, 1.0, 30000.0),)
    return CycleResult(DIRECTION_FORWARD, profit_pct, 1.0 * (1 + profit_pct / 100), orders)


def make_observer(interval: float = 60.0) -> tuple[ProfitabilityObserver, list[float]]:
    """Construye un observer con reloj controlable: clock() == now[0]."""
    now = [0.0]
    observer = ProfitabilityObserver(
        THRESHOLD, stats_interval_s=interval, clock=lambda: now[0]
    )
    return observer, now


def test_record_tracks_best_profit() -> None:
    """El mejor profit histórico y el conteo de evaluaciones se actualizan."""
    observer, _ = make_observer()
    observer.record(make_cycle(-0.10))
    observer.record(make_cycle(-0.05))
    observer.record(make_cycle(-0.08))

    assert observer.evaluations == 3
    assert observer.best_profit_pct == pytest.approx(-0.05)
    assert observer.opportunities == 0


def test_record_counts_opportunities_above_threshold() -> None:
    """Los ciclos sobre el umbral se contabilizan como oportunidades."""
    observer, _ = make_observer()
    observer.record(make_cycle(0.15))
    observer.record(make_cycle(0.05))

    assert observer.opportunities == 1


def test_record_none_counts_skipped() -> None:
    """Un ciclo None (sin liquidez) no cuenta como evaluación."""
    observer, _ = make_observer()
    observer.record(None)

    assert observer.evaluations == 0
    assert observer.skipped == 1


def test_maybe_log_respects_interval() -> None:
    """La línea STATS solo se emite cuando vence el intervalo."""
    observer, now = make_observer(interval=60.0)

    now[0] = 30.0
    assert observer.maybe_log() is False
    now[0] = 61.0
    assert observer.maybe_log() is True
    now[0] = 90.0
    assert observer.maybe_log() is False


def test_new_best_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Superar el máximo histórico genera una alerta inmediata."""
    observer, _ = make_observer()
    with caplog.at_level(logging.INFO):
        observer.record(make_cycle(-0.05))

    assert "Nuevo mejor ciclo" in caplog.text
    assert "-0.0500%" in caplog.text


def test_summary_contains_key_fields() -> None:
    """El resumen incluye evaluaciones, mejor profit, distancia y percentiles."""
    observer, _ = make_observer()
    observer.record(make_cycle(-0.10))
    observer.record(make_cycle(-0.05))

    summary = observer.summary()
    assert "RESUMEN" in summary
    assert "evals=2" in summary
    assert "mejor=-0.0500%" in summary
    assert "faltan 0.1500pp" in summary
    assert "p50=" in summary
    assert "sobre_umbral=0" in summary


def test_summary_without_evaluations() -> None:
    """Sin evaluaciones, el resumen lo indica explícitamente."""
    observer, _ = make_observer()
    assert "sin evaluaciones" in observer.summary()


def test_distance_text_when_above_threshold() -> None:
    """Por encima del umbral, el texto indica cuánto se supera."""
    observer, _ = make_observer()
    observer.record(make_cycle(0.25))
    assert "supera el umbral por 0.1500pp" in observer.summary()


def test_percentile_interpolates() -> None:
    """El percentil interpola sobre la muestra ordenada."""
    assert _percentile([1.0, 2.0, 3.0, 4.0], 50) == pytest.approx(2.5)
    assert _percentile([1.0, 2.0, 3.0, 4.0], 95) == pytest.approx(3.85)
    assert _percentile([], 50) != _percentile([], 50)  # NaN


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(45, "45s"), (754, "12m34s"), (8040, "2h14m"), (266400, "3d02h")],
)
def test_format_duration(seconds: float, expected: str) -> None:
    """Las duraciones se formatean de forma legible."""
    assert _format_duration(seconds) == expected
