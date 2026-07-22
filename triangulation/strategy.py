"""Motor de detección de arbitraje triangular.

Triángulo (numéraire BTC): BTCUSDT / ETHUSDT / ETHBTC.

Dirección FORWARD:  BTC --(vende BTCUSDT @ bid)--> USDT --(compra ETHUSDT @ ask)-->
                    ETH --(vende ETHBTC @ bid)--> BTC
Dirección REVERSE:  BTC --(compra ETHBTC @ ask)--> ETH --(vende ETHUSDT @ bid)-->
                    USDT --(compra BTCUSDT @ ask)--> BTC

En cada pata se descuenta la comisión (fee_rate) sobre el monto recibido, por lo
que el ciclo completo aplica (1 - fee_rate)^3. La evaluación es independiente del
umbral de profit: devuelve siempre el resultado del ciclo (incluso negativo) para
que el motor pueda medir la proximidad a la rentabilidad y decidir si ejecuta.
"""

from dataclasses import dataclass

from triangulation.models import BookTicker

SIDE_BUY = "BUY"
SIDE_SELL = "SELL"

DIRECTION_FORWARD = "FORWARD"
DIRECTION_REVERSE = "REVERSE"


@dataclass(frozen=True)
class Leg:
    """Una pata del ciclo de arbitraje.

    Attributes:
        symbol: Símbolo del par a operar.
        side: SIDE_BUY o SIDE_SELL.
        price: Precio top-of-book aplicable (bid si se vende, ask si se compra).
        available: Cantidad disponible top-of-book en el asset base.
    """

    symbol: str
    side: str
    price: float
    available: float


@dataclass(frozen=True)
class PlannedOrder:
    """Orden market planificada para una pata de un ciclo rentable.

    Attributes:
        symbol: Símbolo del par.
        side: SIDE_BUY o SIDE_SELL.
        quantity: Cantidad del asset base a operar.
        price: Precio de referencia usado en la simulación.
    """

    symbol: str
    side: str
    quantity: float
    price: float


@dataclass(frozen=True)
class CycleResult:
    """Resultado de evaluar un ciclo completo del triángulo.

    Attributes:
        direction: DIRECTION_FORWARD o DIRECTION_REVERSE.
        profit_pct: Profit neto estimado en % sobre el monto inicial (post-fees;
            puede ser negativo).
        final_amount: Monto final estimado en BTC.
        orders: Las 3 órdenes planificadas del ciclo, en orden de ejecución.
    """

    direction: str
    profit_pct: float
    final_amount: float
    orders: tuple[PlannedOrder, ...]


def build_legs(
    direction: str,
    btcusdt: BookTicker,
    ethusdt: BookTicker,
    ethbtc: BookTicker,
) -> list[Leg]:
    """Construye las 3 patas del ciclo para una dirección dada.

    Args:
        direction: DIRECTION_FORWARD o DIRECTION_REVERSE.
        btcusdt: Último tick de BTCUSDT.
        ethusdt: Último tick de ETHUSDT.
        ethbtc: Último tick de ETHBTC.

    Returns:
        Lista de 3 Leg en orden de ejecución.

    Raises:
        ValueError: Si la dirección es desconocida.
    """
    if direction == DIRECTION_FORWARD:
        return [
            Leg(btcusdt.symbol, SIDE_SELL, btcusdt.bid, btcusdt.bid_qty),
            Leg(ethusdt.symbol, SIDE_BUY, ethusdt.ask, ethusdt.ask_qty),
            Leg(ethbtc.symbol, SIDE_SELL, ethbtc.bid, ethbtc.bid_qty),
        ]
    if direction == DIRECTION_REVERSE:
        return [
            Leg(ethbtc.symbol, SIDE_BUY, ethbtc.ask, ethbtc.ask_qty),
            Leg(ethusdt.symbol, SIDE_SELL, ethusdt.bid, ethusdt.bid_qty),
            Leg(btcusdt.symbol, SIDE_BUY, btcusdt.ask, btcusdt.ask_qty),
        ]
    raise ValueError(f"Dirección desconocida: {direction}")


def evaluate(
    direction: str,
    legs: list[Leg],
    amount: float,
    fee_rate: float,
) -> CycleResult | None:
    """Evalúa un ciclo completo simulando las 3 patas con fees y liquidez.

    Args:
        direction: Dirección del ciclo (solo informativa para el resultado).
        legs: Las 3 patas en orden de ejecución.
        amount: Monto inicial en BTC.
        fee_rate: Comisión por pata (ej. 0.00075 = 0.075% con BNB).

    Returns:
        CycleResult con el profit neto del ciclo (puede ser negativo), o None
        si la liquidez top-of-book no cubre alguna pata. El umbral de profit
        lo aplica el motor, no la estrategia.
    """
    value = amount
    orders: list[PlannedOrder] = []
    for leg in legs:
        if leg.side == SIDE_SELL:
            required = value
            received = value * leg.price
        else:
            required = value / leg.price
            received = required
        if required > leg.available:
            return None  # liquidez top-of-book insuficiente
        orders.append(PlannedOrder(leg.symbol, leg.side, required, leg.price))
        value = received * (1 - fee_rate)

    profit_pct = (value / amount - 1) * 100
    return CycleResult(direction, profit_pct, value, tuple(orders))


def find_best_cycle(
    tickers: dict[str, BookTicker],
    pairs: tuple[str, str, str],
    amount: float,
    fee_rate: float,
) -> CycleResult | None:
    """Evalúa ambas direcciones del triángulo y retorna la más rentable.

    Args:
        tickers: Estado actual de precios por símbolo (debe contener los 3 pares).
        pairs: Los 3 pares del triángulo en orden (BTCUSDT, ETHUSDT, ETHBTC).
        amount: Monto inicial en BTC.
        fee_rate: Comisión por pata.

    Returns:
        El CycleResult de mayor profit neto (puede ser negativo), o None si
        ninguna dirección tiene liquidez top-of-book suficiente.
    """
    btcusdt = tickers[pairs[0]]
    ethusdt = tickers[pairs[1]]
    ethbtc = tickers[pairs[2]]

    candidates: list[CycleResult] = []
    for direction in (DIRECTION_FORWARD, DIRECTION_REVERSE):
        legs = build_legs(direction, btcusdt, ethusdt, ethbtc)
        cycle = evaluate(direction, legs, amount, fee_rate)
        if cycle is not None:
            candidates.append(cycle)

    if not candidates:
        return None
    return max(candidates, key=lambda cycle: cycle.profit_pct)
