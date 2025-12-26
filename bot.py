# bot.py
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import telebot
import requests
from datetime import datetime, date
import threading
import time
import random

# تحميل متغيرات البيئة
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# إعداد logging
logger = logging.getLogger("fx_bot")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler = RotatingFileHandler("bot.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())

if not TOKEN:
    logger.critical("Missing TELEGRAM_BOT_TOKEN environment variable. Exiting.")
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

PAIRS = {
    'eurusd': 'EUR/USD', 'gbpusd': 'GBP/USD', 'usdjpy': 'USD/JPY',
    'audusd': 'AUD/USD', 'usdcad': 'USD/CAD', 'gold': 'XAU/USD'
}

analysis_subscribers = set()
_last_sent_date = None
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@your_admin_username")

@bot.message_handler(commands=['start'])
def start(message):
    welcome = f"""
🤖 *بوت تداول الفوركس الاحترافي*

📊 *الأقسام الرئيسية:*
🔹 `/trading` - قسم التداول العام
🔹 `/analysis` - تحليل الذهب والبيتكوين
🔹 `/news` - الأخبار الاقتصادية
🔹 `/support` - التواصل مع {ADMIN_USERNAME}

🚀 *اختر قسمك الآن*
    """
    bot.reply_to(message, welcome)

@bot.message_handler(commands=['analysis'])
def analysis_menu(message):
    text = """
📊 *قسم التحليل اليومي*

/daily_analysis - آخر تحليل الذهب والبيتكوين
/subscribe_analysis - اشتراك يومي تلقائي
/unsubscribe_analysis - إلغاء الاشتراك
/analysis_status - حالة اشتراكك

*التحليل يُرسل يومياً الساعة 8 صباحاً*
    """
    bot.reply_to(message, text)

@bot.message_handler(commands=['daily_analysis'])
def daily_analysis(message):
    gold_analysis = get_gold_analysis()
    btc_analysis = get_btc_analysis()
    analysis_text = f"""
📊 *التحليل اليومي - {datetime.now().strftime('%d/%m/%Y')}*

🪙 *تحليل الذهب (XAU/USD):*
{gold_analysis}

₿ *تحليل البيتكوين (BTC/USD):*
{btc_analysis}

⚠️ *تحليل تعليمي - لا يُعتبر توصية مالية*
    """
    if message is not None:
        bot.reply_to(message, analysis_text)
    return analysis_text

def get_gold_analysis():
    prices = get_gold_price()
    current_price = prices.get('current') if prices else 2650.50
    if current_price > 2650:
        direction = "🟢 صعودي"
        target = f"{current_price + 15:.1f}"
        support = f"{current_price - 10:.1f}"
    elif current_price < 2620:
        direction = "🔴 هبوطي"
        target = f"{current_price - 15:.1f}"
        support = f"{current_price + 10:.1f}"
    else:
        direction = "🟡 جانبي"
        target = f"{current_price + 8:.1f}"
        support = f"{current_price - 8:.1f}"
    return f"""
💰 السعر الحالي: `{current_price:.2f}$`
📈 الاتجاه: {direction}
🎯 الهدف: {target}$
🛡️ الدعم: {support}$
📝 *الملاحظات*: {random.choice(['قوة شرائية عالية', 'ضغط بيعي', 'انتظار اختراق', 'حركة جانبية'])}
    """

def get_btc_analysis():
    prices = get_btc_price()
    current_price = prices.get('current') if prices else 98000.0
    if current_price > 100000:
        direction = "🟢 صعودي قوي"
        target = f"{current_price * 1.05:.0f}"
        support = f"{current_price * 0.97:.0f}"
    elif current_price < 90000:
        direction = "🔴 هبوطي"
        target = f"{current_price * 0.95:.0f}"
        support = f"{current_price * 1.03:.0f}"
    else:
        direction = "🟡 تذبذب"
        target = f"{current_price * 1.03:.0f}"
        support = f"{current_price * 0.97:.0f}"
    return f"""
💰 السعر الحالي: `{current_price:.0f}$`
📈 الاتجاه: {direction}
🎯 الهدف: {target}$
🛡️ الدعم: {support}$
📝 *الملاحظات*: {random.choice(['ضغط شراء من المؤسسات', 'تصريحات رئيس فيدرالي', 'حركة توزيع', 'انتظار قرار ETF'])}
    """

def get_gold_price():
    try:
        resp = requests.get("https://api.metals.live/v1/spot/XAU", timeout=6)
        resp.raise_for_status()
        data = resp.json()
        price = None
        if isinstance(data, list) and data:
            item = data[0]
            price = item.get('price') or item.get('last') or item.get('ask') or item.get('value')
        elif isinstance(data, dict):
            price = data.get('price') or data.get('last') or data.get('ask') or data.get('value')
        if price is None:
            logger.debug("get_gold_price unexpected response %s", data)
            return None
        return {'current': float(price)}
    except Exception as e:
        logger.warning("get_gold_price failed: %s", e)
        return None

def get_btc_price():
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=6)
        resp.raise_for_status()
        data = resp.json()
        price = data.get('bitcoin', {}).get('usd')
        if price is None:
            logger.debug("get_btc_price unexpected response %s", data)
            return None
        return {'current': float(price)}
    except Exception as e:
        logger.warning("get_btc_price failed: %s", e)
        return None

