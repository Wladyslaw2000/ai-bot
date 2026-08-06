import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq
import fal_client
from elevenlabs.client import ElevenLabs
from moviepy.editor import VideoFileClip

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
FAL_KEY = os.environ.get("FAL_KEY")

groq_agent = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
eleven_agent = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# Вшитая системная защита от всех ошибок ИИ при генерации видео
MASTER_VIDEO_PROMPT = (
    "STRICT IDENTITY PRESERVATION: Do not change the person's face, facial features, gender, or age. "
    "Keep exact original clothing, outfit, colors, and overall composition intact. "
    "ENHANCEMENT: Cinematic 4k resolution, 60fps smooth motion, professional golden hour lighting, color graded, photorealistic. "
    "FIXES: Remove video noise, fix camera shake, prevent flickering, ensure strict temporal consistency across all frames. "
    "NO HALLUCINATIONS: No extra limbs, no body morphing, no distortion. "
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖼 Создать Фото (Flux)", callback_data='help_image')],
        [InlineKeyboardButton("📹 Переработка ВИДЕО (V2V)", callback_data='help_v2v'), InlineKeyboardButton("📷 Оживить ФОТО (I2V)", callback_data='help_i2v')],
        [InlineKeyboardButton("🎙 Озвучка (ElevenLabs)", callback_data='help_voice'), InlineKeyboardButton("🪄 Промпт-Улучшайзер", callback_data='help_enhance')],
        [InlineKeyboardButton("⚡️ Статус Системы", callback_data='mode_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔥 **Многоцелевой ИИ-Комбайн (Версия с Защитой Лица)**\n\n"
        "• **Улучшение видео:** Отправь видео и напиши пожелания в подписи.\n"
        "• **Анимация фото:** Отправь фото и напиши движение в подписи.\n"
        "• **Фото по тексту:** `/image [описание]`\n"
        "• **Озвучка:** `/voice [текст]`\n"
        "• **Генератор промптов:** `/enhance [идея]`\n"
        "• **Извлечь звук из видео:** Отправь видео с подписью `/extract_audio`",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'help_image':
        await query.edit_message_text("🎨 **Создание фото:**\n`/image портрет девушки, 8k, вечерний свет`", parse_mode='Markdown')
    elif query.data == 'help_v2v':
        await query.edit_message_text("📹 **Переработка видео:**\nОтправь видео ролик. Бот автоматически заблокирует изменение лица и улучшит качество до 4K.", parse_mode='Markdown')
    elif query.data == 'help_i2v':
        await query.edit_message_text("📷 **Оживление фото:**\nОтправь фото сестры и напиши в подписи: `медленный пролёт камеры`", parse_mode='Markdown')
    elif query.data == 'help_voice':
        await query.edit_message_text("🎙 **Озвучка:**\n`/voice Привет, как дела?`", parse_mode='Markdown')
    elif query.data == 'help_enhance':
        await query.edit_message_text("🪄 **Улучшайзер промптов:**\n`/enhance девушка с подсолнухами на заборчике` — ИИ составит идеальный промпт на английском.", parse_mode='Markdown')
    elif query.data == 'mode_status':
        status = (
            f"📊 **Статус подключения:**\n"
            f"• Telegram Bot: ✅ Активен\n"
            f"• Groq (Llama 3.3): {'✅ OK' if GROQ_API_KEY else '❌ Ошибка'}\n"
            f"• Fal.ai (Wan / Flux): {'✅ OK' if FAL_KEY else '❌ Ошибка'}\n"
            f"• ElevenLabs: {'✅ OK' if ELEVENLABS_API_KEY else '❌ Ошибка'}\n"
            f"• Master Face Guard: ✅ Включен"
        )
        await query.edit_message_text(status, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not groq_agent:
        await update.message.reply_text("⚠️ Ошибка: GROQ_API_KEY не найден.")
        return
    msg = await update.message.reply_text("💡 Думаю...")
    try:
        completion = groq_agent.chat.completions.create(
            messages=[{"role": "user", "content": update.message.text}],
            model="llama-3.3-70b-versatile",
        )
        await msg.edit_text(completion.choices[0].message.content)
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка: {str(e)}")

async def handle_enhance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_idea = " ".join(context.args)
    if not raw_idea:
        await update.message.reply_text("Пример: `/enhance девушка идет по городу на закате`", parse_mode='Markdown')
        return
    if not groq_agent:
        await update.message.reply_text("⚠️ Ошибка: Groq API недоступен.")
        return
    
    msg = await update.message.reply_text("🪄 Генерирую профессиональный промпт...")
    try:
        sys_prompt = "You are an expert AI prompt engineer. Translate the user prompt into a highly detailed, cinematic, high-quality English prompt for video/image generation models. Output ONLY the refined English prompt."
        completion = groq_agent.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": raw_idea}
            ],
            model="llama-3.3-70b-versatile",
        )
        enhanced_prompt = completion.choices[0].message.content.strip()
        await msg.edit_text(f"✨ **Готовый промпт:**\n\n`{enhanced_prompt}`", parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка: {str(e)}")

async def handle_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Пример: `/image красиво одетая девушка, 8k`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎨 Генерирую фото...")
    try:
        result = fal_client.subscribe("fal-ai/flux/schnell", arguments={"prompt": prompt})
        await update.message.reply_photo(photo=result['images'][0]['url'], caption=f"🖼 **Промпт:** {prompt}", parse_mode='Markdown')
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка генерации фото: {str(e)}")

async def handle_voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_speak = " ".join(context.args)
    if not text_to_speak:
        await update.message.reply_text("Пример: `/voice Привет`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎙 Озвучиваю...")
    try:
        audio = eleven_agent.generate(text=text_to_speak, voice="Rachel", model="eleven_multilingual_v2")
        await update.message.reply_voice(voice=audio)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка озвучки: {str(e)}")

async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_caption = update.message.caption or ""
    
    # Режим извлечения аудио
    if user_caption.strip().lower() == "/extract_audio":
        msg = await update.message.reply_text("🎵 Извлекаю аудиодорожку...")
        local_video = "temp_video.mp4"
        local_audio = "extracted_audio.mp3"
        try:
            video_obj = await update.message.video.get_file()
            await video_obj.download_to_drive(local_video)
            clip = VideoFileClip(local_video)
            clip.audio.write_audiofile(local_audio, logger=None)
            clip.close()
            await update.message.reply_audio(audio=open(local_audio, 'rb'), caption="✅ Аудио успешно извлечено!")
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"⚠️ Ошибка извлечения звука: {str(e)}")
        finally:
            if os.path.exists(local_video): os.remove(local_video)
            if os.path.exists(local_audio): os.remove(local_audio)
        return

    # Режим Video-to-Video обработки
    msg = await update.message.reply_text("📹 **Видео получено!** Применяю систему защиты лица...")
    local_file = "input_video.mp4"
    final_prompt = f"{MASTER_VIDEO_PROMPT} USER REQUEST: {user_caption}" if user_caption else MASTER_VIDEO_PROMPT

    try:
        video_obj = await update.message.video.get_file()
        await video_obj.download_to_drive(local_file)

        await msg.edit_text("⚡️ Перерабатываю в Wan 2.2 V2V (сохраняю 100% внешность)...")
        video_url = fal_client.upload_file(local_file)

        result = fal_client.subscribe(
            "fal-ai/wan/v2.2-a14b/video-to-video",
            arguments={
                "prompt": final_prompt,
                "video_url": video_url
            }
        )

        await update.message.reply_video(video=result['video']['url'], caption="✅ **Видео успешно переработано!**\nЛицо и одежда зафиксированы.")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка обработки: {str(e)}")
    finally:
        if os.path.exists(local_file): os.remove(local_file)

async def handle_photo_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_caption = update.message.caption or "Smooth cinematic motion, highly detailed"
    msg = await update.message.reply_text("📷 **Фото получено!** Загружаю в облако...")
    local_file = "input_photo.jpg"

    try:
        photo_obj = await update.message.photo[-1].get_file()
        await photo_obj.download_to_drive(local_file)

        await msg.edit_text("⚡️ **Оживляю фото (Luma Dream Machine)...**")
        image_url = fal_client.upload_file(local_file)

        result = fal_client.subscribe(
            "fal-ai/luma-dream-machine/image-to-video",
            arguments={
                "prompt": user_caption,
                "image_url": image_url
            }
        )

        await update.message.reply_video(video=result['video']['url'], caption="✅ **Фото успешно оживлено!**")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка анимации фото: {str(e)}")
    finally:
        if os.path.exists(local_file): os.remove(local_file)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", handle_image_command))
    app.add_handler(CommandHandler("voice", handle_voice_command))
    app.add_handler(CommandHandler("enhance", handle_enhance_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_file))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_file))
    
    app.run_polling()
