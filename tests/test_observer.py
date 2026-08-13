"""Tests del observador de proximidad a la rentabilidad."""

import logging

import pytest

from triangulation.models import BookTicker
from triangulation.observer import ProfitabilityObserver, _format_duration, _percentile
from triangulation.strategy import (
    DIRECTION_FORWARD,
    SIDE_SELL,
    CycleResult,
    PlannedOrder,
)

THRESHOLD = 0.1


def make_cycle(
    profit_pct: float, gross_profit_pct: float = 0.0, fees_pct: float = 0.0
) -> CycleResult:
    """CycleResult sintético con el profit dado (órdenes irrelevantes)."""
    orders = (PlannedOrder("BTCUSDT", SIDE_SELL, 1.0, 30000.0),)
    return CycleResult(
        DIRECTION_FORWARD,
        profit_pct,
        gross_profit_pct,
        fees_pct,
        1.0 * (1 + profit_pct / 100),
        orders,
    )


def make_tickers() -> dict[str, BookTicker]:
    """Libro sintético de los 3 pares para el log detallado."""
    return {
        "BTCFDUSD": BookTicker("BTCFDUSD", 30000.0, 30010.0, 5.0, 5.0, 0.0),
        "ETHFDUSD": BookTicker("ETHFDUSD", 1999.0, 2000.0, 50.0, 50.0, 0.0),
        "ETHBTC": BookTicker("ETHBTC", 0.067, 0.0671, 20.0, 20.0, 0.0),
    }


def make_observer() -> tuple[ProfitabilityObserver, list[float]]:
    """Construye un observer con reloj controlable: clock() == now[0]."""
    now = [0.0]
    observer = ProfitabilityObserver(THRESHOLD, clock=lambda: now[0])
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


def test_positive_cycle_logs_detailed_fields(caplog: pytest.LogCaptureFixture) -> None:
    """Un ciclo con profit > 0 imprime precios y gross/fees/net por separado."""
    observer, _ = make_observer()
    cycle = make_cycle(
        profit_pct=0.0119, gross_profit_pct=0.0870, fees_pct=0.0751
    )
    with caplog.at_level(logging.INFO):
        observer.record(cycle, make_tickers())

    assert "OPORTUNIDAD" in caplog.text
    assert "direction=FORWARD" in caplog.text
    assert "btcfdusd_bid=30000.00000000" in caplog.text
    assert "btcfdusd_ask=30010.00000000" in caplog.text
    assert "ethfdusd_bid=1999.00000000" in caplog.text
    assert "ethfdusd_ask=2000.00000000" in caplog.text
    assert "ethbtc_bid=0.06700000" in caplog.text
    assert "ethbtc_ask=0.06710000" in caplog.text
    assert "gross_profit=+0.0870%" in caplog.text
    assert "fees=-0.0751%" in caplog.text
    assert "net_profit=+0.0119%" in caplog.text


def test_non_positive_cycle_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Un ciclo con profit <= 0 no emite la línea OPORTUNIDAD."""
    observer, _ = make_observer()
    with caplog.at_level(logging.INFO):
        observer.record(make_cycle(0.0), make_tickers())

    assert "OPORTUNIDAD" not in caplog.text


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
