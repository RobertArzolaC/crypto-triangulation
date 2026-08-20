"""Tests de la utilidad de verificación de fees reales."""

from triangulation.fees import recommended_fee_rate


def test_recommended_rate_uses_bnb_discount() -> None:
    """Con balance BNB se aplica el descuento taker (0.075%); sin BNB, 0.1%."""
    assert recommended_fee_rate(bnb_balance=1.0) == 0.00075
    assert recommended_fee_rate(bnb_balance=0.0) == 0.001


def test_recommended_rate_with_zero_or_negative_balance() -> None:
    """Balance BNB ausente (0 o negativo) se trata como sin descuento."""
    assert recommended_fee_rate(bnb_balance=0) == 0.001
    assert recommended_fee_rate(bnb_balance=-5.0) == 0.001
