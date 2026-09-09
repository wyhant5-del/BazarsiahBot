import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

API_ID = int(os.environ.get("API_ID", "1234567"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

app = Client("CompressorBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
USER_SETTINGS = {}

async def progress(current, total, message, status_text):
    percent = (current / total) * 100
    if int(percent) % 20 == 0:
        try:
            await message.edit_text(f"⏳ {status_text}\n📊 پیشرفت: {percent:.1f}%")
        except Exception:
            pass

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("👋 سلام! ویدیو بفرست یا توی گروه روی یک ویدیو ریپلای کن و /compress رو بزن.")

@app.on_message(filters.command("settings"))
async def settings_cmd(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("کم‌حجم (CRF 28)", callback_data="quality_28")],
        [InlineKeyboardButton("تعادل عالی (CRF 24)", callback_data="quality_24")],
        [InlineKeyboardButton("کیفیت بالا (CRF 20)", callback_data="quality_20")]
    ])
    await message.reply_text("⚙️ کیفیت فشرده‌سازی رو انتخاب کن:", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"^quality_"))
async def set_quality(client, callback):
    crf = callback.data.split("_")[1]
    USER_SETTINGS[callback.from_user.id] = crf
    await callback.message.edit_text(f"✅ کیفیت تنظیم شد روی: {crf}")

@app.on_message(filters.command("compress") | (filters.private & (filters.video | filters.document)))
async def compress_handler(client, message: Message):
    target_msg = message.reply_to_message if message.reply_to_message else message

    if not (target_msg.video or (target_msg.document and target_msg.document.mime_type and target_msg.document.mime_type.startswith("video/"))):
        await message.reply_text("❌ لطفاً دستور /compress رو روی یک ویدیو ریپلای کن.")
        return

    status_msg = await message.reply_text("📥 در حال دانلود فایل...")
    crf_val = USER_SETTINGS.get(message.from_user.id, "26")

    file_path = await target_msg.download(progress=progress, progress_args=(status_msg, "در حال دانلود..."))
    output_path = f"compressed_{os.path.basename(file_path)}"
    await status_msg.edit_text("⚙️ در حال فشرده‌سازی...")

    ffmpeg_cmd = ["ffmpeg", "-i", file_path, "-vcodec", "libx264", "-crf", str(crf_val), "-preset", "faster", output_path, "-y"]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
        await status_msg.edit_text("📤 در حال آپلود...")
        await client.send_video(
            chat_id=message.chat.id,
            video=output_path,
            caption="✅ ویدیو با موفقیت فشرده شد!",
            reply_to_message_id=message.id,
            progress=progress,
            progress_args=(status_msg, "در حال آپلود...")
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(output_path): os.remove(output_path)
        await status_msg.delete()

if __name__ == "__main__":
    app.run()
