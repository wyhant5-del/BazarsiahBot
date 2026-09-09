import asyncio
import logging
import os
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiohttp import web

# توکن جدید
BOT_TOKEN = "8895497755:AAEAjZeyp6x_Vt_NPTQrgM0K8kP1l7ZnHbE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_file_size_mb(file_path):
    return os.path.getsize(file_path) / (1024 * 1024)

@dp.message(CommandStart())
async def send_welcome(message: Message):
    await message.reply(
        "👋 **به ربات فشرده‌ساز ویدیو خوش آمدید!**\n\n"
        "🎬 ویدیوی خود را ارسال کنید (حداکثر ۵۰ مگابایت) تا بدون افت کیفیت محسوس فشرده شود."
    )

@dp.message(F.video | F.document)
async def handle_video(message: Message):
    video_obj = message.video or message.document
    if message.document and not (message.document.mime_type and message.document.mime_type.startswith("video/")):
        await message.reply("⚠️ لطفاً فقط فایل ویدیویی ارسال کنید.")
        return

    if video_obj.file_size > 50 * 1024 * 1024:
        await message.reply("❌ حجم ویدیو بیشتر از ۵۰ مگابایت است. محدودیت ربات‌های تلگرام ۵۰ مگابایت می‌باشد.")
        return

    status_msg = await message.reply("📥 **در حال دریافت ویدیو از تلگرام...**")
    
    input_path = f"input_{message.from_user.id}.mp4"
    output_path = f"compressed_{message.from_user.id}.mp4"
    
    try:
        file_info = await bot.get_file(video_obj.file_id)
        await bot.download_file(file_info.file_path, input_path)
        
        orig_size = get_file_size_mb(input_path)
        await status_msg.edit_text(f"⚙️ **شروع فشرده‌سازی...**\n📏 حجم اولیه: `{orig_size:.1f} MB`")

        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-vcodec', 'libx264', '-crf', '26', '-preset', 'ultrafast',
            '-acodec', 'aac', output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        last_update_time = 0
        duration = None

        while True:
            line = await process.stderr.readline()
            if not line:
                break
            line_str = line.decode('utf-8', errors='ignore')

            if not duration:
                dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line_str)
                if dur_match:
                    h, m, s = map(float, dur_match.groups())
                    duration = h * 3600 + m * 60 + s

            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line_str)
            if time_match and duration and duration > 0:
                h, m, s = map(float, time_match.groups())
                elapsed = h * 3600 + m * 60 + s
                percent = min(100, int((elapsed / duration) * 100))

                now = asyncio.get_event_loop().time()
                if now - last_update_time > 3:
                    last_update_time = now
                    try:
                        await status_msg.edit_text(
                            f"⚙️ **در حال فشرده‌سازی:** `{percent}%`\n"
                            f"📊 [{('▓' * (percent // 10)).ljust(10, '░')}]"
                        )
                    except Exception:
                        pass

        await process.wait()

        if os.path.exists(output_path):
            new_size = get_file_size_mb(output_path)
            saved = max(0, int(((orig_size - new_size) / orig_size) * 100))

            await status_msg.edit_text("📤 **فشرده‌سازی تمام شد. در حال آپلود...**")
            
            caption = (
                f"✅ **فشرده‌سازی با موفقیت انجام شد!**\n\n"
                f"📦 حجم اولیه: `{orig_size:.1f} MB`\n"
                f"📉 حجم جدید: `{new_size:.1f} MB`\n"
                f"⚡ میزان کاهش حجم: `{saved}%`"
            )
            
            with open(output_path, "rb") as video_file:
                await message.reply_video(video=video_file, caption=caption, parse_mode="Markdown")
        else:
            await message.reply("❌ خطا در ایجاد فایل خروجی.")

    except Exception as e:
        await message.reply(f"❌ **خطا:** {str(e)}")

    finally:
        await status_msg.delete()
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

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
    await start_dummy_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
