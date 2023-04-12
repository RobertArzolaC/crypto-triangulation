# import keyboard
from re import T
from threading import Thread
import websocket
import rel
import json
from datetime import datetime
import time
import logging
from rich import print as pprint
from typing import List, Dict
import redis
# ordenes
import apikey
from binance.client import Client # trae client
from binance.enums import * #para generar ordenes
# import sys
# from PyQt5.QtWidgets import QInputDialog
# import keyboard
# from binance.error import ClientError
# from binance.spot import Spot
# from binance.client import Client
# logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename=medicion.txt)
#sys.stdin.readline
#funciona las ordenes
client = Client(apikey.API_KEY , apikey.API_SECRET)#, tld='com')

par_derecha = input("coloque par derecha ").upper()
par_base = input("coloque par base ").upper()
par_izquierda = input("coloque par izquierda ").upper()
    # print("filtro de volumen True o False ")
use_qty_tex = input("filtro de volumen True o False ")
if use_qty_tex == "True":
    use_qty = True
    # print ("volumen btcusdt")
    filter_derecha = float(input("volumen btcusdt "))
    # print ("volumen ethusdt")
    filter_base = float (input("volumen ethusdt "))
    # print ("volumen ethbtc")
    filter_izqierda =  float(input("volumen ethbtc "))
else:
    use_qty = False

# print("comision por cada transaccion")
com = float(input ("comision por cada transaccion "))
comision = round(float((100-com)/100),2)

porcentual_ganancia= round(float(input ("coloque porcentaje de ganancia minimo ")),2)

#metodo demo o real
metodo = input("demo (genera archivo txt) o real ")
if metodo == "demo":
    texto = input ("nombre archivo ")
    # f = open(texto,'a')
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename=texto)

if metodo == "real":
    tipo_operacion = input("mercado o limite ")
    orden_inicial_eth = float(input("ordenes equivalentes eth maximo 4 digitos "))
    if tipo_operacion == "limite":
        while True:
            ordenes = client.get_open_orders()
            if (len(ordenes) != 0):
                print("cantidad de ordenes abiertas ",len(ordenes))
                time.sleep(60)
            else:
                print("no hay ordens continuo iniciales ")
                break


