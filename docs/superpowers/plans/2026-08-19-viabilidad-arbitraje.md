# Validación de Viabilidad + Fix de Ejecución — Implementation Plan

> **ESTADO: DETENIDO en la puerta Go/No-Go A (2026-08-19).**
> La Fase A se completó y arrojó un **NO-GO** decisivo: con las fees taker reales de
> Binance (0.225% total con BNB; 0.30% sin BNB), solo 37/1567 oportunidades del log
> superarían el umbral de 0.05% (todas de una única ventana transitoria), y 0/1567 sin
> BNB — y ello sin contabilizar slippage/latencia/FOK parciales. Por decisión del usuario
> no se construyen las Fases B–D. Fases A1–A3 implementadas y commiteadas; B, C y D
> canceladas.

**Goal:** Determinar con datos reales si el bot de arbitraje triangular es rentable (fees corregidas + simulación de fill) y dejar la ejecución real segura (validación de fills + reconciliación + kill-switch) antes de cualquier capital.

**Architecture:** Corregir la asunción de fees (3× optimista), añadir observabilidad/backtest sobre datos grabados, y endurecer la ejecución real. TDD, sin tocar lógica de `strategy.py`.

**Tech Stack:** Python 3.11+, aiohttp, websockets, pytest, ruff, mypy.

## Global Constraints
- Python 3.11+, type hints en firmas públicas, docstrings Google en español, identificadores en inglés.
- `FEE_RATE` por pata **taker**: `0.00075` con BNB, `0.001` sin BNB (verificado en Binance 2026-08-19: promos FDUSD son solo maker).
- `DRY_RUN=true` por defecto; ninguna fase activa ejecución real sin confirmación explícita.
- No tocar `strategy.py` (la lógica de dominio ya es correcta).
- `pytest` para tests; `ruff check . && mypy --ignore-missing-imports triangulation main.py`.

---

## Fase A — Corregir fees y re-evaluar viabilidad

### Task A1: Corregir FEE_RATE default y docstring
**Files:** Modify `triangulation/config.py:14,28`; Test `tests/test_config.py`
- [ ] **Step 1 (failing test):**
```python
def test_fee_rate_default_is_taker_bnb():
    assert Settings(api_key="", api_secret="").fee_rate == 0.00075
```
- [ ] **Step 2:** Run `pytest tests/test_config.py -v` → FAIL
- [ ] **Step 3:** `fee_rate: float = 0.00075`; docstring: "Comisión taker por pata (0.075% con BNB; 0.1% sin BNB). El bot usa LIMIT FOK al libro, que siempre llena como taker (las promos 0% de FDUSD son solo maker)."
- [ ] **Step 4:** `pytest` → PASS
- [ ] **Step 5:** `git commit -m "fix: fee_rate taker real 0.075% (promos FDUSD son maker-only)"`

### Task A2: Utilidad de verificación de fees
**Files:** Create `triangulation/fees.py`; Modify `.env.example`; Test `tests/test_fees.py`
- [ ] **Step 1 (failing test):**
```python
def test_recommended_rate_uses_bnb_discount():
    assert recommended_fee_rate(bnb_balance=1.0) == 0.00075
    assert recommended_fee_rate(bnb_balance=0.0) == 0.001
```
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:**
```python
def recommended_fee_rate(bnb_balance: float) -> float:
    return 0.00075 if bnb_balance > 0 else 0.001
```
Más `python -m triangulation.fees`: consulta `/api/v3/account`, imprime balance BNB, la fee taker recomendada y las 3 símbolos del triángulo.
- [ ] **Step 4:** `pytest` → PASS
- [ ] **Step 5:** commit `feat: utilidad de verificación de fees reales`

### Task A3: Resumidor de log para decisión go/no-go
**Files:** Create `triangulation/logreport.py`; Test `tests/test_logreport.py`
- [ ] **Step 1 (failing test):**
```python
def test_logreport_counts_above_thresholds(tmp_path):
    p = tmp_path / "s.log"
    p.write_text("net_profit=+0.0003%\nnet_profit=+0.2400%\nnet_profit=+0.0100%\n")
    r = parse_log(str(p))
    assert r["total"] == 3 and r["above"][0.05] == 1 and r["best"] == 0.24
```
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** parsea `net_profit=+X%`, devuelve total, mejor, y conteos por umbral (0, 0.05, 0.1). CLI `python -m triangulation.logreport server-log.txt`.
- [ ] **Step 4:** `pytest` → PASS; correr contra `server-log.txt` para el reporte.
- [ ] **Step 5:** commit `feat: resumidor de log para decisión de viabilidad`

**Go/No-Go A:** si con fees corregidas (0.075%/pata) las oportunidades > umbral son escasas o nulas, parar y no continuar a Fase B–D.

---

