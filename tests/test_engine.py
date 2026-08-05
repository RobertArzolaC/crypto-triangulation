"""Tests del motor de orquestación (frescura, cooldown y medición continua)."""

import time
import pytest

from triangulation.config import Settings
from triangulation.engine import ArbitrageEngine
from triangulation.models import BookTicker
from triangulation.strategy import DIRECTION_FORWARD, CycleResult


class StubExecutor:
    """Executor de prueba que registra los ciclos recibidos."""

    def __init__(self) -> None:
        self.executed: list[CycleResult] = []

    async def execute(self, cycle: CycleResult) -> bool:
        self.executed.append(cycle)
        return True


class StubObserver:
    """Observer de prueba que registra los ciclos medidos."""

    def __init__(self) -> None:
        self.recorded: list[CycleResult | None] = []

    def record(self, cycle: CycleResult | None) -> None:
        self.recorded.append(cycle)

    def maybe_log(self) -> bool:
        return False


def make_ticker(symbol: str, bid: float, ask: float, ts: float | None = None) -> BookTicker:
    """Construye un BookTicker con liquidez amplia y timestamp dado."""
    return BookTicker(
        symbol=symbol, bid=bid, ask=ask,
        bid_qty=100.0, ask_qty=100.0,
        ts=ts if ts is not None else time.time(),
    )


async def profitable_forward_ticks(engine: ArbitrageEngine, ts: float | None = None) -> None:
    """Envía al motor los 3 ticks de un libro con edge FORWARD."""
    await engine.on_tick(make_ticker("BTCFDUSD", 30000.0, 30010.0, ts))
    await engine.on_tick(make_ticker("ETHFDUSD", 1999.0, 2000.0, ts))
    await engine.on_tick(make_ticker("ETHBTC", 0.067, 0.0671, ts))


async def no_edge_ticks(engine: ArbitrageEngine, ts: float | None = None) -> None:
    """Envía al motor los 3 ticks de un libro sin edge en ninguna dirección."""
    await engine.on_tick(make_ticker("BTCFDUSD", 30000.0, 30010.0, ts))
    await engine.on_tick(make_ticker("ETHFDUSD", 2000.0, 2001.0, ts))
    await engine.on_tick(make_ticker("ETHBTC", 0.06668, 0.06672, ts))


def make_engine(
    cooldown_s: float = 0.0,
) -> tuple[ArbitrageEngine, StubExecutor, StubObserver]:
    """Construye un motor con executor y observer stub y settings de prueba."""
    settings = Settings(
        api_key="", api_secret="", cooldown_s=cooldown_s, trade_amount=1.0
    )
    executor = StubExecutor()
    observer = StubObserver()
    engine = ArbitrageEngine(settings, executor, observer)  # type: ignore[arg-type]
    return engine, executor, observer


@pytest.mark.asyncio
async def test_executes_on_fresh_profitable_book() -> None:
    """Con los 3 precios frescos y edge rentable, se ejecuta una oportunidad."""
    engine, executor, _ = make_engine()
    await profitable_forward_ticks(engine)

    assert len(executor.executed) == 1
    assert executor.executed[0].direction == DIRECTION_FORWARD


@pytest.mark.asyncio
async def test_below_threshold_not_executed_but_observed() -> None:
    """Un libro sin edge no ejecuta, pero el observer mide el mejor ciclo."""
    engine, executor, observer = make_engine()
    await no_edge_ticks(engine)

    assert executor.executed == []
    assert len(observer.recorded) == 1
    assert observer.recorded[0] is not None
    assert observer.recorded[0].profit_pct < 0


@pytest.mark.asyncio
async def test_stale_prices_are_ignored() -> None:
    """Un tick obsoleto (> max_price_age_ms) impide evaluar y medir."""
    engine, executor, observer = make_engine()
    stale_ts = time.time() - 10  # 10 s de antigüedad
    await profitable_forward_ticks(engine, ts=stale_ts)

    assert executor.executed == []
    assert observer.recorded == []


@pytest.mark.asyncio
async def test_missing_pair_is_ignored() -> None:
    """Sin los 3 pares presentes no se evalúa."""
    engine, executor, observer = make_engine()
    await engine.on_tick(make_ticker("BTCFDUSD", 30000.0, 30010.0))
    await engine.on_tick(make_ticker("ETHFDUSD", 1999.0, 2000.0))

    assert executor.executed == []
    assert observer.recorded == []


@pytest.mark.asyncio
async def test_cooldown_blocks_immediate_reexecution() -> None:
    """Una segunda oportunidad dentro del cooldown no se ejecuta."""
    engine, executor, _ = make_engine(cooldown_s=60.0)
    await profitable_forward_ticks(engine)
    await profitable_forward_ticks(engine)

    assert len(executor.executed) == 1


@pytest.mark.asyncio
async def test_cooldown_does_not_block_measurement() -> None:
    """El cooldown bloquea la ejecución, nunca la medición del mercado.

    Con los 3 pares en storage, cada tick fresco dispara una evaluación: la
    primera ráfaga mide 1 vez (al completar el triángulo) y la segunda 3.
    """
    engine, executor, observer = make_engine(cooldown_s=60.0)
    await profitable_forward_ticks(engine)
    await profitable_forward_ticks(engine)

    assert len(executor.executed) == 1
    assert len(observer.recorded) == 4


@pytest.mark.asyncio
async def test_on_tick_never_raises() -> None:
    """Un fallo interno (ej. en el executor) no se propaga al stream."""

    class FailingExecutor(StubExecutor):
        async def execute(self, cycle: CycleResult) -> bool:
            raise RuntimeError("fallo simulado")

    settings = Settings(api_key="", api_secret="", cooldown_s=0.0, trade_amount=1.0)
    engine = ArbitrageEngine(settings, FailingExecutor(), StubObserver())  # type: ignore[arg-type]

    await profitable_forward_ticks(engine)  # no debe lanzar