def get_values_derecha(list_dicts: list):
    # logging.debug("1")#mide timepo
    """Triangulo por derecha"""
    bid_btcusdt = round(float(list_dicts[0].get('b')),2)
    bid_btcusdt_tex = str(bid_btcusdt)
    bid_qty_btcusdt = round(float(list_dicts[0].get('B')),5)
    cant_usdt = round(float(bid_btcusdt * comision),8)

    ask_ethusdt = round(float(list_dicts[2].get('a')),2)
    ask_ethusdt_tex = str(ask_ethusdt)
    ask_qty_ethusdt = round(float(list_dicts[2].get('A')),4)
    cant_eth = round(float((cant_usdt/ask_ethusdt) * comision),8)

    bid_ethbtc = round(float(list_dicts[1].get('b')),6)
    bid_ethbtc_tex = str(bid_ethbtc)
    bid_qty_ethbtc = round(float(list_dicts[1].get('B')),4)
    cant_btc = round(float(bid_ethbtc * cant_eth * comision),8)
    # logging.debug("2")

    profit = round(float((cant_btc - 1) * 100),2)
    # if profit > profit_anterior:
    #     profit_anterior = profit
    #     print ("profit guardado der ", profit_anterior)
    if profit > porcentual_ganancia:
        # print("profit derecha ", profit)
        if use_qty:
            # print("analizando volumenes derecha")
            #logging.info(list_dicts)
            if bid_qty_btcusdt >= filter_derecha and \
                ask_qty_ethusdt >= filter_base and \
                bid_qty_ethbtc >= filter_izqierda :
                if metodo == "real":
                    # orden_libro_btcusdt_derecha = bid_ethbtc*orden_inicial_eth
                    ord_lib_btcustd_derecha_n = round(float(ask_ethusdt*orden_inicial_eth/bid_btcusdt),5)
                    if tipo_operacion == "mercado":
                        client.create_order(
                            symbol = par_derecha,
                            side = "SELL",
                            type = "MARKET",
                            quantity = ord_lib_btcustd_derecha_n
                            )
                        client.create_order(
                            symbol = par_base,
                            side = "BUY",
                            type = "MARKET",
                            quantity = orden_inicial_eth
                            )
                        client.create_order(
                            symbol = par_izquierda,
                            side = "SELL",
                            type = "MARKET",
                            quantity = orden_inicial_eth
                        )
                        print("emite operaciones mercado derecha ")
                        time.sleep(60)
                    elif tipo_operacion == "limite":
                        client.create_order(
                            symbol = par_derecha,
                            side = "SELL",
                            price = bid_btcusdt_tex,
                            type = "LIMIT",
                            timeInForce = "GTC",
                            quantity = ord_lib_btcustd_derecha_n
                            )
                        client.create_order(
                            symbol = par_base,
                            side = "BUY",
                            price = ask_ethusdt_tex,
                            type = "LIMIT",
                            timeInForce = "GTC",
                            quantity = orden_inicial_eth
                            )
                        client.create_order(
                            symbol = par_izquierda,
                            side = "SELL",
                            price = bid_ethbtc_tex,
                            type = "LIMIT",
                            timeInForce = "GTC",
                            quantity = orden_inicial_eth
                        )
                        print("emite operaciones limites derecha ")
                        time.sleep(60)
                        while True:
                            ordenes = client.get_open_orders()
                            if (len(ordenes) != 0):
                                print("cantidad de ordenes abiertas ",len(ordenes))
                                time.sleep(60)
                            else:
                                print("no hay ordens derecha ")
                                break
                elif metodo == "demo":
                    logging.info(f'Derecha -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
                    logging.info(f'\t bid qty btcusdt: {bid_qty_btcusdt}')
                    logging.info(f'\t ask qty ethusdt: {ask_qty_ethusdt}')
                    logging.info(f'\t bid qty ethbtc: {bid_qty_ethbtc}')
                    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename=texto)
                    # time.sleep(10)
                    # f.write( ' \n ' + "profi derecha ")
                    # f.write(str(round(profit,4)))
                    # f.close()
            else:
                print("no hay volumen derecha")
                # logging.info(list_dicts)
                # logging.info(f'Derecha -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
                # logging.info(f'\t bid qty btcusdt: {bid_qty_btcusdt}')
                # logging.info(f'\t ask qty ethusdt: {ask_qty_ethusdt}')
                # logging.info(f'\t bid qty ethbtc: {bid_qty_ethbtc}')
        else:
            # r.set(f'{datetime.now()}', profit)
            # print("analizando precios derecha y profit ",profit)
            if metodo == "real":
                # orden_libro_btcusdt_derecha = round(bid_ethbtc*orden_inicial_eth,10)
                ord_lib_btcustd_derecha_n = round(float(ask_ethusdt*orden_inicial_eth/bid_btcusdt),5)
                if tipo_operacion == "mercado":
                    client.create_order(
                        symbol = par_derecha,
                        side = "SELL",
                        type = "MARKET",
                        quantity = ord_lib_btcustd_derecha_n
                        )
                    client.create_order(
                        symbol = par_base,
                        side = "BUY",
                        type = "MARKET",
                        quantity = orden_inicial_eth
                        )
                    client.create_order(
                        symbol = par_izquierda,
                        side = "SELL",
                        type = "MARKET",
                        quantity = orden_inicial_eth
                    )
                    print("emite operaciones mercado derecha ")
                    time.sleep(60)
                elif tipo_operacion == "limite":
                    client.create_order(
                        symbol = par_derecha,
                        side = "SELL",
                        price = bid_btcusdt_tex,
                        type = "LIMIT",
                        timeInForce = "GTC",
                        quantity = ord_lib_btcustd_derecha_n
                        )
                    client.create_order(
                        symbol = par_base,
                        side = "BUY",
                        price = ask_ethusdt_tex,
                        type = "LIMIT",
                        timeInForce = "GTC",
                        quantity = orden_inicial_eth
                        )
                    client.create_order(
                        symbol = par_izquierda,
                        side = "SELL",
                        price = bid_ethbtc_tex,
                        type = "LIMIT",
                        timeInForce = "GTC",
                        quantity = orden_inicial_eth
                    )
                    print("emite operaciones limites derecha ")
                    time.sleep(60)
                    while True:
                        ordenes = client.get_open_orders()
                        if (len(ordenes) != 0):
                            print("cantidad de ordenes abiertas ",len(ordenes))
                            time.sleep(60)
                        else:
                            print("no hay ordens salgo de while ")
                            break
            elif metodo == "demo":
                logging.info(f'Derecha -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
                logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename=texto)
                # time.sleep(10)
                # f.write( ' \n ' + "profi derecha ")
                # f.write(str(round(profit,4)))
                # f.close()
                # logging.info(list_dicts)
                # logging.info(f'Derecha -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
                # logging.info(f'\t bid qty btcusdt: {bid_qty_btcusdt}')
                # logging.info(f'\t ask qty ethusdt: {ask_qty_ethusdt}')
                # logging.info(f'\t bid qty ethbtc: {bid_qty_ethbtc}')
    else:
        print("buscando profit derecha ", profit)
            #logging.warning(f'Derecha -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
            #  print(f'Derecha -> bid_btcusdt: {bid_btcusdt} -> ask_ethusdt: {ask_ethusdt} -> bid_ethbt: {bid_ethbtc} -> cantidad_btc: {cant_btc} -> {(cant_btc-1) * 100}%')

