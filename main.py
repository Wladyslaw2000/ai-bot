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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Написать Сценарий", callback_data='mode_script')],
        [InlineKeyboardButton("🎨 Инструкции по Картинкам", callback_data='mode_image_info')],
        [InlineKeyboardButton("🎙 Инструкции по Озвучке", callback_data='mode_voice_info')],
        [InlineKeyboardButton("⚡️ Проверить Ключи", callback_data='mode_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🚀 **ИИ-Комбайн запущен!**\n\n"
        "• **Текст:** пиши просто в чат\n"
        "• **Картинка:** `/image [описание]`\n"
        "• **Озвучка:** `/voice [текст]`\n"
        "• **Видео:** просто прикрепи видео с подписью.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'mode_script':
        await query.edit_message_text("Напиши тему или идею для сценария!")
    elif query.data == 'mode_image_info':
        await query.edit_message_text("Создание картинки:\n`/image киберпанк город`", parse_mode='Markdown')
    elif query.data == 'mode_voice_info':
        await query.edit_message_text("Озвучка текста:\n`/voice Привет всем`", parse_mode='Markdown')
    elif query.data == 'mode_status':
        status = (
            f"📊 **Статус подключения:**\n"
            f"• Telegram: ✅ Активен\n"
            f"• Groq: {'✅ OK' if GROQ_API_KEY else '❌ Нет ключа'}\n"
            f"• Fal.ai: {'✅ OK' if FAL_KEY else '❌ Нет ключа'}\n"
            f"• ElevenLabs: {'✅ OK' if ELEVENLABS_API_KEY else '❌ Нет ключа'}\n"
        )
        await query.edit_message_text(status, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not groq_agent:
        await update.message.reply_text("⚠️ Ошибка: Добавь GROQ_API_KEY в Render Environment.")
        return
    msg = await update.message.reply_text("🎬 Генерирую ответ...")
    try:
        completion = groq_agent.chat.completions.create(
            messages=[{"role": "user", "content": update.message.text}],
            model="llama-3.1-8b-instant",
        )
        await msg.edit_text(completion.choices[0].message.content)
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка Groq: {str(e)}")

async def handle_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Пиши так: `/image космический корабль`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎨 Генерирую изображение...")
    try:
        result = fal_client.subscribe("fal-ai/flux/schnell", arguments={"prompt": prompt})
        await update.message.reply_photo(photo=result['images'][0]['url'], caption=f"🖼 {prompt}")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка картинки: {str(e)}")

async def handle_voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_speak = " ".join(context.args)
    if not text_to_speak:
        await update.message.reply_text("Пиши так: `/voice Привет`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎙 Озвучиваю...")
    try:
        audio = eleven_agent.generate(text=text_to_speak, voice="Rachel", model="eleven_multilingual_v2")
        await update.message.reply_voice(voice=audio)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка голоса: {str(e)}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption or "High quality video processing"
    msg = await update.message.reply_text("📹 **Видео принято!** Отправляю в облако Fal.ai...")
    try:
        result = fal_client.subscribe(
            "fal-ai/hunyuan-video",
            arguments={"prompt": caption}
        )
        await update.message.reply_video(video=result['video']['url'], caption="✅ **Готово!**")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка обработки видео: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", handle_image_command))
    app.add_handler(CommandHandler("voice", handle_voice_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.run_polling()
