import ccxt
import time
import logging
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# Настройки логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Подключение к Bybit без API-ключей
bybit = ccxt.bybit({'options': {'defaultType': 'future'}})

# Телеграм API
TELEGRAM_BOT_TOKEN = "ТВОЙ_ТОКЕН"
TELEGRAM_CHAT_ID = "ТВОЙ_ЧАТ_ID"

# Настройки бота
timeframe_minutes = 20  # Время анализа (в минутах)
percent_threshold = 2  # Процент изменения цены для сигнала
pump_block_time = timedelta(minutes=15)  # Блокировка повторных сигналов

# Хранение времени последнего пампа/дампа по каждой монете
last_signal_time = {}

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

# Отправка сообщения при запуске
startup_message = (
    f"🚀 Бот запущен и отслеживает пампы/дампы!\n"
    f"⏱️ Время анализа: {timeframe_minutes} минут\n"
    f"📊 Процент изменения: {percent_threshold}%"
)
send_telegram_message(startup_message)

def get_futures_symbols():
    """Получение списка фьючерсных пар с Bybit"""
    all_coins = []

    try:
        bybit_markets = bybit.load_markets()

        bybit_coins = [
            (symbol.replace('/', '').split(':')[0], 'Bybit')  
            for symbol, data in bybit_markets.items()
            if symbol.endswith('USDT') and data.get('active', False) and 'swap' in data.get('type', '')  
        ]

        logging.info(f"✅ Найдено {len(bybit_coins)} фьючерсных пар с Bybit.")
        all_coins.extend(bybit_coins)
    except Exception as e:
        logging.error(f"❌ Ошибка при загрузке Bybit: {e}")

    return all_coins

def check_pump_dump(symbol, exchange_name):
    """Анализ пампа/дампа"""
    try:
        now = datetime.now(timezone.utc)
        ohlcv = bybit.fetch_ohlcv(symbol, timeframe='1m', limit=21)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        if len(df) < 21:
            logging.warning(f"⚠️ Недостаточно данных для {symbol} ({exchange_name})")
            return

        first_price = df.iloc[-21]['close']
        last_price = df.iloc[-1]['close']
        percent_change = ((last_price - first_price) / first_price) * 100

        # Рассчитываем объем за последние 20 минут
        volume_first = df.iloc[-21:-1]['volume'].sum()
        volume_last = df.iloc[-20:]['volume'].sum()

        if volume_first == 0:
            volume_ratio = 0  # Избегаем деления на ноль
        else:
            volume_ratio = volume_last / volume_first

        logging.info(f"📊 {symbol} ({exchange_name}): {percent_change:.2f}% за {timeframe_minutes} минут")
        logging.info(f"📊 {symbol} ({exchange_name}): объем вырос в {volume_ratio:.2f} раз за последние 20 минут")

        # Проверка блокировки на повторный сигнал
        if symbol in last_signal_time and now - last_signal_time[symbol] < pump_block_time:
            logging.info(f"⏳ Пропускаем {symbol} (ещё не прошло 15 минут с последнего сигнала)")
            return  

        # Фиксируем новое время сигнала
        last_signal_time[symbol] = now  

        # Формируем ссылку на CoinGlass
        coinglass_url = f"https://www.coinglass.com/tv/Bybit_{symbol.replace('USDT', 'USDT')}"

        # Форматируем цены
        first_price_formatted = f"{first_price:.6f}".rstrip('0').rstrip('.')
        last_price_formatted = f"{last_price:.6f}".rstrip('0').rstrip('.')

        # Оповещения при достижении порога изменения цены
        if percent_change >= percent_threshold:
            message = (
                f"🚀 <b><a href='{coinglass_url}'>{symbol} ({exchange_name})</a></b> <b>Памп: {percent_change:.2f}%</b>\n"
                f"🕒 {timeframe_minutes} минут ( {first_price_formatted} → {last_price_formatted} )\n"
                f"📊 Объем вырос в {volume_ratio:.2f} раз"
            )
            send_telegram_message(message)

        elif percent_change <= -percent_threshold:
            message = (
                f"🔻 <b><a href='{coinglass_url}'>{symbol} ({exchange_name})</a></b> <b>Дамп: {percent_change:.2f}%</b>\n"
                f"🕒 {timeframe_minutes} минут ( {first_price_formatted} → {last_price_formatted} )\n"
                f"📊 Объем вырос в {volume_ratio:.2f} раз"
            )
            send_telegram_message(message)

    except Exception as e:
        logging.error(f"❌ Ошибка при анализе {symbol} ({exchange_name}): {e}")

# Запуск основного цикла
try:
    while True:
        now = datetime.now(timezone.utc)

        futures_pairs = get_futures_symbols()
        logging.info(f"📢 Отслеживаем {len(futures_pairs)} пар")

        for symbol, exchange_name in futures_pairs:
            check_pump_dump(symbol, exchange_name)

        time.sleep(60)  # Пауза в 60 секунд

except KeyboardInterrupt:
    logging.info("❌ Бот остановлен пользователем.")
    send_telegram_message("❌ Бот был остановлен пользователем.")

except Exception as e:
    logging.error(f"❌ Ошибка в основном цикле: {e}")
    send_telegram_message(f"❌ Ошибка в основном цикле: {e}")