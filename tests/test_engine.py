"""Tests del motor de orquestación (frescura de precios y cooldown)."""

import time

from triangulation.config import Settings
from triangulation.engine import ArbitrageEngine
from triangulation.models import BookTicker
from triangulation.storage import PriceStorage
from triangulation.strategy import DIRECTION_FORWARD, Opportunity


class StubExecutor:
    """Executor de prueba que registra las oportunidades recibidas."""

    def __init__(self) -> None:
        self.executed: list[Opportunity] = []

    def execute(self, opportunity: Opportunity) -> bool:
        self.executed.append(opportunity)
        return True


def make_ticker(symbol: str, bid: float, ask: float, ts: float | None = None) -> BookTicker:
    """Construye un BookTicker con liquidez amplia y timestamp dado."""
    return BookTicker(
        symbol=symbol, bid=bid, ask=ask,
        bid_qty=100.0, ask_qty=100.0,
        ts=ts if ts is not None else time.time(),
    )


def profitable_forward_ticks(engine: ArbitrageEngine, ts: float | None = None) -> None:
    """Envía al motor los 3 ticks de un libro con edge FORWARD."""
    engine.on_tick(make_ticker("BTCUSDT", 30000.0, 30010.0, ts))
    engine.on_tick(make_ticker("ETHUSDT", 1999.0, 2000.0, ts))
    engine.on_tick(make_ticker("ETHBTC", 0.067, 0.0671, ts))


def make_engine(cooldown_s: float = 0.0) -> tuple[ArbitrageEngine, StubExecutor]:
    """Construye un motor con executor stub y settings de prueba."""
    settings = Settings(
        api_key="", api_secret="", cooldown_s=cooldown_s, trade_amount=1.0
    )
    executor = StubExecutor()
    return ArbitrageEngine(settings, PriceStorage(), executor), executor


def test_executes_on_fresh_profitable_book() -> None:
    """Con los 3 precios frescos y edge rentable, se ejecuta una oportunidad."""
    engine, executor = make_engine()
    profitable_forward_ticks(engine)

    assert len(executor.executed) == 1
    assert executor.executed[0].direction == DIRECTION_FORWARD


def test_stale_prices_are_ignored() -> None:
    """Un tick obsoleto (> max_price_age_ms) impide la evaluación."""
    engine, executor = make_engine()
    stale_ts = time.time() - 10  # 10 s de antigüedad
    profitable_forward_ticks(engine, ts=stale_ts)

    assert executor.executed == []


def test_missing_pair_is_ignored() -> None:
    """Sin los 3 pares presentes no se evalúa."""
    engine, executor = make_engine()
    engine.on_tick(make_ticker("BTCUSDT", 30000.0, 30010.0))
    engine.on_tick(make_ticker("ETHUSDT", 1999.0, 2000.0))

    assert executor.executed == []


def test_cooldown_blocks_immediate_reexecution() -> None:
    """Una segunda oportunidad dentro del cooldown no se ejecuta."""
    engine, executor = make_engine(cooldown_s=60.0)
    profitable_forward_ticks(engine)
    profitable_forward_ticks(engine)

    assert len(executor.executed) == 1
