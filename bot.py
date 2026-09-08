import asyncio
import os
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

API_TOKEN = '8967480237:AAG5vHg04VHi_ybk3ztSzZ5lvwTkCl9Eg-Q'  # توکن اصلی ربات خود را اینجا بگذارید

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ساخت و اتصال به دیتابیس
conn = sqlite3.connect('trade_game.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        cash INTEGER DEFAULT 50000,
        crypto INTEGER DEFAULT 0,
        gold INTEGER DEFAULT 0
    )
''')
conn.commit()

market_prices = {
    "crypto": 10000,
    "gold": 25000
}

def update_market():
    market_prices["crypto"] = max(2000, market_prices["crypto"] + random.randint(-1500, 2000))
    market_prices["gold"] = max(5000, market_prices["gold"] + random.randint(-3000, 3500))

def get_player(user_id):
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    player = cursor.fetchone()
    if not player:
        cursor.execute('INSERT INTO players (user_id) VALUES (?)', (user_id,))
        conn.commit()
        return (user_id, 50000, 0, 0)
    return player

def group_game_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💼 کیف پول من", callback_data="profile"),
        InlineKeyboardButton("📈 بازار سیاه", callback_data="market"),
        InlineKeyboardButton("🎰 دزدی و ریسک", callback_data="rob")
    )
    return kb

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    get_player(user_id)
    
    if message.chat.type == types.ChatType.PRIVATE:
        me = await bot.get_me()
        text = (
            f"👋 **سلام به ربات بازی بازار سیاه خوش آمدی!**\n\n"
            f"📖 **راهنمای بازی:**\n"
            f"این یک بازی گروهی رقابتی است. شما می‌توانید ربات را به گروه‌های خود اضافه کنید و با بقیه اعضا به تجارت، خرید و فروش ارز و دزدی بپردازید.\n\n"
            f"🌐 **ویژگی مهم:** تمام دارایی‌ها و سکه‌های شما بین تمام گروه‌ها مشترک و یکسان است!"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("➕ افزودن ربات به گروه", url=f"https://t.me/{me.username}?startgroup=true"))
        await message.reply(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.reply("💵 **بازی بازار سیاه در این گروه فعال است!**\nاز دکمه‌های زیر برای بازی استفاده کنید:", reply_markup=group_game_keyboard(), parse_mode="Markdown")

@dp.callback_query_handler(lambda c: True)
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    _, cash, crypto, gold = get_player(user_id)

    if data == "profile":
        text = (
            f"👤 **دارایی‌های کاربر {callback_query.from_user.first_name}:**\n\n"
            f"💰 پول نقد: {cash:,} تومان\n"
            f"🪙 ارز دیجیتال: {crypto} واحد\n"
            f"🥇 شمش طلا: {gold} عدد"
        )
        await callback_query.answer()
        await bot.send_message(callback_query.message.chat.id, text, parse_mode="Markdown")

    elif data == "market":
        update_market()
        text = (
            f"📈 **قیمت‌های لحظه‌ای بازار:**\n\n"
            f"🪙 ارز دیجیتال: {market_prices['crypto']:,} تومان\n"
            f"🥇 شمش طلا: {market_prices['gold']:,} تومان\n\n"
            f"💰 پول شما: {cash:,} تومان"
        )
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("خرید ۱ ارز 🪙", callback_data="buy_crypto"),
            InlineKeyboardButton("فروش ۱ ارز 🪙", callback_data="sell_crypto"),
            InlineKeyboardButton("خرید ۱ طلا 🥇", callback_data="buy_gold"),
            InlineKeyboardButton("فروش ۱ طلا 🥇", callback_data="sell_gold")
        )
        await callback_query.answer()
        await bot.send_message(callback_query.message.chat.id, text, reply_markup=kb, parse_mode="Markdown")

    elif data == "buy_crypto":
        price = market_prices["crypto"]
        if cash >= price:
            cursor.execute('UPDATE players SET cash = cash - ?, crypto = crypto + 1 WHERE user_id = ?', (price, user_id))
            conn.commit()
            await callback_query.answer("✅ ۱ واحد ارز خریدی!", show_alert=True)
        else:
            await callback_query.answer("❌ پولت کافی نیست!", show_alert=True)

    elif data == "sell_crypto":
        price = market_prices["crypto"]
        if crypto >= 1:
            cursor.execute('UPDATE players SET cash = cash + ?, crypto = crypto - 1 WHERE user_id = ?', (price, user_id))
            conn.commit()
            await callback_query.answer("✅ ۱ واحد ارز فروختی!", show_alert=True)
        else:
            await callback_query.answer("❌ ارز دیجیتال نداری!", show_alert=True)

    elif data == "rob":
        if random.random() < 0.5:
            win = random.randint(5000, 25000)
            cursor.execute('UPDATE players SET cash = cash + ? WHERE user_id = ?', (win, user_id))
            conn.commit()
            await callback_query.answer(f"🔥 موفق شدی! {win:,} تومان دزدیدی!", show_alert=True)
        else:
            fine = min(cash, 10000)
            cursor.execute('UPDATE players SET cash = cash - ? WHERE user_id = ?', (fine, user_id))
            conn.commit()
            await callback_query.answer(f"🚔 پلیس دستگیرت کرد! {fine:,} جریمه شدی.", show_alert=True)

# وب‌سرور داخلی جهت پاس کردن Port Scan در Render
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    executor.start_polling(dp, skip_updates=True, loop=loop)
