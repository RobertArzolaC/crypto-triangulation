"""Tests de la carga de configuración desde variables de entorno."""

import pytest

from triangulation.config import Settings

ENV_VARS = [
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "DRY_RUN",
    "FEE_RATE",
    "MIN_PROFIT_PCT",
    "TRADE_AMOUNT",
    "MAX_PRICE_AGE_MS",
    "COOLDOWN_S",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garantiza un entorno limpio para cada test."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults() -> None:
    """Sin variables de entorno se usan los defaults seguros."""
    settings = Settings.from_env()
    assert settings.dry_run is True
    assert settings.fee_rate == pytest.approx(0.00075)
    assert settings.min_profit_pct == pytest.approx(0.1)
    assert settings.trade_amount == pytest.approx(0.002)
    assert settings.max_price_age_ms == 1500
    assert settings.cooldown_s == pytest.approx(5.0)
    assert settings.pairs == ("BTCFDUSD", "ETHFDUSD", "ETHBTC")


def test_fee_rate_default_is_taker_bnb() -> None:
    """El default de fee_rate es la fee taker real con BNB (0.075%)."""
    settings = Settings(api_key="", api_secret="")
    assert settings.fee_rate == pytest.approx(0.00075)


def test_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Las variables de entorno pisan los defaults."""
    monkeypatch.setenv("BINANCE_API_KEY", "key")
    monkeypatch.setenv("BINANCE_API_SECRET", "secret")
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("FEE_RATE", "0.001")
    monkeypatch.setenv("MIN_PROFIT_PCT", "0.2")
    monkeypatch.setenv("TRADE_AMOUNT", "0.005")
    monkeypatch.setenv("MAX_PRICE_AGE_MS", "800")
    monkeypatch.setenv("COOLDOWN_S", "10")

    settings = Settings.from_env()
    assert settings.dry_run is False
    assert settings.api_key == "key"
    assert settings.fee_rate == pytest.approx(0.001)
    assert settings.min_profit_pct == pytest.approx(0.2)
    assert settings.trade_amount == pytest.approx(0.005)
    assert settings.max_price_age_ms == 800
    assert settings.cooldown_s == pytest.approx(10.0)


def test_real_mode_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """DRY_RUN=false sin credenciales lanza ValueError."""
    monkeypatch.setenv("DRY_RUN", "false")
    with pytest.raises(ValueError, match="BINANCE_API_KEY"):
        Settings.from_env()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fee_rate": -0.001},
        {"min_profit_pct": -0.1},
        {"trade_amount": 0.0},
        {"max_price_age_ms": 0},
        {"cooldown_s": -1.0},
        {"pairs": ("BTCUSDT", "ETHUSDT")},
    ],
)
def test_invalid_values_rejected(kwargs: dict) -> None:
    """Valores incoherentes se rechazan en la construcción de Settings."""
    with pytest.raises(ValueError):
        Settings(api_key="", api_secret="", **kwargs)
