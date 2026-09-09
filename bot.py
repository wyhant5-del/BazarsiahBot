import asyncio
import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# توکن به صورت مستقیم و بدون os.environ.get قرار داده شد
BOT_TOKEN = "8095497755:AAGbvTc4bjFBdjvpbgskMSOgboxdQtSNvGU"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(F.video | F.document)
async def handle_video(message: Message):
    status_msg = await message.reply("در حال دانلود و فشرده‌سازی ویدیو...")
    
    # تعیین مسیر دانلود فایل
    file_id = message.video.file_id if message.video else message.document.file_id
    file_info = await bot.get_file(file_id)
    input_path = f"input_{message.from_user.id}.mp4"
    output_path = f"compressed_{message.from_user.id}.mp4"
    
    try:
        # دانلود فایل از تلگرام
        await bot.download_file(file_info.file_path, input_path)
        
        # اجرای دستور FFmpeg برای فشرده‌سازی
        cmd = f'ffmpeg -y -i "{input_path}" -vcodec libx264 -crf 28 "{output_path}"'
        subprocess.run(cmd, shell=True, check=True)
        
        # ارسال ویدیوی فشرده‌شده
        with open(output_path, "rb") as video_file:
            await message.reply_video(video=video_file, caption="ویدیو با موفقیت فشرده شد!")
            
    except Exception as e:
        await message.reply(f"خطا در پردازش ویدیو: {str(e)}")
        
    finally:
        # پاکسازی فایل‌های موقت
        await status_msg.delete()
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
