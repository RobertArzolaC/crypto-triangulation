"""Tests del motor de detección de arbitraje triangular."""

import time

import pytest

from triangulation.models import BookTicker
from triangulation.strategy import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    SIDE_BUY,
    SIDE_SELL,
    build_legs,
    evaluate,
    find_best_cycle,
)

FEE = 0.00075  # 0.075% con BNB
PAIRS = ("BTCUSDT", "ETHUSDT", "ETHBTC")


def make_ticker(
    symbol: str,
    bid: float,
    ask: float,
    bid_qty: float = 100.0,
    ask_qty: float = 100.0,
) -> BookTicker:
    """Construye un BookTicker de prueba con timestamp actual."""
    return BookTicker(
        symbol=symbol, bid=bid, ask=ask,
        bid_qty=bid_qty, ask_qty=ask_qty, ts=time.time(),
    )


def profitable_forward_tickers() -> dict[str, BookTicker]:
    """Libro sintético con edge FORWARD ~+0.5% bruto (~+0.274% neto)."""
    return {
        "BTCUSDT": make_ticker("BTCUSDT", bid=30000.0, ask=30010.0),
        "ETHUSDT": make_ticker("ETHUSDT", bid=1999.0, ask=2000.0),
        "ETHBTC": make_ticker("ETHBTC", bid=0.067, ask=0.0671),
    }


def profitable_reverse_tickers() -> dict[str, BookTicker]:
    """Libro sintético con edge REVERSE ~+0.45% bruto (~+0.226% neto)."""
    return {
        "BTCUSDT": make_ticker("BTCUSDT", bid=29900.0, ask=29910.0),
        "ETHUSDT": make_ticker("ETHUSDT", bid=2001.0, ask=2002.0),
        "ETHBTC": make_ticker("ETHBTC", bid=0.0665, ask=0.0666),
    }


def test_forward_profitable() -> None:
    """Un ciclo FORWARD con edge produce CycleResult con profit neto correcto."""
    tickers = profitable_forward_tickers()
    legs = build_legs(
        DIRECTION_FORWARD, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    cycle = evaluate(DIRECTION_FORWARD, legs, amount=1.0, fee_rate=FEE)

    assert cycle is not None
    assert cycle.direction == DIRECTION_FORWARD
    # neto = 1.005 * (1 - 0.00075)^3 - 1 ≈ 0.27404%
    assert cycle.profit_pct == pytest.approx(0.27404, abs=1e-4)
    assert cycle.final_amount == pytest.approx(1.0027404, abs=1e-6)
    assert [o.side for o in cycle.orders] == [SIDE_SELL, SIDE_BUY, SIDE_SELL]
    assert [o.symbol for o in cycle.orders] == list(PAIRS)
    assert cycle.orders[0].quantity == pytest.approx(1.0)
    assert cycle.orders[1].quantity == pytest.approx(14.98875)


def test_reverse_profitable() -> None:
    """Un ciclo REVERSE con edge produce CycleResult con profit neto correcto."""
    tickers = profitable_reverse_tickers()
    legs = build_legs(
        DIRECTION_REVERSE, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    cycle = evaluate(DIRECTION_REVERSE, legs, amount=1.0, fee_rate=FEE)

    assert cycle is not None
    assert cycle.direction == DIRECTION_REVERSE
    # neto = 2001 / (0.0666 * 29910) * (1 - 0.00075)^3 - 1 ≈ 0.22566%
    assert cycle.profit_pct == pytest.approx(0.22566, abs=1e-4)
    assert [o.side for o in cycle.orders] == [SIDE_BUY, SIDE_SELL, SIDE_BUY]
    assert [o.symbol for o in cycle.orders] == ["ETHBTC", "ETHUSDT", "BTCUSDT"]


def test_edge_below_fees_yields_negative_profit() -> None:
    """Un edge bruto menor que los fees devuelve profit neto negativo (no None).

    La estrategia ya no filtra por umbral: reporta el resultado para que el
    motor pueda medir la proximidad a la rentabilidad.
    """
    tickers = {
        "BTCUSDT": make_ticker("BTCUSDT", bid=30000.0, ask=30010.0),
        "ETHUSDT": make_ticker("ETHUSDT", bid=1999.0, ask=2000.0),
        "ETHBTC": make_ticker("ETHBTC", bid=0.0667, ask=0.0671),
    }
    legs = build_legs(
        DIRECTION_FORWARD, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    # bruto = 15 * 0.0667 = 1.0005 -> neto = 1.0005 * 0.9977517 - 1 ≈ -0.175%
    cycle = evaluate(DIRECTION_FORWARD, legs, amount=1.0, fee_rate=FEE)
    assert cycle is not None
    assert cycle.profit_pct == pytest.approx(-0.17494, abs=1e-4)
    assert cycle.profit_pct < 0


def test_insufficient_liquidity_rejected() -> None:
    """Si el top-of-book no cubre la cantidad requerida, el ciclo es None."""
    tickers = profitable_forward_tickers()
    tickers["BTCUSDT"] = make_ticker("BTCUSDT", bid=30000.0, ask=30010.0, bid_qty=0.5)
    legs = build_legs(
        DIRECTION_FORWARD, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    # se requieren vender 1.0 BTC pero solo hay 0.5 en el bid
    cycle = evaluate(DIRECTION_FORWARD, legs, amount=1.0, fee_rate=FEE)
    assert cycle is None


def test_find_best_cycle_forward() -> None:
    """find_best_cycle retorna la dirección más rentable con el libro FORWARD."""
    cycle = find_best_cycle(
        profitable_forward_tickers(), PAIRS, amount=0.002, fee_rate=FEE
    )
    assert cycle is not None
    assert cycle.direction == DIRECTION_FORWARD


def test_find_best_cycle_reports_negative_edge() -> None:
    """Sin edge en ninguna dirección, igualmente se reporta el mejor ciclo."""
    tickers = {
        "BTCUSDT": make_ticker("BTCUSDT", bid=30000.0, ask=30010.0),
        "ETHUSDT": make_ticker("ETHUSDT", bid=2000.0, ask=2001.0),
        "ETHBTC": make_ticker("ETHBTC", bid=0.06668, ask=0.06672),
    }
    cycle = find_best_cycle(tickers, PAIRS, amount=0.002, fee_rate=FEE)
    assert cycle is not None
    assert cycle.profit_pct < 0


def test_build_legs_invalid_direction() -> None:
    """Una dirección desconocida lanza ValueError."""
    tickers = profitable_forward_tickers()
    with pytest.raises(ValueError):
        build_legs("DIAGONAL", tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"])
