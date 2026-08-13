"""Configuración de la aplicación a partir de variables de entorno."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Parámetros de configuración del bot de arbitraje triangular.

    Attributes:
        api_key: API key de Binance (opcional en dry-run).
        api_secret: API secret de Binance (opcional en dry-run).
        fee_rate: Comisión promedio por pata (ej. 0.00025 = 0.025% promedio si dos pares tienen 0% fee y uno 0.075%).
        min_profit_pct: Umbral de profit neto (post-fees) en porcentaje.
        trade_amount: Monto base por ciclo de arbitraje, en BTC.
        dry_run: True solo simula y loguea oportunidades; False opera de verdad.
        max_price_age_ms: Frescura máxima de los precios para evaluar (ms).
        cooldown_s: Espera mínima entre ejecuciones (segundos).
        ws_base_url: URL base del WebSocket de Binance.
        api_base_url: URL base de la API REST de Binance.
        log_file: Ruta del archivo de log (vacío desactiva salida a archivo).
        pairs: Los 3 pares del triángulo en orden (ej. BTCFDUSD, ETHFDUSD, ETHBTC).
    """

    api_key: str
    api_secret: str
    fee_rate: float = 0.00025
    min_profit_pct: float = 0.1
    trade_amount: float = 0.002
    dry_run: bool = True
    max_price_age_ms: int = 1500
    cooldown_s: float = 5.0
    ws_base_url: str = "wss://stream.binance.com:9443/ws/"
    api_base_url: str = "https://api.binance.com"
    log_file: str = "crypto.log"
    pairs: tuple[str, str, str] = ("BTCFDUSD", "ETHFDUSD", "ETHBTC")

    def __post_init__(self) -> None:
        """Valida que los parámetros sean coherentes."""
        if self.fee_rate < 0:
            raise ValueError("fee_rate no puede ser negativo")
        if self.min_profit_pct < 0:
            raise ValueError("min_profit_pct no puede ser negativo")
        if self.trade_amount <= 0:
            raise ValueError("trade_amount debe ser positivo")
        if self.max_price_age_ms <= 0:
            raise ValueError("max_price_age_ms debe ser positivo")
        if self.cooldown_s < 0:
            raise ValueError("cooldown_s no puede ser negativo")
        if len(self.pairs) != 3:
            raise ValueError("pairs debe contener exactamente 3 símbolos")

    @classmethod
    def from_env(cls) -> "Settings":
        """Construye Settings leyendo variables de entorno con defaults.

        Returns:
            Instancia de Settings con la configuración resuelta.

        Raises:
            ValueError: Si DRY_RUN=false y faltan las credenciales de Binance.
        """
        dry_run = _get_bool("DRY_RUN", True)
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")
        if not dry_run and (not api_key or not api_secret):
            raise ValueError(
                "BINANCE_API_KEY y BINANCE_API_SECRET son requeridas cuando DRY_RUN=false"
            )
        return cls(
            api_key=api_key,
            api_secret=api_secret,
            fee_rate=_get_float("FEE_RATE", 0.00025),
            min_profit_pct=_get_float("MIN_PROFIT_PCT", 0.1),
            trade_amount=_get_float("TRADE_AMOUNT", 0.002),
            dry_run=dry_run,
            max_price_age_ms=_get_int("MAX_PRICE_AGE_MS", 1500),
            cooldown_s=_get_float("COOLDOWN_S", 5.0),
            pairs=_get_tuple("PAIRS", ("BTCFDUSD", "ETHFDUSD", "ETHBTC")),
        )


def _get_float(name: str, default: float) -> float:
    """Lee un float desde el entorno; usa el default si no está definido."""
    raw = os.getenv(name)
    return float(raw) if raw else default


def _get_int(name: str, default: int) -> int:
    """Lee un int desde el entorno; usa el default si no está definido."""
    raw = os.getenv(name)
    return int(raw) if raw else default


def _get_bool(name: str, default: bool) -> bool:
    """Lee un bool desde el entorno ('1', 'true', 'yes', 'on' = True)."""
    raw = os.getenv(name)
    if not raw:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _get_tuple(name: str, default: tuple[str, str, str]) -> tuple[str, str, str]:
    """Lee una tupla de 3 strings desde el entorno (separados por coma)."""
    raw = os.getenv(name)
    if not raw:
        return default
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 3:
        raise ValueError(f"{name} debe contener exactamente 3 símbolos separados por coma")
    return (parts[0], parts[1], parts[2])
