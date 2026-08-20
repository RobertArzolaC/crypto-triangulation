"""Resumen de un log de oportunidades para la decisión de viabilidad.

Parsea las líneas del observador con el patrón `net_profit=+X%` y reporta el
total de oportunidades, el mejor profit neto y cuántas superan varios umbrales.
Permite re-evaluar con fees corregidas (ver Task A1) si la estrategia sigue
siendo viable antes de considerar una ejecución real.
"""

import re
from typing import Any

_NET_PROFIT_RE = re.compile(r"net_profit=\+([0-9.]+)%")


def parse_log(path: str, thresholds: tuple[float, ...] = (0.0, 0.05, 0.1)) -> dict[str, Any]:
    """Analiza un log y resume las oportunidades de profit neto positivo.

    Args:
        path: Ruta del archivo de log.
        thresholds: Umbrales de profit neto (%) sobre los que se cuenta.

    Returns:
        Dict con "total" (oportunidades), "best" (mejor profit neto o None),
        "above" (dict {umbral: conteo de oportunidades >= umbral}).
    """
    profits: list[float] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            match = _NET_PROFIT_RE.search(line)
            if match:
                profits.append(float(match.group(1)))

    best = max(profits) if profits else None
    return {
        "total": len(profits),
        "best": best,
        "above": {t: sum(1 for p in profits if p >= t) for t in thresholds},
    }


def main() -> None:
    """Entrypoint CLI: `python -m triangulation.logreport <logfile>`."""
    import sys

    if len(sys.argv) < 2:
        print("Uso: python -m triangulation.logreport <archivo.log>")
        raise SystemExit(1)

    result = parse_log(sys.argv[1])
    print(f"Oportunidades totales: {result['total']}")
    print(f"Mejor profit neto: {result['best']:+.4f}%" if result["best"] is not None else "Mejor profit neto: n/a")
    for threshold, count in result["above"].items():
        print(f"  >= {threshold:.2f}%: {count}")


if __name__ == "__main__":
    main()
