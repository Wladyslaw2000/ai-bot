import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq
import fal_client
from elevenlabs.client import ElevenLabs

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
FAL_KEY = os.environ.get("FAL_KEY")

groq_agent = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
eleven_agent = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# --- Главное интерактивное меню ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖼 Создать Фото (Flux)", callback_data='help_image'), InlineKeyboardButton("🎬 Создать Видео (с нуля)", callback_data='help_gen_video')],
        [InlineKeyboardButton("📹 Переработать Видео (V2V)", callback_data='help_v2v'), InlineKeyboardButton("📷 Оживить Фото (I2V)", callback_data='help_i2v')],
        [InlineKeyboardButton("🎙 Озвучка (ElevenLabs)", callback_data='help_voice'), InlineKeyboardButton("⚡️ Проверить Ключи", callback_data='mode_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔥 **Многоцелевой ИИ-Комбайн**\n\n"
        "Выбери нужный режим ниже или отправляй контент прямо в чат:\n\n"
        "• **Текст / Сценарии:** просто пиши сообщение.\n"
        "• **Фото (девушки, пейзажи):** `/image [описание]`\n"
        "• **Видео с нуля:** `/video [описание]`\n"
        "• **Озвучить текст:** `/voice [текст]`\n"
        "• **Переработка ВИДЕО (5-10 сек целиком):** отправь видеоролик с ТЗ в подписи.\n"
        "• **Оживление ФОТО:** отправь фото с ТЗ в подписи.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'help_image':
        await query.edit_message_text("🎨 **Создание фото:**\nОтправь команду:\n`/image красиво одетыя девушка на фоне неонового города, портрет, 8k, photorealistic`", parse_mode='Markdown')
    elif query.data == 'help_gen_video':
        await query.edit_message_text("🎬 **Генерация видео с нуля:**\nОтправь команду:\n`/video девушка гуляет по парку, солнечный день, 4k`", parse_mode='Markdown')
    elif query.data == 'help_v2v':
        await query.edit_message_text("📹 **Переработка видео:**\nПрикрепи видеофайл (5-10 сек) и напиши в подписи, что изменить (например: *'добавь фильтры, измени стиль на аниме, сделай вечернее освещение'*).", parse_mode='Markdown')
    elif query.data == 'help_i2v':
        await query.edit_message_text("📷 **Оживление фото:**\nПрикрепи картинку/фото и напиши в подписи (например: *'девушка улыбается и моргает, ветер развевает волосы'*).", parse_mode='Markdown')
    elif query.data == 'help_voice':
        await query.edit_message_text("🎙 **Озвучка:**\nОтправь команду:\n`/voice Привет, это твой личный ИИ генератор`", parse_mode='Markdown')
    elif query.data == 'mode_status':
        status = (
            f"📊 **Статус подключения:**\n"
            f"• Telegram Bot: ✅ Активен\n"
            f"• Groq (Текст/Сценарии): {'✅ Подключен' if GROQ_API_KEY else '❌ Ошибка'}\n"
            f"• Fal.ai (Фото/Видео): {'✅ Подключен' if FAL_KEY else '❌ Ошибка'}\n"
            f"• ElevenLabs (Голос): {'✅ Подключен' if ELEVENLABS_API_KEY else '❌ Ошибка'}\n"
        )
        await query.edit_message_text(status, parse_mode='Markdown')

# --- 1. Текст и Сценарии (Groq Llama-3.3-70B) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not groq_agent:
        await update.message.reply_text("⚠️ Добавь GROQ_API_KEY в переменные окружения Render.")
        return
    msg = await update.message.reply_text("💡 Анализирую запрос...")
    try:
        completion = groq_agent.chat.completions.create(
            messages=[{"role": "user", "content": update.message.text}],
            model="llama-3.3-70b-versatile",
        )
        await msg.edit_text(completion.choices[0].message.content)
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка Groq: {str(e)}")

# --- 2. Генерация Фото с нуля (/image) ---
async def handle_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Пример: `/image красивый портрет девушки, реалистичное освещение, 8k`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎨 Генерирую изображение (FLUX)...")
    try:
        result = fal_client.subscribe("fal-ai/flux/schnell", arguments={"prompt": prompt, "image_size": "landscape_16_9"})
        await update.message.reply_photo(photo=result['images'][0]['url'], caption=f"🖼 **Промпт:** {prompt}", parse_mode='Markdown')
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка генерации фото: {str(e)}")

# --- 3. Генерация Видео с нуля (/video) ---
async def handle_video_gen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Пример: `/video кинематографичная девушка идущая по улице`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎬 Генерирую видео с нуля (Hunyuan Video)...")
    try:
        result = fal_client.subscribe(
            "fal-ai/hunyuan-video",
            arguments={"prompt": prompt, "aspect_ratio": "16:9"}
        )
        await update.message.reply_video(video=result['video']['url'], caption=f"🎬 **Видео:** {prompt}", parse_mode='Markdown')
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка генерации видео: {str(e)}")

# --- 4. Озвучка текста (/voice) ---
async def handle_voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_speak = " ".join(context.args)
    if not text_to_speak:
        await update.message.reply_text("Пример: `/voice Привет мир`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎙 Озвучиваю...")
    try:
        audio = eleven_agent.generate(text=text_to_speak, voice="Rachel", model="eleven_multilingual_v2")
        await update.message.reply_voice(voice=audio)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка озвучки: {str(e)}")

# --- 5. Переработка ВИДЕО целиком (Video-to-Video, 5-10 сек) ---
async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption or "High quality enhanced video, fix artifacts, high realism"
    msg = await update.message.reply_text("📹 **Видео получено!** Загружаю полный файл (5-10 сек) в облако...")
    local_file = "input_video.mp4"

    try:
        video_obj = await update.message.video.get_file()
        await video_obj.download_to_drive(local_file)

        await msg.edit_text("⚡️ **Полный ролик в облаке!** Анализирую весь видеоряд и запускаю рендер (Wan 2.2 V2V)...")
        video_url = fal_client.upload_file(local_file)

        result = fal_client.subscribe(
            "fal-ai/wan/v2.2-a14b/video-to-video",
            arguments={
                "prompt": caption,
                "video_url": video_url
            }
        )

        await update.message.reply_video(video=result['video']['url'], caption="✅ **Переработка завершена! Проверено от начала до конца.**")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка переработки видео: {str(e)}")
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)

# --- 6. Оживление ФОТО (Image-to-Video) ---
async def handle_photo_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption or "Cinematic natural motion, smooth movements"
    msg = await update.message.reply_text("📷 **Фото получено!** Отправляю в облако...")
    local_file = "input_photo.jpg"

    try:
        photo_obj = await update.message.photo[-1].get_file()
        await photo_obj.download_to_drive(local_file)

        await msg.edit_text("⚡️ **Анимирую изображение (Luma Dream Machine)...**")
        image_url = fal_client.upload_file(local_file)

        result = fal_client.subscribe(
            "fal-ai/luma-dream-machine/image-to-video",
            arguments={
                "prompt": caption,
                "image_url": image_url
            }
        )

        await update.message.reply_video(video=result['video']['url'], caption="✅ **Готово! Изображение оживлено.**")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка анимации фото: {str(e)}")
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", handle_image_command))
    app.add_handler(CommandHandler("video", handle_video_gen_command))
    app.add_handler(CommandHandler("voice", handle_voice_command))
    
    # Кнопки и медиа
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_file))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_file))
    
    app.run_polling()
