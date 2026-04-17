#!/usr/bin/env python3
"""
Finam bot - автоматический встречный ордер при сделке
Токен: FINAM_TOKEN=т TOKEN python bot.py
"""
import os
import asyncio
from datetime import datetime
from threading import Thread
import time
import sys

from FinamPy import FinamPy
import FinamPy.grpc.side_pb2 as side
from finam_trade_api import Client, TokenManager
from google.type.decimal_pb2 import Decimal

from config import ACCOUNT_ID, INSTRUMENTS

TOKEN = os.environ.get('FINAM_TOKEN', '')
if not TOKEN:
    print("Ошибка: нужен FINAM_TOKEN")
    print("FINAM_TOKEN=токен python bot.py")
    sys.exit(1)

SYMBOL = list(INSTRUMENTS.keys())[0]
PRICE_DELTA = INSTRUMENTS[SYMBOL]

SEEN_TRADES = set()
trade_client = None


async def get_trade_client():
    global trade_client
    if not trade_client:
        trade_client = Client(TokenManager(TOKEN))
        await trade_client.access_tokens.set_jwt_token()
    return trade_client


async def place_order_async(qty, side_name, price):
    c = await get_trade_client()
    try:
        from finam_trade_api.order import Order, OrderType, TimeInForce
        from finam_trade_api.base_client.models import FinamDecimal, Side
        
        order = Order(
            account_id=ACCOUNT_ID,
            symbol=SYMBOL,
            quantity=FinamDecimal(value=str(qty)),
            side=Side.BUY if side_name == 'BUY' else Side.SELL,
            type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            limit_price=FinamDecimal(value=str(price)),
        )
        result = await c.orders.place_order(order)
        print(f"  => Ордер создан: {result}")
        return result
    except Exception as e:
        print(f"  => Ошибка: {e}")
        return None


def on_trade(trade):
    trade_time = trade.timestamp.seconds if trade.timestamp else 0
    current_time = int(time.time())
    if current_time - trade_time > 10:
        return
    
    trade_id = trade.trade_id
    if not trade_id or trade_id == "0" or trade_id in SEEN_TRADES:
        return
    
    SEEN_TRADES.add(trade_id)
    if len(SEEN_TRADES) > 100:
        SEEN_TRADES.clear()
    
    price = float(trade.price.value)
    qty = float(trade.size.value) if trade.size else 1.0
    
    trade_side = trade.side
    side_name = "BUY" if trade_side == 1 else "SELL" if trade_side == 2 else str(trade_side)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Сделка: {side_name} {int(qty)} @ {price}")
    
    if price and qty:
        counter_price = round(price + PRICE_DELTA, 3) if trade_side == 1 else round(price - PRICE_DELTA, 3)
        counter_side = "SELL" if trade_side == 1 else "BUY"
        
        print(f"  => Выставляю {counter_side} {int(qty)} @ {counter_price}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(place_order_async(int(qty), counter_side, counter_price))
        finally:
            loop.close()


def on_order(order):
    print(f"DEBUG: Заявка: {order.order_id}, status={order.status}")


def main():
    fp_provider = FinamPy(TOKEN)
    
    print(f"=== Finam Bot ===")
    print(f"Мониторим: {SYMBOL}")
    print(f"Отступ: {PRICE_DELTA}")
    
    fp_provider.on_trade.subscribe(on_trade)
    fp_provider.on_order.subscribe(on_order)
    Thread(target=fp_provider.subscribe_trades_thread).start()
    Thread(target=fp_provider.subscribe_orders_thread).start()
    
    print("Бот запущен. Ожидание сделок...")
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        fp_provider.close_channel()


if __name__ == '__main__':
    main()