@bot.message_handler(commands=['subscribe_analysis'])
def subscribe_analysis(message):
    user_id = message.from_user.id
    analysis_subscribers.add(user_id)
    logger.info("User %s subscribed", user_id)
    bot.reply_to(message, "📊 ✅ تم اشتراكك في التحليل اليومي للذهب والبيتكوين!\n🕐 يُرسل يومياً الساعة 8 صباحاً")

@bot.message_handler(commands=['unsubscribe_analysis'])
def unsubscribe_analysis(message):
    user_id = message.from_user.id
    analysis_subscribers.discard(user_id)
    logger.info("User %s unsubscribed", user_id)
    bot.reply_to(message, "📊 ❌ تم إلغاء اشتراكك من التحليل اليومي")

@bot.message_handler(commands=['analysis_status'])
def analysis_status(message):
    user_id = message.from_user.id
    status = "✅ مشترك" if user_id in analysis_subscribers else "❌ غير مشترك"
    bot.reply_to(message, f"حالة اشتراكك في التحليل اليومي: {status}")

@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            raise ValueError("missing pair")
        pair = parts[1].lower()
        if pair == 'gold':
            prices = get_gold_price()
            rate = prices['current'] if prices else 2650.0
            text = f"🪙 *XAU/USD*\n💰 `{rate:.2f}$`\n⏰ {datetime.now().strftime('%H:%M')}"
        else:
            pair_label = PAIRS.get(pair, pair).upper()
            text = f"💹 *{pair_label}*\n💰 `1.12345`\n⏰ {datetime.now().strftime('%H:%M')}"
        bot.reply_to(message, text)
    except Exception:
        bot.reply_to(message, "❌ استخدم: /price gold أو /price eurusd")

@bot.message_handler(commands=['support'])
def support(message):
    bot.reply_to(message, f"📞 *التواصل مع الإدارة*\n{ADMIN_USERNAME}\n\nأرسل رسالتك الآن وسيتم إرسالها للإدارة 👇")
    bot.register_next_step_handler(message, handle_support)

def handle_support(message):
    try:
        support_text = f"📩 *رسالة دعم جديدة*\n👤 {message.from_user.first_name}\n🆔 `{message.from_user.id}`\n📅 {datetime.now().strftime('%H:%M %d/%m')}\n💬 {message.text}"
        if ADMIN_ID:
            bot.send_message(ADMIN_ID, support_text)
            logger.info("Forwarded support from %s to admin %s", message.from_user.id, ADMIN_ID)
        else:
            bot.send_message(ADMIN_USERNAME, support_text)
        bot.reply_to(message, "✅ تم إرسال رسالتك للإدارة!")
    except Exception as e:
        logger.error("handle_support failed: %s", e)
        bot.reply_to(message, "❌ خطأ في الإرسال")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "🤖 *الأوامر المتاحة:*\n/start\n/analysis\n/price gold\n/daily_analysis\n/subscribe_analysis\n/support")

def send_to_user(user_id, text):
    try:
        bot.send_message(user_id, text)
        logger.info("Sent message to %s", user_id)
    except Exception as e:
        logger.warning("Failed to send message to %s: %s", user_id, e)

def send_daily_analysis():
    global _last_sent_date
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            today = date.today()
            if _last_sent_date != today and analysis_subscribers:
                logger.info("Sending daily analysis to %d subscribers", len(analysis_subscribers))
                analysis_text = daily_analysis(None)
                for user_id in list(analysis_subscribers):
                    send_to_user(user_id, analysis_text)
                _last_sent_date = today
            time.sleep(70)
        else:
            time.sleep(10)

threading.Thread(target=send_daily_analysis, daemon=True).start()

if __name__ == "__main__":
    logger.info("Bot is starting")
    try:
        bot.infinity_polling()
    except AttributeError:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.exception("Polling stopped unexpectedly: %s", e)