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
| `STATS_INTERVAL_S` | `60` | Intervalo entre líneas STATS de proximidad (s) |

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

Además, un **cooldown** (`COOLDOWN_S`) evita ejecuciones repetidas sobre la misma oportunidad. El cooldown solo bloquea la *ejecución*: la **medición es continua** y nunca se pausa.

## 📈 Log de proximidad a rentabilidad

El bot mide **cada tick fresco** y reporta qué tan cerca está el mercado del umbral de ejecución, sin necesidad de operar:

- **Línea `STATS`** cada `STATS_INTERVAL_S` segundos:

  ```
  STATS 2h14m | evals=48210 saltadas=13 | mejor=-0.0312% (FORWARD) | faltan 0.1312pp al umbral 0.100% | p50=-0.1801% p95=-0.0987% | sobre_umbral=0
  ```

  - `mejor`: mejor profit neto (post-fees) visto en la sesión y su dirección.
  - `faltan ... pp`: distancia en puntos porcentuales del mejor ciclo al umbral `MIN_PROFIT_PCT`. Si algún ciclo lo superó, verás `supera el umbral por ...`.
  - `p50`/`p95`: percentiles de la ventana reciente (últimas ~10k evaluaciones).
  - `sobre_umbral`: ciclos que habrían disparado ejecución (aunque el cooldown los haya bloqueado).

- **Alerta inmediata** cada vez que se bate el máximo histórico de la sesión:

  ```
  Nuevo mejor ciclo: -0.0312% (FORWARD) | faltan 0.1312pp al umbral 0.100%
  ```

- **Línea `RESUMEN`** al detener el bot (Ctrl+C o `SIGTERM` — ej. `systemctl stop`) con las estadísticas finales de la sesión.

El archivo `crypto.log` rota automáticamente (5 MB × 3 respaldos) para operación 24/7.

## ⚠️ Riesgos conocidos

- **Órdenes market secuenciales:** el precio de ejecución real puede deslizar (slippage) respecto a la simulación. El umbral `MIN_PROFIT_PCT` actúa como colchón.
- **Fallo parcial:** si una pata falla en modo real, las restantes se abortan y se loguea una alerta crítica. **No hay unwind automático** — revisar la posición manualmente.
- **Top-of-book:** la simulación usa solo el mejor nivel del libro; montos grandes pueden sufrir más slippage del estimado.

## 🖥️ Despliegue 24/7 en un droplet (medición de rentabilidad)

Recomendación: dejar el bot en **`DRY_RUN=true` durante 2–4 semanas** para recolectar evidencia real de proximidad a la rentabilidad antes de arriesgar capital. Un droplet básico (~$6 USD/mes) es suficiente: el bot consume CPU y RAM mínimas.

1. **Crear el droplet** (Ubuntu 24.04). Región recomendada: la más cercana a los servidores de Binance (AWS Tokio); en DigitalOcean, `SGP1` (Singapur) suele ser la opción más próxima. Menos latencia = ticks más frescos y medición más fiel.

2. **Instalar y configurar:**

   ```bash
   $ sudo apt update && sudo apt install -y python3-venv git
   $ git clone https://github.com/RobertArzolaC/crypto-triangulation
   $ cd crypto-triangulation
   $ python3 -m venv venv && source venv/bin/activate
   $ pip install -r requirements.txt
   $ cp env.sample .env   # edita .env: DRY_RUN=true
   ```

3. **Servicio systemd** (`/etc/systemd/system/triangulation.service`) para auto-reinicio:

   ```ini
   [Unit]
   Description=Crypto triangulation bot (dry-run)
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/crypto-triangulation
   ExecStart=/home/ubuntu/crypto-triangulation/venv/bin/python main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   $ sudo systemctl enable --now triangulation
   $ journalctl -u triangulation -f     # consola en vivo
   ```

4. **Analizar la proximidad a rentabilidad:**

   ```bash
   $ grep STATS crypto.log | tail -20        # evolución del mejor profit
   $ grep "Nuevo mejor" crypto.log | tail    # alertas de máximo histórico
   ```

**Criterio de decisión:** considera ejecución real solo si las stats muestran ciclos `sobre_umbral` frecuentes y `mejor` claramente por encima del umbral con margen para slippage. En este triángulo (BTC/ETH/USDT, muy eficiente) lo esperable es que el mejor neto se mantenga negativo la mayor parte del tiempo — los datos mandan.

## ✨ Estructura base de código

```bash
< crypto-triangulation >
   |
   |-- triangulation/
   |      |-- config.py           # Settings desde variables de entorno
   |      |-- logger.py           # Logging centralizado (rotación de archivo)
   |      |-- models.py           # BookTicker (bid/ask + cantidades + timestamp)
   |      |-- storage.py          # Almacén thread-safe de últimos precios
   |      |-- strategy.py         # Cálculo de ciclos (2 direcciones, fees, liquidez)
   |      |-- observer.py         # Métricas de proximidad a rentabilidad
   |      |-- execution.py        # Cliente Binance + executor (dry-run aware)
   |      |-- market_data.py      # WebSocket bookTicker
   |      |-- engine.py           # Orquestación tick -> medición -> ejecución
   |-- tests/                     # Suite pytest (estrategia, config, engine, observer)
   |-- main.py                    # Entrypoint
   |-- requirements.txt           # Dependencias de runtime
   |-- requirements-dev.txt       # Dependencias de desarrollo (pytest, ruff, mypy)
   |-- env.sample                 # Plantilla de configuración
   |-- AGENTS.md                  # Contexto para agentes de IA
   |-- *************************************************************************************
```
