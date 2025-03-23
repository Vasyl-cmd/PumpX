import ccxt
import time
import logging
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

# Настройки логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Подключение к Bybit без API-ключей
bybit = ccxt.bybit({'options': {'defaultType': 'future'}})

# Телеграм API
TELEGRAM_BOT_TOKEN = "7913216420:AAHvkdJB9Gx7wktl5DFkGrvvlhBsz8rdTNU"
TELEGRAM_CHAT_ID = "359242722"

# Настройки бота
timeframe_minutes = 20  # Время в минутах
percent_threshold = 5  # Процент пампа/дампа

# Хранение количества сигналов за 24 часа
signal_counts = {}
last_reset_time = datetime.now(timezone.utc)  # Исправленный код

def send_telegram_message(message):
    """Отправка сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            logging.info("✅ Уведомление отправлено в Telegram")
        else:
            logging.error(f"❌ Ошибка Telegram: {response.text}")
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке в Telegram: {e}")

# Отправка сообщения при запуске с настройками бота
startup_message = (
    f"🚀 Бот запущен и отслеживает пампы/дампы!\n"
    f"⏱️ Время: {timeframe_minutes} минут\n"
    f"📊 Процент: {percent_threshold}%"
)
send_telegram_message(startup_message)

# Функция получения списка фьючерсных пар с Bybit
def get_futures_symbols():
    all_coins = []

    try:
        bybit_markets = bybit.load_markets()

        bybit_coins = [
            (symbol.replace('/', '').split(':')[0], 'Bybit')  # Убираем слэш и всё после двоеточия
            for symbol, data in bybit_markets.items()
            if symbol.endswith('USDT')  
            and data.get('active', False)  
            and 'swap' in data.get('type', '')  
        ]

        logging.info(f"✅ Найдено {len(bybit_coins)} фьючерсных пар с Bybit.")
        all_coins.extend(bybit_coins)
    except Exception as e:
        logging.error(f"❌ Ошибка при загрузке Bybit: {e}")

    return all_coins

# Функция анализа пампа/дампа
def check_pump_dump(symbol, exchange_name):
    global last_reset_time, signal_counts

    try:
        # Сброс счетчика сигналов каждые 24 часа
        if datetime.now(timezone.utc) - last_reset_time > timedelta(hours=24):  # Исправленный код
            signal_counts.clear()
            last_reset_time = datetime.now(timezone.utc)  # Исправленный код
            logging.info("🔄 Сброс счетчика сигналов за 24 часа.")

        ohlcv = bybit.fetch_ohlcv(symbol, timeframe='1m', limit=21)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        if len(df) < 21:
            logging.warning(f"⚠️ Недостаточно данных для {symbol} ({exchange_name})")
            return

        first_price = df.iloc[-21]['close']
        last_price = df.iloc[-1]['close']
        percent_change = ((last_price - first_price) / first_price) * 100

        logging.info(f"📊 {symbol} ({exchange_name}): {percent_change:.2f}% за {timeframe_minutes} минут")

        # Увеличение счетчика сигналов для монеты
        signal_counts[symbol] = signal_counts.get(symbol, 0) + 1

        # Формируем ссылку на CoinGlass
        coinglass_url = f"https://www.coinglass.com/tv/Bybit_{symbol.replace('USDT', 'USDT')}"

        if percent_change >= percent_threshold:
            message = (
                f"🚀 <b><a href='{coinglass_url}'>{symbol} ({exchange_name})</a></b> <b>Памп: {percent_change:.2f}%</b>\n"
                f"🕒 {timeframe_minutes} минут ( {first_price:.4f} → {last_price:.4f} )\n"
                f"📢 Signal 24h: {signal_counts[symbol]}"
            )
            send_telegram_message(message)
        elif percent_change <= -percent_threshold:
            message = (
                f"🔻 <b><a href='{coinglass_url}'>{symbol} ({exchange_name})</a></b> <b>Дамп: {percent_change:.2f}%</b>\n"
 f"🕒 {timeframe_minutes} минут ( {first_price:.4f} → {last_price:.4f} )\n"
                f"📢 Signal 24h: {signal_counts[symbol]}"
            )
            send_telegram_message(message)

    except Exception as e:
        logging.error(f"❌ Ошибка при анализе {symbol} ({exchange_name}): {e}")

# Запуск цикла проверки
try:
    while True:
        futures_pairs = get_futures_symbols()
        logging.info(f"📢 Отслеживаем {len(futures_pairs)} пар")

        for symbol, exchange_name in futures_pairs:
            check_pump_dump(symbol, exchange_name)

        time.sleep(60)  # Пауза в 60 секунд

except KeyboardInterrupt:
    logging.info("❌ Бот остановлен пользователем.")
    send_telegram_message("❌ Бот был остановлен пользователем.")  # Оповещение о завершении работы бота

except Exception as e:
    logging.error(f"❌ Ошибка в основном цикле: {e}")
    send_telegram_message(f"❌ Ошибка в основном цикле: {e}")  # Оповещение о возникшей ошибке