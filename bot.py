#!/usr/bin/env python3
"""
Finam bot - автоматический встречный ордер при сделке
Токен: FINAM_TOKEN=тOKEN python bot.py
"""
import os
import asyncio
import json
import aiohttp
from datetime import datetime

from config import ACCOUNT_ID, INSTRUMENTS

FINAM_TOKEN = os.environ.get('FINAM_TOKEN', '')
if not FINAM_TOKEN:
    print("Ошибка: нужен FINAM_TOKEN")
    print("FINAM_TOKEN=токен python bot.py")
    exit(1)

WS_URL = "wss://api.finam.ru/trading"
TOKEN_URL = "https://api.finam.ru/v1/auth/token"

SEEN_TRADES = set()


async def get_jwt_token(session, secret_token):
    async with session.post(TOKEN_URL, json={"secretToken": secret_token}) as resp:
        data = await resp.json()
        return data.get("token", "")


async def create_order(session, token, symbol, direction, quantity, price, account_id):
    url = f"https://api.finam.ru/v1/orders/{account_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    order_data = {
        "symbol": symbol,
        "direction": direction,
        "quantity": quantity,
        "price": price,
        "orderType": "limit",
        "timeInForce": "day"
    }
    
    async with session.post(url, json=order_data, headers=headers) as resp:
        return await resp.json()


def process_trade(order, symbol, price_delta, session, jwt_token):
    direction = order.get("direction", 0)
    trades = order.get("trades", [])
    if not trades:
        return
    
    for trade in trades:
        trade_id = str(trade.get("tradeId", ""))
        if not trade_id or trade_id in SEEN_TRADES:
            continue
        
        SEEN_TRADES.add(trade_id)
        if len(SEEN_TRADES) > 100:
            SEEN_TRADES.clear()
        
        price = float(trade.get("price", 0))
        quantity = int(trade.get("quantity", 0))
        
        counter_direction = 2 if direction == 1 else 1
        counter_price = round(price + price_delta, 3) if direction == 1 else round(price - price_delta, 3)
        
        action = "BUY" if counter_direction == 1 else "SELL"
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Сделка: {action} {quantity} @ {price}")
        print(f"  => Выставляю {'SELL' if direction == 1 else 'BUY'} {quantity} @ {counter_price}")
        
        asyncio.create_task(create_order(
            session, jwt_token, symbol, counter_direction,
            quantity, counter_price, ACCOUNT_ID
        ))


async def main():
    print("=== Finam Bot ===")
    print(f"Мониторим: {list(INSTRUMENTS.keys())}")
    
    async with aiohttp.ClientSession() as session:
        print("Получение токена...")
        jwt_token = await get_jwt_token(session, FINAM_TOKEN)
        print("Токен получен")
        
        ws = await session.ws_connect(WS_URL)
        
        symbol = list(INSTRUMENTS.keys())[0]
        price_delta = INSTRUMENTS[symbol]
        
        subscribe_msg = {
            "action": "SUBSCRIBE",
            "type": "ORDERS",
            "token": jwt_token,
            "data": {"symbols": [symbol]}
        }
        await ws.send_json(subscribe_msg)
        
        print("Бот запущен. Ожидание сделок...")
        
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")
                    
                    if msg_type == "SUBSCRIPTION":
                        print(f"Подписка: {data}")
                    elif msg_type == "DATA":
                        payload = data.get("payload", {})
                        orders = payload.get("orders", [])
                        for order in orders:
                            if order.get("symbol") == symbol:
                                process_trade(order, symbol, price_delta, session, jwt_token)
                    elif msg_type == "PING":
                        pass
                    elif msg_type == "ERROR":
                        print(f"Ошибка: {data}")
                except Exception as e:
                    print(f"Ошибка: {e}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("WebSocket ошибка")
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                print("WebSocket закрыт")
                break


if __name__ == "__main__":
    asyncio.run(main())