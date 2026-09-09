import asyncio
import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiohttp import web  # اضافه شده برای حل مشکل پورت Render

BOT_TOKEN = "8095497755:AAGbvTc4bjFBdjvpbgskMSOgboxdQtSNvGU"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(F.video | F.document)
async def handle_video(message: Message):
    status_msg = await message.reply("در حال دانلود و فشرده‌سازی ویدیو...")
    
    file_id = message.video.file_id if message.video else message.document.file_id
    file_info = await bot.get_file(file_id)
    input_path = f"input_{message.from_user.id}.mp4"
    output_path = f"compressed_{message.from_user.id}.mp4"
    
    try:
        await bot.download_file(file_info.file_path, input_path)
        cmd = f'ffmpeg -y -i "{input_path}" -vcodec libx264 -crf 28 "{output_path}"'
        subprocess.run(cmd, shell=True, check=True)
        
        with open(output_path, "rb") as video_file:
            await message.reply_video(video=video_file, caption="ویدیو با موفقیت فشرده شد!")
            
    except Exception as e:
        await message.reply(f"خطا در پردازش ویدیو: {str(e)}")
        
    finally:
        await status_msg.delete()
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

# کدهای مربوط به گول زدن رندر جهت باز کردن پورت
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await start_dummy_server()  # اجرای پورت فرضی
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
