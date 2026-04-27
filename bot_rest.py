#!/usr/bin/env python3
"""
Finam Bot - REST API версия
Токен: FINAM_TOKEN=тOKEN python bot.py
Символ: NRJ6@RTSX (газ)
"""
import os
import asyncio
import aiohttp
import json
from datetime import datetime

FINAM_TOKEN = os.environ.get('FINAM_TOKEN', '')
if not FINAM_TOKEN:
    print("Ошибка: нужен FINAM_TOKEN")
    exit(1)

ACCOUNT_ID = "2038952"
SYMBOL = "NRJ6@RTSX"
PRICE_DELTA = 0.020

AUTH_URL = "https://api.finam.ru/v1/token"
ORDERS_URL = f"https://api.finam.ru/v1/orders/{ACCOUNT_ID}"
WS_URL = "wss://api.finam.ru/tradinginfo"

SEEN = set()


async def get_jwt(session, secret):
    async with session.post(AUTH_URL, json={"secretToken": secret}) as resp:
        data = await resp.json()
        return data.get("token", "")


async def place_order(session, token, sym, side, qty, price):
    headers = {"Authorization": f"Bearer {token}"}
    # side: 1=BUY, 2=SELL
    body = {
        "symbol": sym,
        "direction": side,
        "quantity": qty,
        "price": price,
        "orderType": "limit",
        "timeInForce": "day"
    }
    async with session.post(ORDERS_URL, json=body, headers=headers) as resp:
        return await resp.json()


async def main():
    print("=== Finam Bot (REST) ===")
    print(f"Символ: {SYMBOL}")
    
    async with aiohttp.ClientSession() as session:
        print("Получаю токен...")
        jwt = await get_jwt(session, FINAM_TOKEN)
        print("Токен получен")
        
        # WebSocket подписка
        ws = await session.ws_connect(WS_URL)
        
        sub = {
            "action": "SUBSCRIBE",
            "type": "ORDERS",
            "token": jwt,
            "data": {"symbols": [SYMBOL]}
        }
        await ws.send_json(sub)
        print("Подписка отправлена. Жду сделок...")
        
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if data.get("type") == "DATA":
                        orders = data.get("payload", {}).get("orders", [])
                        for o in orders:
                            if o.get("symbol") != SYMBOL:
                                continue
                            
                            trades = o.get("trades", [])
                            for t in trades:
                                tid = str(t.get("tradeId", ""))
                                if tid in SEEN or not tid or tid == "0":
                                    continue
                                SEEN.add(tid)
                                if len(SEEN) > 100:
                                    SEEN.clear()
                                
                                price = float(t.get("price", 0))
                                qty = int(t.get("quantity", 0))
                                direction = o.get("direction", 0)  # 1=BUY, 2=SELL from ORDER
                                
                                if not price or not qty:
                                    continue
                                
                                side_name = "BUY" if direction == 1 else "SELL" if direction == 2 else str(direction)
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Сделка: {side_name} {qty} @ {price}")
                                
                                # Противоположное направление
                                new_dir = 2 if direction == 1 else 1
                                new_price = round(price + PRICE_DELTA, 3) if direction == 1 else round(price - PRICE_DELTA, 3)
                                new_side = "SELL" if direction == 1 else "BUY"
                                
                                print(f"  => Ставлю {new_side} {qty} @ {new_price}")
                                result = await place_order(session, jwt, SYMBOL, new_dir, qty, new_price)
                                print(f"  => Результат: {result}")
                except Exception as e:
                    print(f"Ошибка: {e}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("WS ошибка")
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                print("WS закрыт")
                break


if __name__ == "__main__":
    asyncio.run(main())