"""Utilidad para verificar la comisión taker real aplicable a las patas.

El bot opera con órdenes LIMIT FOK al top-of-book, que siempre llenan como
* taker * (comprar al ask y vender al bid cruza el spread). Las promociones 0%
de los pares FDUSD en Binance aplican solo a maker, por lo que la comisión real
por pata es la taker estándar: 0.075% con descuento BNB, o 0.1% sin BNB.
"""

import asyncio
import logging

from triangulation.config import Settings
from triangulation.execution import BinanceClient

logger = logging.getLogger(__name__)

TAKER_FEE_WITH_BNB = 0.00075
TAKER_FEE_NO_BNB = 0.001


def recommended_fee_rate(bnb_balance: float) -> float:
    """Devuelve la comisión taker por pata según si hay saldo BNB.

    Args:
        bnb_balance: Saldo de BNB disponible en la cuenta.

    Returns:
        TAKER_FEE_WITH_BNB si hay saldo BNB; TAKER_FEE_NO_BNB en caso contrario.
    """
    return TAKER_FEE_WITH_BNB if bnb_balance > 0 else TAKER_FEE_NO_BNB


async def _fetch_bnb_balance(settings: Settings) -> float:
    """Consulta /api/v3/account y extrae el saldo libre de BNB."""
    client = BinanceClient(settings.api_key, settings.api_secret, settings.api_base_url)
    try:
        data = await client.get_account()
        for asset in data.get("balances", []):
            if asset["asset"] == "BNB":
                return float(asset["free"])
        return 0.0
    finally:
        await client.close()


async def _report(settings: Settings) -> None:
    """Imprime la fee recomendada y los símbolos del triángulo."""
    balance = await _fetch_bnb_balance(settings)
    fee = recommended_fee_rate(balance)
    print(f"Saldo BNB libre: {balance}")
    print(f"Fee taker recomendada por pata: {fee * 100:.3f}%")
    print(f"Fee total del ciclo (3 patas): {fee * 3 * 100:.3f}%")
    print(f"Pares del triángulo: {', '.join(settings.pairs)}")


def main() -> None:
    """Entrypoint CLI: verifica la fee aplicable leyendo la configuración."""
    from dotenv import load_dotenv

    load_dotenv()
    settings = Settings.from_env()
    asyncio.run(_report(settings))


if __name__ == "__main__":
    main()
