# Finam Bot

Бот для автоматических встречных ордеров на Finam.

## Установка

```bash
cd finam-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Настройка

Отредактируй `config.py`:

```python
FINAM_SECRET_TOKEN = "твой_токен"  # Сгенерировать на finam.ru
ACCOUNT_ID = "KЛФ-XXXXXXXX"
```

## Запуск

```bash
source venv/bin/activate
python bot.py
```

## Символы фьючерсов FORTS

- NGM6@FORTS - Нефть Brent (NRJ6)
- BRK6@FORTS - Нефть Brent
- SiK6@FORTS - Доллар-рубль