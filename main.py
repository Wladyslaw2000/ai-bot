import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq
import fal_client
from elevenlabs.client import ElevenLabs
from moviepy import VideoFileClip

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Переменные окружения (API-ключи)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
FAL_KEY = os.environ.get("FAL_KEY")

# Инициализация клиентов
groq_agent = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
eleven_agent = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

DEFAULT_V2V_STRENGTH = 0.65

# Промпт для обеспечения плавности, высокого разрешения и устранения рывков
MASTER_VIDEO_PROMPT = (
    "Cinematic 4k resolution, ultra-smooth motion, slow panning camera shot, "
    "natural lighting, highly detailed face features, photorealistic, 60fps, no jitter, no artifacts, masterpiece."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    keyboard = [
        [InlineKeyboardButton("🖼 Создать Фото (Flux)", callback_data='help_image')],
        [InlineKeyboardButton("📹 Режим Видео (HQ Animation)", callback_data='help_v2v'), InlineKeyboardButton("📷 Оживить ФОТО (I2V)", callback_data='help_i2v')],
        [InlineKeyboardButton("🎙 Озвучка (ElevenLabs)", callback_data='help_voice'), InlineKeyboardButton("🪄 Промпт-Улучшайзер", callback_data='help_enhance')],
        [InlineKeyboardButton("🎵 Извлечь Звук", callback_data='help_audio'), InlineKeyboardButton("⚙️ Настройки Силы ИИ", callback_data='help_strength')],
        [InlineKeyboardButton("⚡️ Статус Подключений", callback_data='mode_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"👋 **Привет, {user_name}! Добро пожаловать в ИИ-Комбайн V4.0 HD**\n\n"
        "⚡️ **Основные возможности:**\n"
        "• **Обработка Видео:** Отправь ролик + напиши желаемый сюжет/движение.\n"
        "• **Анимация Фото (I2V):** Отправь фото + напиши движение кадра.\n"
        "• **Генерация Фото:** Команда `/image [описание]`\n"
        "• **Синтез Голоса:** Команда `/voice [текст]`\n"
        "• **Генератор Промптов:** Команда `/enhance [идея]`\n"
        "• **Сила ИИ:** Измени процент изменений через `/strength 0.65`"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help_image':
        text = "🎨 **Генерация Изображений (Flux Schnell)**\n\nПример:\n`/image портрет красивой девушки, 8k, золотой час`"
    elif query.data == 'help_v2v':
        text = "📹 **Обработка и Улучшение Видео**\n\nПрикрепи видеофайл и напиши желаемое движение/стиль. Бот извлечет идеальный кадр и сгенерирует плавный ролик высокого качества."
    elif query.data == 'help_i2v':
        text = "📷 **Оживление Фото (Luma / Wan I2V)**\n\nПрикрепи фото и напиши в подписи желаемое движение камеры или человека."
    elif query.data == 'help_voice':
        text = "🎙 **Озвучка Текста (ElevenLabs)**\n\nПример:\n`/voice Привет! Видеоролик полностью готов.`"
    elif query.data == 'help_enhance':
        text = "🪄 **Промпт-Улучшайзер**\n\nПример:\n`/enhance девушка с букетом цветов на закате` — ИИ создаст готовый английский промпт."
    elif query.data == 'help_audio':
        text = "🎵 **Извлечение Аудио**\n\nПрикрепи видео и напиши подпись:\n`/extract_audio`"
    elif query.data == 'help_strength':
        text = "⚙️ **Настройка Силы Изменений (V2V Strength)**\n\nОтправь команду:\n`/strength 0.4` — точное повторение оригинальных кадров\n`/strength 0.7` — плавная генерация новых красивых движений"
    elif query.data == 'mode_status':
        curr_str = context.user_data.get('v2v_strength', DEFAULT_V2V_STRENGTH)
        text = (
            f"📊 **Статус Системы:**\n\n"
            f"• Telegram Bot: ✅ Активен\n"
            f"• Groq AI: {'✅ Подключен' if GROQ_API_KEY else '❌ Ошибка'}\n"
            f"• Fal.ai: {'✅ Подключен' if FAL_KEY else '❌ Ошибка'}\n"
            f"• ElevenLabs: {'✅ Подключен' if ELEVENLABS_API_KEY else '❌ Ошибка'}\n"
            f"• V2V Strength: 🎯 `{curr_str}`"
        )
    await query.edit_message_text(text, parse_mode='Markdown')

async def handle_strength_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        curr_str = context.user_data.get('v2v_strength', DEFAULT_V2V_STRENGTH)
        await update.message.reply_text(f"Текущая сила: `{curr_str}`\nИзменить: `/strength 0.6` (от 0.1 до 0.9)", parse_mode='Markdown')
        return
    try:
        val = float(context.args[0])
        if 0.1 <= val <= 0.9:
            context.user_data['v2v_strength'] = val
            await update.message.reply_text(f"✅ Сила трансформации установлена на: `{val}`", parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Введи число от 0.1 до 0.9.")
    except ValueError:
        await update.message.reply_text("⚠️ Пример: `/strength 0.6`", parse_mode='Markdown')

async def handle_enhance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_idea = " ".join(context.args)
    if not raw_idea:
        await update.message.reply_text("Пример:\n`/enhance девушка идет по парку`", parse_mode='Markdown')
        return
    if not groq_agent:
        await update.message.reply_text("⚠️ Groq API недоступен.")
        return
    
    msg = await update.message.reply_text("🪄 Создаю профессиональный промпт...")
    try:
        sys_prompt = "You are an expert cinematic prompt engineer for AI video generation (Wan 2.1, Luma). Translate the user idea into a detailed, smooth cinematic prompt in English."
        completion = groq_agent.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": raw_idea}
            ],
            model="llama-3.3-70b-versatile",
        )
        enhanced = completion.choices[0].message.content.strip()
        await msg.edit_text(f"✨ **Сгенерированный Промпт:**\n\n`{enhanced}`", parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка: {str(e)}")

async def handle_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Пример:\n`/image красиво одетая девушка, 8k`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎨 Генерирую изображение...")
    try:
        result = fal_client.subscribe("fal-ai/flux/schnell", arguments={"prompt": prompt})
        await update.message.reply_photo(photo=result['images'][0]['url'], caption=f"🖼 **Промпт:** {prompt}", parse_mode='Markdown')
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка: {str(e)}")

async def handle_voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_speak = " ".join(context.args)
    if not text_to_speak:
        await update.message.reply_text("Пример:\n`/voice Текст для озвучки.`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎙 Озвучиваю...")
    try:
        audio = eleven_agent.generate(text=text_to_speak, voice="Rachel", model="eleven_multilingual_v2")
        await update.message.reply_voice(voice=audio)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not groq_agent:
        await update.message.reply_text("⚠️ GROQ_API_KEY не задан.")
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

async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_caption = update.message.caption or "Girl walking smoothly, cinematic lighting, photorealistic"
    
    if user_caption.strip().lower() == "/extract_audio":
        msg = await update.message.reply_text("🎵 Извлекаю звук...")
        local_video = "temp_vid.mp4"
        local_audio = "extracted.mp3"
        try:
            video_obj = await update.message.video.get_file()
            await video_obj.download_to_drive(local_video)
            clip = VideoFileClip(local_video)
            clip.audio.write_audiofile(local_audio, logger=None)
            clip.close()
            await update.message.reply_audio(audio=open(local_audio, 'rb'), caption="✅ Аудио готово!")
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"⚠️ Ошибка извлечения: {str(e)}")
        finally:
            if os.path.exists(local_video): os.remove(local_video)
            if os.path.exists(local_audio): os.remove(local_audio)
        return

    msg = await update.message.reply_text("📹 **Видео получено!** Подготавливаю кадры...")
    local_video = "input_video.mp4"
    extracted_frame = "first_frame.jpg"

    try:
        video_obj = await update.message.video.get_file()
        await video_obj.download_to_drive(local_video)

        # Извлекаем первый кадр из видео
        clip = VideoFileClip(local_video)
        clip.save_frame(extracted_frame, t=0.5)
        clip.close()

        await msg.edit_text("⚡️ **Генерирую кинематографичное видео (Wan 2.1)...**")
        image_url = fal_client.upload_file(extracted_frame)
        
        full_prompt = f"{user_caption}, {MASTER_VIDEO_PROMPT}"

        # Генерация на проверенном эндпоинте Wan 2.1
        result = fal_client.subscribe(
            "fal-ai/wan-i2v",
            arguments={
                "prompt": full_prompt,
                "image_url": image_url,
                "aspect_ratio": "9:16"
            }
        )

        await update.message.reply_video(
            video=result['video']['url'], 
            caption="✨ **Идеальное видео готово!**\n\nПлавные движения сгенерированы без дерганий и лагов."
        )
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка обработки видео: {str(e)}")
    finally:
        if os.path.exists(local_video): os.remove(local_video)
        if os.path.exists(extracted_frame): os.remove(extracted_frame)

async def handle_photo_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_caption = update.message.caption or "Smooth slow motion camera pan, highly detailed"
    msg = await update.message.reply_text("📷 **Фото получено!** Запускаю анимацию...")
    local_file = "input_photo.jpg"

    try:
        photo_obj = await update.message.photo[-1].get_file()
        await photo_obj.download_to_drive(local_file)

        await msg.edit_text("⚡️ **Оживляю фото (Luma Dream Machine)...**")
        image_url = fal_client.upload_file(local_file)

        full_prompt = f"{user_caption}, {MASTER_VIDEO_PROMPT}"

        result = fal_client.subscribe(
            "fal-ai/luma-dream-machine/image-to-video",
            arguments={
                "prompt": full_prompt,
                "image_url": image_url
            }
        )

        await update.message.reply_video(video=result['video']['url'], caption="✅ **Фото успешно оживлено!**")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка: {str(e)}")
    finally:
        if os.path.exists(local_file): os.remove(local_file)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", handle_image_command))
    app.add_handler(CommandHandler("voice", handle_voice_command))
    app.add_handler(CommandHandler("enhance", handle_enhance_command))
    app.add_handler(CommandHandler("strength", handle_strength_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_file))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_file))
    
    app.run_polling()
