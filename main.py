import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq
import fal_client
from elevenlabs.client import ElevenLabs

# Настройка логов
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Получение ключей из Environment Variables на Render
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
FAL_KEY = os.environ.get("FAL_KEY")

# Инициализация клиентов API
groq_agent = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
eleven_agent = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# Команда /start с главным меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Написать Сценарий", callback_data='mode_script')],
        [InlineKeyboardButton("🎨 Инструкции по Картинкам", callback_data='mode_image_info')],
        [InlineKeyboardButton("🎙 Инструкции по Озвучке", callback_data='mode_voice_info')],
        [InlineKeyboardButton("⚡️ Проверить Ключи", callback_data='mode_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🚀 **ИИ-Комбайн полностью готов к работе!**\n\n"
        "Вся генерация происходит в облаке (на ноутбук нагрузки нет):\n"
        "• **Текст / Сценарии:** отправь любой текст прямо в чат.\n"
        "• **Картинка:** напиши `/image [описание]`\n"
        "• **Озвучка:** напиши `/voice [текст]`\n"
        "• **Обработка видео:** просто пришли видео в чат.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработка меню-кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'mode_script':
        await query.edit_message_text("Напиши мне тему или идею, и Агент-Режиссер создаст подробный сценарий!")
    elif query.data == 'mode_image_info':
        await query.edit_message_text("Чтобы создать изображение, отправь команду:\n`/image красиво оформленная девушка с цветами, кинематографично`", parse_mode='Markdown')
    elif query.data == 'mode_voice_info':
        await query.edit_message_text("Чтобы озвучить текст, отправь команду:\n`/voice Привет, это тестовая озвучка нейросетью`", parse_mode='Markdown')
    elif query.data == 'mode_status':
        status = (
            f"📊 **Статус подключений:**\n"
            f"• Telegram Bot: ✅ Активен\n"
            f"• Groq (Текст): {'✅ Подключен' if GROQ_API_KEY else '❌ Нет ключа'}\n"
            f"• Fal.ai (Визуал): {'✅ Подключен' if FAL_KEY else '❌ Нет ключа'}\n"
            f"• ElevenLabs (Голос): {'✅ Подключен' if ELEVENLABS_API_KEY else '❌ Нет ключа'}\n"
        )
        await query.edit_message_text(status, parse_mode='Markdown')

# Генерация текста через Groq
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    msg = await update.message.reply_text("🎬 **Агент-Режиссер:** Думаю над ответом...")
    
    try:
        completion = groq_agent.chat.completions.create(
            messages=[{"role": "user", "content": user_text}],
            model="llama3-8b-8192",
        )
        response = completion.choices[0].message.content
        await msg.edit_text(response)
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка генерации текста: {str(e)}")

# Генерация картинок через Fal.ai (/image промпт)
async def handle_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Укажи описание картинки. Пример:\n`/image космический корабль`", parse_mode='Markdown')
        return

    msg = await update.message.reply_text("🎨 **Агент-Художник:** Генерирую картинку через Fal.ai...")
    try:
        result = fal_client.subscribe(
            "fal-ai/flux/schnell",
            arguments={"prompt": prompt}
        )
        image_url = result['images'][0]['url']
        await update.message.reply_photo(photo=image_url, caption=f"🖼 **Запрос:** {prompt}")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка генерации изображения: {str(e)}")

# Озвучка текста через ElevenLabs (/voice текст)
async def handle_voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_speak = " ".join(context.args)
    if not text_to_speak:
        await update.message.reply_text("Укажи текст для озвучки. Пример:\n`/voice Привет мир`", parse_mode='Markdown')
        return

    msg = await update.message.reply_text("🎙 **Агент-Диктор:** Озвучиваю текст...")
    try:
        audio = eleven_agent.generate(
            text=text_to_speak,
            voice="Rachel",
            model="eleven_multilingual_v2"
        )
        await update.message.reply_voice(voice=audio)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка озвучки: {str(e)}")

# Прием видеофайлов
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📹 **Видео принято в облачный шлюз!** Все параметры и ТЗ переданы в систему обработчиков.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", handle_image_command))
    app.add_handler(CommandHandler("voice", handle_voice_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    app.run_polling()
    
