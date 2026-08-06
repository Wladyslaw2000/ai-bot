import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 ИИ-Комбайн запущен и готов к работе! Напиши мне что-нибудь.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not groq_client:
        await update.message.reply_text("⚠️ Ключ GROQ_API_KEY не найден в Environment Variables.")
        return
        
    user_text = update.message.text
    msg = await update.message.reply_text("🎬 Генерирую ответ...")
    
    try:
        completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": user_text}],
            model="llama3-8b-8192",
        )
        response = completion.choices[0].message.content
        await msg.edit_text(response)
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка: {str(e)}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📹 Видео успешно получено и отправлено в обработку!")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.run_polling()
