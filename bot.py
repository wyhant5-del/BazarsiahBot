import asyncio
import logging
import os
import re
import time
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command, CommandStart
from aiohttp import web

BOT_TOKEN = "8895497755:AAEAjZeyp6x_Vt_NPTQrgM0K8kP1l7ZnHbE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


def get_file_size_mb(file_path):
    return os.path.getsize(file_path) / (1024 * 1024)


async def compress_and_send(message: Message, video_obj):
    if video_obj.file_size > 50 * 1024 * 1024:
        await message.reply("❌ حجم ویدیو بیشتر از ۵۰ مگابایت است. محدودیت ربات ۵۰ مگابایت می‌باشد.")
        return

    status_msg = await message.reply("📥 **در حال دریافت ویدیو از تلگرام...**")

    input_path = f"input_{message.from_user.id}_{video_obj.file_id[:6]}.mp4"
    output_path = f"compressed_{message.from_user.id}_{video_obj.file_id[:6]}.mp4"

    start_total_time = time.time()

    try:
        # ۱. دانلود ویدیو از تلگرام
        start_dl_time = time.time()
        file_info = await bot.get_file(video_obj.file_id)
        await bot.download(file=file_info, destination=input_path)
        dl_duration = time.time() - start_dl_time

        # محاسبه حجم واقعی روی دیسک (بدون دروغ!)
        orig_size = get_file_size_mb(input_path)

        await status_msg.edit_text(
            f"⚙️ **در حال فشرده‌سازی ویدیو...**\n"
            f"📏 حجم واقعی: `{orig_size:.2f} MB`"
        )

        start_compress_time = time.time()

        # ۲. اجرا دستور استاندارد فشرده‌سازی
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-vcodec', 'libx264',
            '-crf', '30',
            '-preset', 'veryfast',
            '-vf', "scale='min(720,iw)':-2",
            '-acodec', 'aac', '-b:a', '96k',
            '-movflags', '+faststart',
            output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024
        )

        last_update_time = 0
        duration_sec = 0
        stderr_lines = []  # برای دیباگ - کل خروجی خطای ffmpeg رو نگه می‌داریم

        # خوندن لاگ FFmpeg برای نمایش درصد پیشرفت
        while True:
            try:
                line = await process.stderr.readline()
            except Exception:
                break

            if not line:
                break
            line_str = line.decode('utf-8', errors='ignore')
            stderr_lines.append(line_str)

            if duration_sec <= 0:
                dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line_str)
                if dur_match:
                    h, m, s = map(float, dur_match.groups())
                    duration_sec = h * 3600 + m * 60 + s

            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line_str)
            if time_match and duration_sec > 0:
                h, m, s = map(float, time_match.groups())
                elapsed = h * 3600 + m * 60 + s
                percent = min(100, int((elapsed / duration_sec) * 100))

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
        compress_duration = time.time() - start_compress_time

        # ۲.۵ چک کردن اینکه ffmpeg واقعاً بدون خطا تموم شده باشه
        if process.returncode != 0:
            error_tail = "".join(stderr_lines[-15:])  # ۱۵ خط آخر لاگ خطا
            logging.error(f"FFmpeg failed (code {process.returncode}) for user {message.from_user.id}:\n{error_tail}")
            await status_msg.edit_text(
                f"❌ **خطا در فشرده‌سازی (کد {process.returncode})**\n"
                f"این خطا توی لاگ سرور ثبت شد."
            )
            return

        # ۳. چک کردن خروجی و ارسال ویدیو
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            new_size = get_file_size_mb(output_path)

            # اگر به هر دلیلی فایل فشرده بزرگتر شد، اصل فایل رو بفرست
            if new_size >= orig_size:
                final_file_path = input_path
                saved = 0
                new_size = orig_size
            else:
                final_file_path = output_path
                saved = round(((orig_size - new_size) / orig_size) * 100, 2)

            await status_msg.edit_text("📤 **فشرده‌سازی تمام شد. در حال آپلود...**")

            start_ul_time = time.time()
            video_file = FSInputFile(final_file_path)

            ul_duration = time.time() - start_ul_time
            total_duration = time.time() - start_total_time

            caption = (
                f"📦 `{orig_size:.2f} مگابایت` 👈 `{new_size:.2f} مگابایت`\n"
                f"⚡ `{saved}%` فشرده شد\n"
                f"📥 دانلود: `{dl_duration:.2f} ثانیه`\n"
                f"⚙️ فشرده‌سازی: `{compress_duration:.2f} ثانیه`\n"
                f"📤 آپلود: `{ul_duration:.2f} ثانیه`\n"
                f"⏱ زمان کل: `{total_duration:.2f} ثانیه`"
            )

            await message.reply_video(video=video_file, caption=caption, parse_mode="Markdown")
        else:
            error_tail = "".join(stderr_lines[-15:])
            logging.error(f"Output file missing/empty for user {message.from_user.id}:\n{error_tail}")
            await message.reply("❌ خطا در ایجاد فایل خروجی.")

    except Exception as e:
        logging.exception("Unexpected error in compress_and_send")
        await message.reply(f"❌ **خطا:** {str(e)}")

    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass
        # پاکسازی فایل‌های موقت روی سرور جهت پر نشدن حافظه
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)


@dp.message(CommandStart())
async def send_welcome(message: Message):
    await message.reply(
        "👋 **به ربات فشرده‌ساز ویدیو خوش آمدید!**\n\n"
        "🎬 ویدیوهای بالای ۱۰ مگابایت به صورت خودکار فشرده می‌شوند.\n"
        "📌 برای ویدیوهای زیر ۱۰ مگابایت، دستور `/compress` را روی ویدیو ریپلای کنید."
    )


@dp.message(Command("compress"))
async def handle_compress_command(message: Message):
    if not message.reply_to_message:
        await message.reply("⚠️ لطفاً دستور `/compress` را روی یک ویدیو ریپلای کنید.")
        return

    reply_msg = message.reply_to_message
    video_obj = reply_msg.video or reply_msg.document

    if not video_obj:
        await message.reply("⚠️ پیام ریپلای شده حاوی ویدیو نیست.")
        return

    if reply_msg.document and not (reply_msg.document.mime_type and reply_msg.document.mime_type.startswith("video/")):
        await message.reply("⚠️ لطفاً دستور را فقط روی فایل‌های ویدیویی ریپلای کنید.")
        return

    await compress_and_send(message, video_obj)


@dp.message(F.video | F.document)
async def handle_auto_video(message: Message):
    video_obj = message.video or message.document

    if message.document and not (message.document.mime_type and message.document.mime_type.startswith("video/")):
        return

    ten_mb = 10 * 1024 * 1024
    if video_obj.file_size >= ten_mb:
        await compress_and_send(message, video_obj)


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
    await start_dummy_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
