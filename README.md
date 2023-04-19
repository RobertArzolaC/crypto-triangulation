# crypto-triangulation

## ✨ Crear `.env` usando este archivo de ejemplo `env.sample`

- `Binance API Token` - [Binance API Token](https://www.binance.com/es/support/faq/360002502072)
  - `BINANCE_API_KEY`=<BINANCE_API_KEY>
  - `BINANCE_API_SECRET`=<BINANCE_API_SECRET>

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

## ✨ Estructura base de código

El proyecto está codificado utilizando una estructura simple e intuitiva que se presenta a continuación:

```bash
< crypto-triangulation >
   |
   |-- binance_client.py                # Binance Client
   |-- binance_orders.py                # Binance Orders
   |-- binance_websocket.py             # Binance Websocket
   |-- constants.py                     # Constants
   |-- observers.py                     # Observers for Triangulation
   |-- storage.py                       # Storage for prices
   |-- strategy_triangulation.py        # Stratiegies for Triangulation
   |-- requirements.txt                 # Package dependencies
   |-- main.py                          # Start the app here
   |-- logger.py                        # Logger configuration
   |-- .env.sample                      # Inject Configuration via Environment Variables
   |-- *************************************************************************************
```
