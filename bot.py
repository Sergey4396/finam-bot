#!/usr/bin/env python3
"""
Finam bot - автоматический встречный ордер при сделке
Токен: FINAM_TOKEN=тOKEN python bot.py
"""
import os
import asyncio
import time
from threading import Thread

from config import ACCOUNT_ID, INSTRUMENTS
from finam_trade_api import Client, TokenManager
from FinamPy import FinamPy
import FinamPy.grpc.side_pb2 as side

FINAM_TOKEN = os.environ.get('FINAM_TOKEN', '')
if not FINAM_TOKEN:
    print("Ошибка: нужен FINAM_TOKEN")
    print("FINAM_TOKEN=токен python bot.py")
    exit(1)

SEEN_TRADES = set()


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
    
    print(f"[Сделка] {side_name} {int(qty)} @ {price}")
    
    if price and qty and trade_side in [1, 2]:
        from config import INSTRUMENTS
        SYMBOL = list(INSTRUMENTS.keys())[0]
        PRICE_DELTA = INSTRUMENTS[SYMBOL]
        
        counter_price = round(price + PRICE_DELTA, 3) if trade_side == 1 else round(price - PRICE_DELTA, 3)
        counter_side = "SELL" if trade_side == 1 else "BUY"
        
        print(f"  => Выставляю {counter_side} {int(qty)} @ {counter_price}")
        
        from threading import Thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def place_order():
            try:
                client = Client(TokenManager(FINAM_TOKEN))
                await client.access_tokens.set_jwt_token()
                
                from finam_trade_api.order import Order, OrderType, TimeInForce
                from finam_trade_api.base_client.models import FinamDecimal, Side
                
                order = Order(
                    account_id=ACCOUNT_ID,
                    symbol=SYMBOL,
                    quantity=FinamDecimal(value=str(int(qty))),
                    side=Side.BUY if counter_side == 'BUY' else Side.SELL,
                    type=OrderType.LIMIT,
                    time_in_force=TimeInForce.DAY,
                    limit_price=FinamDecimal(value=str(counter_price)),
                )
                result = await client.orders.place_order(order)
                print(f"  => Ордер: {result}")
            except Exception as e:
                print(f"  => Ошибка: {e}")
        
        try:
            loop.run_until_complete(place_order())
        finally:
            loop.close()


def on_order(order):
    print(f"[Заявка] {order.order_id} status={order.status}")


def main():
    fp_provider = FinamPy(FINAM_TOKEN)
    
    print("=== Finam Bot ===")
    print(f"Мониторим: {list(INSTRUMENTS.keys())}")
    
    fp_provider.on_trade.subscribe(on_trade)
    fp_provider.on_order.subscribe(on_order)
    Thread(target=fp_provider.subscribe_trades_thread).start()
    Thread(target=fp_provider.subscribe_orders_thread).start()
    
    print("Бот запущен. Ожидание сделок...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        fp_provider.close_channel()


if __name__ == "__main__":
    main()