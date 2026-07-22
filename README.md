# crypto-triangulation

Bot de **arbitraje triangular** en Binance Spot sobre el triángulo `BTCUSDT / ETHUSDT / ETHBTC`. Consume precios en tiempo real vía WebSocket (`bookTicker`), detecta ciclos con profit neto positivo (descontando comisiones de las 3 operaciones) y, opcionalmente, ejecuta las 3 órdenes market del ciclo.

> **Modo seguro por defecto:** el bot arranca en `DRY_RUN=true` — solo detecta y loguea oportunidades, **no envía órdenes**.

## ✨ Crear `.env` usando este archivo de ejemplo `env.sample`

- `Binance API Token` - [Binance API Token](https://www.binance.com/es/support/faq/360002502072) (requerido solo si `DRY_RUN=false`)
  - `BINANCE_API_KEY`=<BINANCE_API_KEY>
  - `BINANCE_API_SECRET`=<BINANCE_API_SECRET>

### Parámetros de estrategia (`.env`)

| Variable | Default | Descripción |
|---|---|---|
| `DRY_RUN` | `true` | `true`: simula y loguea; `false`: opera con dinero real |
| `FEE_RATE` | `0.00075` | Comisión por operación (0.075% pagando con BNB) |
| `MIN_PROFIT_PCT` | `0.1` | Profit neto mínimo post-fees (%) para operar |
| `TRADE_AMOUNT` | `0.002` | Monto por ciclo en BTC |
| `MAX_PRICE_AGE_MS` | `1500` | Frescura máxima de precios para evaluar (ms) |
| `COOLDOWN_S` | `5` | Espera mínima entre ejecuciones (s) |

<br />

## ✨ Cómo usarlo

> Descarga el código

```bash
$ git clone https://github.com/RobertArzolaC/crypto-triangulation
$ cd crypto-triangulation
```

<br />

## ✨ Instalando dependencias y ejecutando la aplicación

> Instalar módulos a través de `venv`

```bash
$ python3 -m venv venv
$ source venv/bin/activate
$ pip3 install -r requirements.txt
```

<br />

> `Iniciar la aplicación`

```bash
$ python main.py
```

<br />

> `Tests y chequeos de calidad` (requieren `pip install -r requirements-dev.txt`)

```bash
$ pytest
$ ruff check .
$ mypy --ignore-missing-imports triangulation main.py
```

<br />

## ✨ Cómo funciona la estrategia

Con numéraire BTC, se evalúan las dos direcciones del triángulo en cada tick:

- **FORWARD:** BTC → vende `BTCUSDT`@bid → USDT → compra `ETHUSDT`@ask → ETH → vende `ETHBTC`@bid → BTC
- **REVERSE:** BTC → compra `ETHBTC`@ask → ETH → vende `ETHUSDT`@bid → USDT → compra `BTCUSDT`@ask → BTC

Una oportunidad solo se considera válida si cumple **todas** estas condiciones:

1. **Profit neto > `MIN_PROFIT_PCT`** tras descontar `FEE_RATE` en cada una de las 3 patas.
2. **Liquidez suficiente**: el top-of-book (`bid_qty`/`ask_qty`) cubre la cantidad requerida en cada pata.
3. **Precios frescos**: los 3 pares tienen ticks con menos de `MAX_PRICE_AGE_MS` de antigüedad.
4. **Filtros de Binance**: las cantidades respetan `LOT_SIZE` y `MIN_NOTIONAL` de `exchangeInfo`.

Además, un **cooldown** (`COOLDOWN_S`) evita ejecuciones repetidas sobre la misma oportunidad.

## ⚠️ Riesgos conocidos

- **Órdenes market secuenciales:** el precio de ejecución real puede deslizar (slippage) respecto a la simulación. El umbral `MIN_PROFIT_PCT` actúa como colchón.
- **Fallo parcial:** si una pata falla en modo real, las restantes se abortan y se loguea una alerta crítica. **No hay unwind automático** — revisar la posición manualmente.
- **Top-of-book:** la simulación usa solo el mejor nivel del libro; montos grandes pueden sufrir más slippage del estimado.

## ✨ Estructura base de código

```bash
< crypto-triangulation >
   |
   |-- triangulation/
   |      |-- config.py           # Settings desde variables de entorno
   |      |-- logger.py           # Configuración centralizada de logging
   |      |-- models.py           # BookTicker (bid/ask + cantidades + timestamp)
   |      |-- storage.py          # Almacén thread-safe de últimos precios
   |      |-- strategy.py         # Motor de arbitraje (2 direcciones, fees, liquidez)
   |      |-- execution.py        # Cliente Binance + executor (dry-run aware)
   |      |-- market_data.py      # WebSocket bookTicker
   |      |-- engine.py           # Orquestación tick -> evaluación -> ejecución
   |-- tests/                     # Suite pytest (estrategia, config, engine)
   |-- main.py                    # Entrypoint
   |-- requirements.txt           # Dependencias de runtime
   |-- requirements-dev.txt       # Dependencias de desarrollo (pytest, ruff, mypy)
   |-- env.sample                 # Plantilla de configuración
   |-- AGENTS.md                  # Contexto para agentes de IA
   |-- *************************************************************************************
```
