"""Ejecución de órdenes en Binance Spot, con soporte de dry-run.

Modo dry-run (default): simula y loguea las 3 patas sin enviar órdenes.
Modo real: ejecuta las patas secuencialmente; si una falla, aborta las
restantes y loguea una alerta crítica (no hay unwind automático).
"""

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Any
from urllib.parse import urlencode

import requests

from triangulation.strategy import Opportunity, PlannedOrder

logger = logging.getLogger(__name__)


class BinanceAPIError(Exception):
    """Error devuelto por la API de Binance (código + mensaje)."""


class BinanceClient:
    """Cliente REST mínimo para Binance Spot con firma HMAC-SHA256."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.binance.com",
        timeout_s: float = 10.0,
    ) -> None:
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._session = requests.Session()
        self._session.headers["X-MBX-APIKEY"] = api_key

    def _sign(self, params: dict[str, Any]) -> str:
        """Genera la firma HMAC-SHA256 del query string."""
        query = urlencode(params)
        return hmac.new(
            self._api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> Any:
        """Envía una request a la API y valida la respuesta.

        Raises:
            BinanceAPIError: Si Binance responde con un código de error.
        """
        params = dict(params or {})
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)

        response = self._session.request(
            method, f"{self._base_url}{path}", params=params, timeout=self._timeout_s
        )
        data = response.json()
        if response.status_code != 200:
            raise BinanceAPIError(
                f"Binance error {data.get('code')}: {data.get('msg')}"
            )
        return data

    def get_exchange_info(self, symbols: list[str]) -> dict[str, Any]:
        """Obtiene exchangeInfo (filtros de trading) de los símbolos dados.

        Nota: Binance rechaza espacios en el array JSON del parámetro
        `symbols` (error -1100); se serializa de forma compacta.
        """
        return self._request(
            "GET",
            "/api/v3/exchangeInfo",
            {"symbols": json.dumps(symbols, separators=(",", ":"))},
        )

    def create_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> dict[str, Any]:
        """Crea una orden market firmada. Retorna el fill de Binance."""
        return self._request(
            "POST",
            "/api/v3/order",
            {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": quantity,
            },
            signed=True,
        )


@dataclass(frozen=True)
class SymbolFilters:
    """Filtros de trading de un símbolo (derivados de exchangeInfo).

    Attributes:
        step_size: Incremento mínimo de cantidad (LOT_SIZE).
        min_qty: Cantidad mínima por orden (LOT_SIZE).
        min_notional: Valor nocional mínimo por orden (MIN_NOTIONAL/NOTIONAL).
    """

    step_size: float
    min_qty: float
    min_notional: float

    @classmethod
    def from_exchange_info(cls, symbol_info: dict[str, Any]) -> "SymbolFilters":
        """Parsea los filtros relevantes desde la entrada de exchangeInfo."""
        filters = {f["filterType"]: f for f in symbol_info["filters"]}
        lot_size = filters["LOT_SIZE"]
        notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}
        return cls(
            step_size=float(lot_size["stepSize"]),
            min_qty=float(lot_size["minQty"]),
            min_notional=float(notional.get("minNotional", 0.0)),
        )

    def adjust(self, quantity: float, price: float) -> float | None:
        """Redondea la cantidad hacia abajo al stepSize y valida los mínimos.

        Args:
            quantity: Cantidad deseada del asset base.
            price: Precio de referencia para validar el nocional mínimo.

        Returns:
            Cantidad ajustada si cumple los filtros; None en caso contrario.
        """
        stepped = _floor_to_step(quantity, self.step_size)
        if stepped < self.min_qty:
            return None
        if stepped * price < self.min_notional:
            return None
        return stepped


def _floor_to_step(quantity: float, step: float) -> float:
    """Redondea hacia abajo una cantidad al múltiplo de step más cercano."""
    qty_dec = Decimal(str(quantity))
    step_dec = Decimal(str(step))
    steps = (qty_dec / step_dec).to_integral_value(rounding=ROUND_DOWN)
    return float(steps * step_dec)


def load_symbol_filters(
    client: BinanceClient, symbols: list[str]
) -> dict[str, SymbolFilters]:
    """Descarga exchangeInfo y construye los filtros por símbolo."""
    info = client.get_exchange_info(symbols)
    return {
        entry["symbol"]: SymbolFilters.from_exchange_info(entry)
        for entry in info["symbols"]
    }


class OrderExecutor:
    """Ejecuta (o simula en dry-run) las patas de una oportunidad."""

    def __init__(
        self,
        client: BinanceClient,
        filters: dict[str, SymbolFilters],
        dry_run: bool = True,
    ) -> None:
        self._client = client
        self._filters = filters
        self._dry_run = dry_run

    def execute(self, opportunity: Opportunity) -> bool:
        """Ejecuta las 3 patas secuencialmente.

        Args:
            opportunity: Oportunidad detectada por la estrategia.

        Returns:
            True si el ciclo se completó (o se simuló en dry-run); False si se
            abortó por filtros no cumplidos o por un fallo en alguna pata.
        """
        planned = self._apply_filters(opportunity.orders)
        if planned is None:
            return False

        if self._dry_run:
            for order in planned:
                logger.info(
                    "[DRY-RUN] %s %s qty=%.8f @ %.8f",
                    order.side, order.symbol, order.quantity, order.price,
                )
            return True

        for order in planned:
            try:
                result = self._client.create_market_order(
                    order.symbol, order.side, order.quantity
                )
                logger.info(
                    "Orden ejecutada: %s %s qty=%.8f -> status=%s",
                    order.side, order.symbol, order.quantity,
                    result.get("status", "?"),
                )
            except (BinanceAPIError, requests.RequestException) as exc:
                logger.critical(
                    "FALLO en pata %s %s: %s. Patas restantes abortadas; "
                    "revisar posición manualmente (no hay unwind automático).",
                    order.side, order.symbol, exc,
                )
                return False
        return True

    def _apply_filters(
        self, orders: tuple[PlannedOrder, ...]
    ) -> list[PlannedOrder] | None:
        """Ajusta cantidades a los filtros de Binance; None si alguna no cumple."""
        planned: list[PlannedOrder] = []
        for order in orders:
            symbol_filters = self._filters.get(order.symbol)
            if symbol_filters is None:
                if not self._dry_run:
                    logger.critical(
                        "Sin filtros de exchangeInfo para %s; abortando en modo real.",
                        order.symbol,
                    )
                    return None
                planned.append(order)
                continue
            adjusted = symbol_filters.adjust(order.quantity, order.price)
            if adjusted is None:
                logger.warning(
                    "Pata %s %s descartada por filtros (qty=%.8f @ %.8f)",
                    order.side, order.symbol, order.quantity, order.price,
                )
                return None
            planned.append(
                PlannedOrder(order.symbol, order.side, adjusted, order.price)
            )
        return planned