## Fase B — Fix de ejecución real

### Task B1: Validar status FILLED por pata
**Files:** Modify `triangulation/execution.py:230-247`; Test `tests/test_execution.py`
- [ ] **Step 1 (failing test):** mock client con `create_fok_order` devolviendo `{"status": "EXPIRED"}`, `{"status": "FILLED"}` y `ConnectionError`; `execute(dry_run=False)` debe devolver `False` si alguna no es `FILLED`.
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** en el loop, `if isinstance(result, BaseException) or result.get("status") != "FILLED": success = False` + `logger.critical`.
- [ ] **Step 4:** `pytest` → PASS
- [ ] **Step 5:** commit `fix: validar status FILLED en las 3 patas`

### Task B2: newClientOrderId + reconciliación
**Files:** Modify `execution.py` (`create_fok_order`, nueva `get_order`); Test `tests/test_execution.py`
- [ ] **Step 1 (failing test):** `create_fok_order` incluye `newClientOrderId` en params; `get_order(symbol, client_order_id)` llama a `/api/v3/order` y devuelve status.
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** añadir `newClientOrderId=f"tri-{int(time.time()*1000)}"`; método `get_order` con `recvWindow`.
- [ ] **Step 4:** `pytest` → PASS
- [ ] **Step 5:** commit `feat: ids de cliente + reconciliación de fills`

### Task B3: Kill-switch
**Files:** Modify `execution.py`/`engine.py`; Test `tests/test_engine.py`
- [ ] **Step 1 (failing test):** crear archivo `.kill` → `engine` rechaza ejecutar un ciclo y loguea crítico; borrar archivo → ejecuta de nuevo.
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** `engine._process_tick` chequea `os.path.exists(KILL_FILE)` antes de `executor.execute`.
- [ ] **Step 4:** `pytest` → PASS
- [ ] **Step 5:** commit `feat: kill-switch por archivo`

### Task B4: PnL real por ciclo
**Files:** Modify `execution.py`; Test `tests/test_execution.py`
- [ ] **Step 1 (failing test):** dados fills `(symbol, side, price, qty)` de las 3 patas, `compute_realized_pnl` devuelve el PnL neto en BTC aplicando fee por pata.
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** implementar `compute_realized_pnl(fills, fee_rate)` usando el mismo recorrido de `strategy.evaluate` pero con precios de fill reales; loggear por ciclo.
- [ ] **Step 4:** `pytest` → PASS
- [ ] **Step 5:** commit `feat: PnL real por ciclo`

---

## Fase C — Grabación + backtest con simulación de fill

### Task C1: Grabador de bookTicker a JSONL
**Files:** Create `triangulation/recorder.py`; Test `tests/test_recorder.py`
- [ ] **Step 1 (failing test):** con ticks fake, escribe JSONL con `ts, symbol, bid, ask, bid_qty, ask_qty`.
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** reutiliza `BookTickerStream` + callback que serializa a JSONL (`RECORD=1 python -m triangulation.recorder`).
- [ ] **Step 4:** `pytest` → PASS
- [ ] **Step 5:** commit `feat: grabador de bookTicker`

*(Correr el grabador 1–2 semanas antes de C2.)*

### Task C2: Backtest con fill-simulado
**Files:** Create `triangulation/backtest.py`; Test `tests/test_backtest.py`
- [ ] **Step 1 (failing test):** sobre un JSONL sintético, el backtest debe simular fills al precio del libro + slippage (`slippage_bps`) con `fee=0.00075`, y reportar PnL simulado vs. top-of-book; assert sobre un caso conocido.
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** reordenar ticks por `ts`, reconstruir libro por símbolo, evaluar ciclo con `find_best_cycle` y aplicar slippage a cada pata.
- [ ] **Step 4:** `pytest` → PASS
- [ ] **Step 5:** commit `feat: backtest con simulación de fill`

**Go/No-Go C:** live solo si PnL simulado neto > 0 consistente.

---

## Fase D — Escala de test
**Files:** Modify `.env`/`.env.example`; Test `tests/test_config.py`
- [ ] **Step 1 (failing test):** `TRADE_AMOUNT=0.1` se carga y `__post_init__` no rompe.
- [ ] **Step 2/3/4:** subir `TRADE_AMOUNT` a `0.1` en dry-run, correr, `pytest` → PASS.
- [ ] **Step 5:** commit `chore: escala de test 0.1 BTC (dry-run)`

---

## Self-review
- Cobertura: A→fees, B→ejecución, C→backtest, D→escala. ✓
- Sin placeholders; cada task tiene test+impl+commit. ✓
- Tipos consistentes: `recommended_fee_rate(bnb_balance: float) -> float`, `parse_log(path) -> dict`, `compute_realized_pnl(fills, fee_rate)`. ✓
