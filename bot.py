"""
Finam bot - автоматический встречный ордер при сделке
"""
import asyncio
import json
import aiohttp
from config import FINAM_SECRET_TOKEN, ACCOUNT_ID, INSTRUMENTS

WS_URL = "wss://api.finam.ru/trading"
TOKEN_URL = "https://api.finam.ru/v1/auth/token"
REFRESH_URL = "https://api.finam.ru/v1/auth/refresh"


async def get_jwt_token(session, secret_token):
    """Получение JWT токена"""
    async with session.post(TOKEN_URL, json={"secretToken": secret_token}) as resp:
        data = await resp.json()
        return data.get("token", "")


async def refresh_token(session, secret_token):
    """Обновление JWT токена"""
    async with session.post(REFRESH_URL, json={"secretToken": secret_token}) as resp:
        data = await resp.json()
        return data.get("token", "")


async def create_order(session, token, symbol, direction, quantity, price, account_id):
    """Создание ордера"""
    url = f"https://api.finam.ru/v1/orders/{account_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    order_data = {
        "symbol": symbol,
        "direction": direction,  # 1 = buy, 2 = sell
        "quantity": quantity,
        "price": price,
        "orderType": "limit",
        "timeInForce": "day"
    }
    
    async with session.post(url, json=order_data, headers=headers) as resp:
        return await resp.json()


async def on_trade(order, symbol, price_delta, session, jwt_token):
    """Обработка сделки"""
    direction = order.get("direction", 0)
    is_buy = direction == 1
    
    trades = order.get("trades", [])
    if not trades:
        return
    
    # Противоположное направление
    counter_direction = 2 if is_buy else 1  # 1=buy, 2=sell
    price_delta_dir = -price_delta if is_buy else price_delta
    
    for trade in trades:
        price = float(trade.get("price", 0))
        quantity = int(trade.get("quantity", 0))
        
        counter_price = round(price + price_delta_dir, 3)
        action = "ПОКУПКУ" if counter_direction == 1 else "ПРОДАЖУ"
        
        print(f"  => Сделка: {symbol} {quantity} @ {price}")
        print(f"  => Ордер на {action}: {quantity} @ {counter_price}")
        
        try:
            result = await create_order(
                session, jwt_token, 
                symbol, counter_direction, 
                quantity, counter_price, 
                ACCOUNT_ID
            )
            print(f"  => Ордер создан: {result}")
        except Exception as e:
            print(f"  => Ошибка: {e}")


async def process_message(msg, session, jwt_token):
    """Обработка сообщения от WebSocket"""
    msg_type = msg.get("type")
    
    if msg_type == "SUBSCRIPTION":
        print(f"Подписка: {msg.get('subscription_key')}")
    
    elif msg_type == "DATA":
        payload = msg.get("payload", {})
        orders = payload.get("orders", [])
        
        for order in orders:
            symbol = order.get("symbol", "")
            if symbol not in INSTRUMENTS:
                continue
            
            await on_trade(order, symbol, INSTRUMENTS[symbol], session, jwt_token)
    
    elif msg_type == "PING":
        print(f"Ping")
    
    elif msg_type == "ERROR":
        print(f"Ошибка: {msg}")


async def main():
    print("=== Finam Bot ===")
    print(f"Мониторим: {list(INSTRUMENTS.keys())}")
    
    session = aiohttp.ClientSession()
    
    print("Получение токена...")
    jwt_token = await get_jwt_token(session, FINAM_SECRET_TOKEN)
    print("Токен получен")
    
    print("Подключение к WebSocket...")
    
    ws = await session.ws_connect(WS_URL)
    
    # Подписка на ордера
    subscribe_msg = {
        "action": "SUBSCRIBE",
        "type": "ORDERS",
        "token": jwt_token,
        "data": {
            "symbols": list(INSTRUMENTS.keys())
        }
    }
    
    await ws.send_json(subscribe_msg)
    
    print("Бот запущен. Ожидание сделок...")
    
    # Обработка сообщений
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
                await process_message(data, session, jwt_token)
            except Exception as e:
                print(f"Ошибка обработки: {e}")
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print(f"WebSocket ошибка")
            break
        elif msg.type == aiohttp.WSMsgType.CLOSED:
            print("WebSocket закрыт")
            break
    
    await session.close()


if __name__ == "__main__":
    asyncio.run(main())