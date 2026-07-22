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
    find_opportunity,
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
    """Un ciclo FORWARD con edge neto > umbral produce Opportunity correcta."""
    tickers = profitable_forward_tickers()
    legs = build_legs(
        DIRECTION_FORWARD, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    opp = evaluate(DIRECTION_FORWARD, legs, amount=1.0, fee_rate=FEE, min_profit_pct=0.1)

    assert opp is not None
    assert opp.direction == DIRECTION_FORWARD
    # neto = 1.005 * (1 - 0.00075)^3 - 1 ≈ 0.27404%
    assert opp.profit_pct == pytest.approx(0.27404, abs=1e-4)
    assert opp.final_amount == pytest.approx(1.0027404, abs=1e-6)
    assert [o.side for o in opp.orders] == [SIDE_SELL, SIDE_BUY, SIDE_SELL]
    assert [o.symbol for o in opp.orders] == list(PAIRS)
    assert opp.orders[0].quantity == pytest.approx(1.0)
    assert opp.orders[1].quantity == pytest.approx(14.98875)


def test_reverse_profitable() -> None:
    """Un ciclo REVERSE con edge neto > umbral produce Opportunity correcta."""
    tickers = profitable_reverse_tickers()
    legs = build_legs(
        DIRECTION_REVERSE, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    opp = evaluate(DIRECTION_REVERSE, legs, amount=1.0, fee_rate=FEE, min_profit_pct=0.1)

    assert opp is not None
    assert opp.direction == DIRECTION_REVERSE
    # neto = 2001 / (0.0666 * 29910) * (1 - 0.00075)^3 - 1 ≈ 0.22566%
    assert opp.profit_pct == pytest.approx(0.22566, abs=1e-4)
    assert [o.side for o in opp.orders] == [SIDE_BUY, SIDE_SELL, SIDE_BUY]
    assert [o.symbol for o in opp.orders] == ["ETHBTC", "ETHUSDT", "BTCUSDT"]


def test_edge_below_fees_not_profitable() -> None:
    """Un edge bruto menor que los fees de las 3 patas se descarta."""
    tickers = {
        "BTCUSDT": make_ticker("BTCUSDT", bid=30000.0, ask=30010.0),
        "ETHUSDT": make_ticker("ETHUSDT", bid=1999.0, ask=2000.0),
        "ETHBTC": make_ticker("ETHBTC", bid=0.0667, ask=0.0671),
    }
    legs = build_legs(
        DIRECTION_FORWARD, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    # bruto = 15 * 0.0667 = 1.0005 -> neto = 1.0005 * 0.9977517 - 1 ≈ -0.175%
    opp = evaluate(DIRECTION_FORWARD, legs, amount=1.0, fee_rate=FEE, min_profit_pct=0.1)
    assert opp is None


def test_min_profit_threshold() -> None:
    """Un ciclo rentable pero bajo el umbral mínimo se descarta."""
    tickers = profitable_forward_tickers()
    legs = build_legs(
        DIRECTION_FORWARD, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    # profit neto ≈ 0.274% < umbral 0.5%
    opp = evaluate(DIRECTION_FORWARD, legs, amount=1.0, fee_rate=FEE, min_profit_pct=0.5)
    assert opp is None


def test_insufficient_liquidity_rejected() -> None:
    """Si el top-of-book no cubre la cantidad requerida, se descarta el ciclo."""
    tickers = profitable_forward_tickers()
    tickers["BTCUSDT"] = make_ticker("BTCUSDT", bid=30000.0, ask=30010.0, bid_qty=0.5)
    legs = build_legs(
        DIRECTION_FORWARD, tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"]
    )
    # se requieren vender 1.0 BTC pero solo hay 0.5 en el bid
    opp = evaluate(DIRECTION_FORWARD, legs, amount=1.0, fee_rate=FEE, min_profit_pct=0.1)
    assert opp is None


def test_find_opportunity_forward() -> None:
    """find_opportunity retorna la dirección rentable con el libro FORWARD."""
    opp = find_opportunity(
        profitable_forward_tickers(), PAIRS,
        amount=0.002, fee_rate=FEE, min_profit_pct=0.1,
    )
    assert opp is not None
    assert opp.direction == DIRECTION_FORWARD


def test_find_opportunity_none_when_no_edge() -> None:
    """Sin edge en ninguna dirección, no hay oportunidad."""
    tickers = {
        "BTCUSDT": make_ticker("BTCUSDT", bid=30000.0, ask=30010.0),
        "ETHUSDT": make_ticker("ETHUSDT", bid=2000.0, ask=2001.0),
        "ETHBTC": make_ticker("ETHBTC", bid=0.06668, ask=0.06672),
    }
    opp = find_opportunity(
        tickers, PAIRS, amount=0.002, fee_rate=FEE, min_profit_pct=0.1
    )
    assert opp is None


def test_build_legs_invalid_direction() -> None:
    """Una dirección desconocida lanza ValueError."""
    tickers = profitable_forward_tickers()
    with pytest.raises(ValueError):
        build_legs("DIAGONAL", tickers["BTCUSDT"], tickers["ETHUSDT"], tickers["ETHBTC"])
