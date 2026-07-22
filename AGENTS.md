# AGENTS.md — crypto-triangulation

## Descripción

Bot de arbitraje triangular en Binance Spot (BTCUSDT / ETHUSDT / ETHBTC).
Detecta ciclos rentables con datos bookTicker en tiempo real y opera
(opcionalmente) 3 órdenes market secuenciales.

## Estructura

- `triangulation/config.py` — Settings desde .env (fee, umbrales, dry_run)
- `triangulation/models.py` — BookTicker dataclass
- `triangulation/storage.py` — Precios thread-safe con frescura
- `triangulation/strategy.py` — Matemática de arbitraje (2 direcciones)
- `triangulation/execution.py` — Cliente Binance + executor (dry-run aware)
- `triangulation/market_data.py` — WebSocket bookTicker
- `triangulation/engine.py` — Orquestación tick → evaluación → ejecución
- `tests/` — pytest (estrategia, config, engine)
- `main.py` — Entrypoint

## Comandos

- Instalar: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt`
- Ejecutar: `python main.py`
- Tests: `pytest`
- Lint/tipos: `ruff check . && mypy --ignore-missing-imports triangulation main.py`

## Convenciones

- Python 3.11+, type hints en todas las firmas públicas, docstrings estilo Google
- Docstrings/comentarios en español; identificadores en inglés
- Lógica de dominio en `strategy.py`/`engine.py`; `main.py` solo cablea dependencias
- YAGNI: no añadir features sin validar rentabilidad primero

## Reglas de dominio (NO romper)

- `FEE_RATE` default 0.00075 (0.075% con BNB); el profit se evalúa NETO de fees ×3 patas
- `DRY_RUN=true` por defecto; nunca activar ejecución real sin confirmación del usuario
- Solo evaluar con los 3 precios frescos (< `MAX_PRICE_AGE_MS`); nunca mezclar ticks antiguos
- Verificar liquidez top-of-book en las 3 patas antes de operar
- Respetar `LOT_SIZE` y `MIN_NOTIONAL` de exchangeInfo antes de enviar órdenes
- Si una pata falla en ejecución real: abortar restantes + log crítico (no hay unwind)

## Configuración (.env)

`BINANCE_API_KEY`, `BINANCE_API_SECRET`, `DRY_RUN`, `FEE_RATE`,
`MIN_PROFIT_PCT`, `TRADE_AMOUNT`, `MAX_PRICE_AGE_MS`, `COOLDOWN_S`