def get_values_izquierda(list_dicts: list):
    """Triangulo por izquierda"""
    ask_ethbtc = round(float(list_dicts[1].get('a')),6)
    ask_ethbtc_tex = str(ask_ethbtc)
    ask_qty_ethbtc = round(float(list_dicts[1].get('A')),4)
    cant_eth = round(float(comision/ask_ethbtc),8)

    bid_ethusdt = round(float(list_dicts[2].get('b')),2)
    bid_ethusdt_tex = str(bid_ethusdt)
    bid_qty_ethusdt = round(float(list_dicts[2].get('B')),4)
    cant_usdt = round(float(bid_ethusdt * cant_eth * comision),8)

    ask_btcusdt = round(float(list_dicts[0].get('a')),2)
    ask_btcusdt_tex = str(ask_btcusdt)
    ask_qty_btcusdt = round(float(list_dicts[0].get('A')),5)
    cant_btc = round(float((cant_usdt/ask_btcusdt) * comision),8)

    profit = round(float((cant_btc - 1) * 100),2)
    # if profit > profit_anterior:
    #     profit_anterior = profit
    #     print ("profit guardado izq ", profit_anterior)
    if profit > porcentual_ganancia:
        # print("profit izquierda ", profit)
        if use_qty:
            # print("analizando volumenes izquierda")
            if ask_qty_ethbtc >= filter_izqierda and \
                bid_qty_ethusdt >= filter_base and \
                ask_qty_btcusdt >= filter_derecha:
                if metodo == "real":
                    # orden_libro_btcusdt_izquierda = (bid_ethusdt*orden_inicial_eth)/ask_btcusdt
                    ord_lib_btcustd_izquierda_n = round(float(ask_ethbtc*orden_inicial_eth),5)
                    if tipo_operacion == "mercado":
                        client.create_order(
                            symbol = par_izquierda,
                            side = "BUY",
                            type = "MARKET",
                            quantity = orden_inicial_eth
                        )
                        client.create_order(
                            symbol = par_base,
                            side = "SELL",
                            type = "MARKET",
                            quantity = orden_inicial_eth
                        )
                        client.create_order(
                            symbol = par_derecha,
                            side = "BUY",
                            type = "MARKET",
                            quantity=ord_lib_btcustd_izquierda_n
                        )
                        print("emite operaciones mercado izquierda ")
                        time.sleep(60)
                    elif tipo_operacion == "limite":
                        client.create_order(
                            symbol = par_izquierda,
                            side = "BUY",
                            price = ask_ethbtc_tex,
                            type = "LIMIT",
                            timeInForce = "GTC",
                            quantity = orden_inicial_eth
                        )
                        client.create_order(
                            symbol = par_base,
                            side = "SELL",
                            price = bid_ethusdt_tex,
                            type = "LIMIT",
                            timeInForce = "GTC",
                            quantity = orden_inicial_eth
                        )
                        client.create_order(
                            symbol = par_derecha,
                            side = "BUY",
                            price = ask_btcusdt_tex,
                            type = "LIMIT",
                            timeInForce = "GTC",
                            quantity = ord_lib_btcustd_izquierda_n
                        )
                        print("emite operaciones limites izquierda ")
                        time.sleep(60)
                        while True:
                            ordenes = client.get_open_orders()
                            if (len(ordenes) != 0):
                                print("cantidad de ordenes abiertas ",len(ordenes))
                                time.sleep(60)
                            else:
                                print("no hay ordens salgo de while ")
                                break
                elif metodo == "demo":
                    logging.info(f'Izquierda -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
                    logging.info(f'\t ask qty ethbtc: {ask_qty_ethbtc}')
                    logging.info(f'\t bid qty ethusdt: {bid_qty_ethusdt}')
                    logging.info(f'\t ask qty btcusdt: {ask_qty_btcusdt}')
                    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename=texto)
                    # time.sleep(10)
                    # f.write( ' \n ' + "profi izquierda " )
                    # f.write(str(round(profit,4)))
                    # f.close()
            else:
                print("no hay volumen izquierda")
                # logging.info(list_dicts)
                # logging.info(f'Izquierda -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
                # logging.info(f'\t ask qty ethbtc: {ask_qty_ethbtc}')
                # logging.info(f'\t bid qty ethusdt: {bid_qty_ethusdt}'
                # logging.info(f'\t ask qty btcusdt: {ask_qty_btcusdt}')
        else:
            if metodo == "real":
                ord_lib_btcustd_izquierda_n = round(float(ask_ethbtc*orden_inicial_eth),5)
                if tipo_operacion == "mercado":
                    client.create_order(
                        symbol = par_izquierda,
                        side = "BUY",
                        type = "MARKET",
                        quantity = orden_inicial_eth
                    )
                    client.create_order(
                        symbol = par_base,
                        side = "SELL",
                        type = "MARKET",
                        quantity = orden_inicial_eth
                    )
                    client.create_order(
                        symbol = par_derecha,
                        side = "BUY",
                        type = "MARKET",
                        quantity=ord_lib_btcustd_izquierda_n
                    )
                    print("emite operaciones mercado izquierda ")
                    time.sleep(60)
                elif tipo_operacion == "limite":
                    client.create_order(
                        symbol = par_izquierda,
                        side = "BUY",
                        price = ask_ethbtc_tex,
                        type = "LIMIT",
                        timeInForce = "GTC",
                        quantity = orden_inicial_eth
                    )
                    client.create_order(
                        symbol = par_base,
                        side = "SELL",
                        price = bid_ethusdt_tex,
                        type = "LIMIT",
                        timeInForce = "GTC",
                        quantity = orden_inicial_eth
                    )
                    client.create_order(
                        symbol = par_derecha,
                        side = "BUY",
                        price = ask_btcusdt_tex,
                        type = "LIMIT",
                        timeInForce = "GTC",
                        quantity = ord_lib_btcustd_izquierda_n
                    )
                    print("emite operaciones limites izquierda ")
                    time.sleep(60)
                    while True:
                        ordenes = client.get_open_orders()
                        if (len(ordenes) != 0):
                            print("cantidad de ordenes abiertas ",len(ordenes))
                            time.sleep(60)
                        else:
                            print("no hay ordens salgo de while ")
                            break
            elif metodo == "demo":
                logging.info(f'Izquierda -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
                logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename=texto)
                # time.sleep(10)
                # f.write( ' \n ' + "profi izquierda ")
                # f.write(str(round(profit,4)))
                # f.close()
            # logging.info(list_dicts)
            # logging.info(f'Izquierda -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
            # logging.info(f'\t ask qty ethbtc: {ask_qty_ethbtc}')
            # logging.info(f'\t bid qty ethusdt: {bid_qty_ethusdt}')
            # logging.info(f'\t ask qty btcusdt: {ask_qty_btcusdt}')
    else:
        print("buscando profit izquierda ", profit)
    #     logging.warning(f'Izquierda -> cantidad_btc: {cant_btc} -> {profit:.4f} %')
    #   print(f'Izquierda -> ask_ethbtc: {ask_ethbtc} -> bid_ethusdt: {bid_ethusdt} -> ask_btcusdt: {ask_btcusdt} -> cantidad_btc: {cant_btc} -> {(cant_btc-1) * 100}%')

