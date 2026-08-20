"""Tests del resumidor de log para la decisión de viabilidad."""

from triangulation.logreport import parse_log


def test_logreport_counts_above_thresholds(tmp_path) -> None:
    """Cuenta oportunidades totales, mejores y las que superan cada umbral."""
    p = tmp_path / "s.log"
    p.write_text(
        "net_profit=+0.0003%\n"
        "net_profit=+0.2400%\n"
        "net_profit=+0.0100%\n"
    )
    r = parse_log(str(p))
    assert r["total"] == 3
    assert r["best"] == 0.24
    assert r["above"][0.0] == 3
    assert r["above"][0.05] == 1
    assert r["above"][0.1] == 1


def test_logreport_empty_file(tmp_path) -> None:
    """Un archivo sin oportunidades produce total 0 y best None."""
    p = tmp_path / "empty.log"
    p.write_text("no hay oportunidades\n")
    r = parse_log(str(p))
    assert r["total"] == 0
    assert r["best"] is None
    assert r["above"][0.05] == 0


def test_logreport_ignores_non_matching_lines(tmp_path) -> None:
    """Líneas sin el patrón net_profit se ignoran."""
    p = tmp_path / "mixed.log"
    p.write_text(
        "INFO Iniciando bot\n"
        "net_profit=+0.0867%\n"
        "net_profit=-0.0200%\n"
        "net_profit=+0.2449%\n"
    )
    r = parse_log(str(p))
    assert r["total"] == 2
    assert r["best"] == 0.2449
    assert r["above"][0.0] == 2
