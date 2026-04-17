"""
Finam bot configuration
"""

FINAM_SECRET_TOKEN = "YOUR_SECRET_TOKEN"  # Сгенерировать на портале finam.ru

ACCOUNT_ID = "YOUR_ACCOUNT_ID"  # Счёт в формате КЛФ-XXXXXXXX

# Отслеживаемые инструменты
# Для фьючерсов формат: code + month + year
# Пример: NRJ6 -> NRM (месяц: 6=июнь)
INSTRUMENTS = {
    "NGM6@FORTS": 0.022,  # NRJ6 - фьючерс на нефть Brent
}