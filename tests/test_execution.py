"""Tests del módulo de ejecución (cliente Binance y filtros de símbolos)."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from triangulation.execution import BinanceClient, SymbolFilters


def make_client_with_mock() -> tuple[BinanceClient, MagicMock]:
    """Construye un BinanceClient con la sesión HTTP mockeada."""
    client = BinanceClient("key", "secret")
    mock_session = MagicMock()
    mock_session.request.return_value.status_code = 200
    mock_session.request.return_value.json.return_value = {"symbols": []}
    client._session = mock_session
    return client, mock_session


def last_request_params(mock_session: MagicMock) -> dict[str, Any]:
    """Extrae los params de la última request mockeada."""
    return mock_session.request.call_args.kwargs["params"]


def test_symbols_param_is_compact_json() -> None:
    """El parámetro `symbols` se serializa sin espacios (Binance error -1100)."""
    client, mock_session = make_client_with_mock()
    client.get_exchange_info(["BTCUSDT", "ETHUSDT", "ETHBTC"])

    params = last_request_params(mock_session)
    assert params["symbols"] == '["BTCUSDT","ETHUSDT","ETHBTC"]'
    assert " " not in params["symbols"]


def make_symbol_info() -> dict[str, Any]:
    """Entrada de exchangeInfo sintética con filtros LOT_SIZE y NOTIONAL."""
    return {
        "symbol": "ETHUSDT",
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01000000"},
            {
                "filterType": "LOT_SIZE",
                "minQty": "0.00010000",
                "maxQty": "9000.00000000",
                "stepSize": "0.00010000",
            },
            {"filterType": "NOTIONAL", "minNotional": "5.00000000"},
        ],
    }


def test_symbol_filters_parsing() -> None:
    """from_exchange_info extrae step_size, min_qty y min_notional."""
    filters = SymbolFilters.from_exchange_info(make_symbol_info())
    assert filters.step_size == pytest.approx(0.0001)
    assert filters.min_qty == pytest.approx(0.0001)
    assert filters.min_notional == pytest.approx(5.0)


def test_adjust_rounds_down_to_step() -> None:
    """adjust redondea hacia abajo al stepSize."""
    filters = SymbolFilters.from_exchange_info(make_symbol_info())
    adjusted = filters.adjust(14.98875, price=2000.0)
    assert adjusted == pytest.approx(14.9887)


def test_adjust_rejects_below_min_notional() -> None:
    """adjust retorna None si el nocional queda bajo el mínimo."""
    filters = SymbolFilters.from_exchange_info(make_symbol_info())
    # 0.002 ETH * 2000 = 4 USDT < 5 USDT mínimo
    assert filters.adjust(0.002, price=2000.0) is None


def test_adjust_rejects_below_min_qty() -> None:
    """adjust retorna None si la cantidad queda bajo el mínimo."""
    filters = SymbolFilters.from_exchange_info(make_symbol_info())
    assert filters.adjust(0.00005, price=2000.0) is None