def task_criptopar(val: str):
    socket = f'wss://stream.binance.com:9443/ws/{val}@bookTicker'
    ws = websocket.WebSocketApp(socket,
                                on_message=on_message,
                                on_close=on_close,
                                )
    print(f"iniciando {val}")
    ws.run_forever(reconnect=5)  # Set dispatcher to automatic reconnection

def on_message(ws, message):
    data = json.loads(message)
    get_par_dict(data=data, dict_par=select_dict(data=data))
    
def on_close(ws, close_status_code, close_msg):
    print(f'{close_msg} -> {close_status_code}')

def select_dict(data: dict) -> dict:
    if data.get('s') == par_derecha:
        return dict_btcusdt
    elif data.get('s') == par_base:
        return dict_ethusdt
    elif data.get('s') == par_izquierda:
        return dict_ethbtc
    
def get_par_dict(data: dict, dict_par: dict):
    if dict_par.get('a') or dict_par.get('b'):
        item_a = dict_par.get('a')
        item_b = dict_par.get('b')
        if item_a != data.get("a") or item_b != data.get('b'):
            dict_par['a'] = data.get("a")
            dict_par['b'] = data.get("b")
            dict_par['A'] = data.get('A')
            dict_par['B'] = data.get('B')
            get_values_derecha(list_dicts=list_dicts)
            get_values_izquierda(list_dicts=list_dicts)
    else:
        dict_par['a'] = data.get('a')
        dict_par['b'] = data.get('b')
        dict_par['A'] = data.get('A')
        dict_par['B'] = data.get('B')


if __name__ == "__main__":
    # r = redis.Redis(host='127.0.0.1', port=6379, db=0)
    # create two new threads
    dict_btcusdt = {'a': None, 'b': None}
    dict_ethusdt = {'a': None, 'b': None}
    dict_ethbtc = {'a': None, 'b': None}
    list_dicts = [dict_btcusdt, dict_ethbtc, dict_ethusdt]

    # t1 = Thread(target=task_criptopar, args=['btcusdt', ])
    # t2 = Thread(target=task_criptopar, args=['ethusdt', ])
    # t3 = Thread(target=task_criptopar, args=['ethbtc', ])
    t1 = Thread(target=task_criptopar, args=[par_derecha.lower(), ])
    t2 = Thread(target=task_criptopar, args=[par_base.lower(), ])
    t3 = Thread(target=task_criptopar, args=[par_izquierda.lower(), ])

    t1.start()
    t2.start()
    t3.start()

    # wait for the threads to complete
    t1.join()
    t2.join()
    t3.join()

    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()

#"https://github.com/binance-us/binance-official-api-docs/blob/master/web-socket-streams.md"

