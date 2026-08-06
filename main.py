import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq
import fal_client
from elevenlabs.client import ElevenLabs
from moviepy.editor import VideoFileClip

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

# Сила трансформации по умолчанию (0.50 = сохранение геометрии лица)
DEFAULT_V2V_STRENGTH = 0.50

# Вшитый мастер-промпт для защиты лица и предотвращения фликеринга
MASTER_VIDEO_PROMPT = (
    "STRICT IDENTITY PRESERVATION: Do not alter the person's face, jawline, eye structure, or distinct facial features. "
    "Keep exact original outfit, clothing color, hair length, and structural background intact. "
    "ENHANCEMENT ONLY: Cinematic 4k resolution, smooth 60fps movement, vibrant natural color grading, soft golden hour lighting. "
    "STABILITY: Zero flickering, zero temporal artifacts, remove motion blur and noise, no extra limbs, photorealistic finish."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    keyboard = [
        [InlineKeyboardButton("🖼 Создать Фото (Flux)", callback_data='help_image')],
        [InlineKeyboardButton("📹 Переработка ВИДЕО (V2V)", callback_data='help_v2v'), InlineKeyboardButton("📷 Оживить ФОТО (I2V)", callback_data='help_i2v')],
        [InlineKeyboardButton("🎙 Озвучка (ElevenLabs)", callback_data='help_voice'), InlineKeyboardButton("🪄 Промпт-Улучшайзер", callback_data='help_enhance')],
        [InlineKeyboardButton("🎵 Извлечь Звук", callback_data='help_audio'), InlineKeyboardButton("⚙️ Настройки Силы ИИ", callback_data='help_strength')],
        [InlineKeyboardButton("⚡️ Статус Подключений", callback_data='mode_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"👋 **Привет, {user_name}! Добро пожаловать в ИИ-Комбайн V3.5**\n\n"
        "⚡️ **Основные возможности:**\n"
        "• **Улучшение Видео (V2V):** Отправь ролик + напиши желаемый свет/ракурс. Бот удержит лицо на 100%.\n"
        "• **Анимация Фото (I2V):** Отправь фото + напиши движение в подписи.\n"
        "• **Генерация Фото:** Команда `/image [описание]`\n"
        "• **Синтез Голоса:** Команда `/voice [текст]`\n"
        "• **Генератор Промптов:** Команда `/enhance [короткая идея]`\n"
        "• **Извлечение Аудио:** Отправь видео с подписью `/extract_audio`\n"
        "• **Уровень ИИ:** Измени процент изменений через `/strength 0.4`"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help_image':
        text = "🎨 **Генерация Изображений (Flux Schnell)**\n\nОтправь команду:\n`/image портрет красивой девушки, 8k, золотой час, детализация`"
    elif query.data == 'help_v2v':
        text = "📹 **Переработка Видео (Wan 2.2 V2V)**\n\nПрикрепи видеофайл и напиши в подписи пожелание. Бот автоматически задействует мастер-промпт защиты лица."
    elif query.data == 'help_i2v':
        text = "📷 **Оживление Картинки (Luma Dream Machine)**\n\nПрикрепи фото и напиши в подписи желаемый пролёт камеры или движение."
    elif query.data == 'help_voice':
        text = "🎙 **Озвучка Текста (ElevenLabs)**\n\nОтправь команду:\n`/voice Привет! Твой видеоролик полностью обработан.`"
    elif query.data == 'help_enhance':
        text = "🪄 **Промпт-Улучшайзер (Groq Llama 3.3)**\n\nНапиши короткую идею:\n`/enhance девушка с подсолнухами на заборчике` — ИИ составит идеальное ТЗ."
    elif query.data == 'help_audio':
        text = "🎵 **Извлечение Аудиодорожки**\n\nПрикрепи видеофайл и напиши в подписи к нему команду:\n`/extract_audio`"
    elif query.data == 'help_strength':
        text = "⚙️ **Настройка силы трансформации (V2V Strength)**\n\nПо умолчанию стоит 0.50 (баланс сходства).\nОтправь командам:\n`/strength 0.35` — максимальное сходство с исходником\n`/strength 0.65` — больше изменений фона и стиля"
    elif query.data == 'mode_status':
        curr_str = context.user_data.get('v2v_strength', DEFAULT_V2V_STRENGTH)
        text = (
            f"📊 **Текущий Статус Системы:**\n\n"
            f"• Telegram Bot: ✅ Активен\n"
            f"• Groq AI (Llama 3.3): {'✅ Подключен' if GROQ_API_KEY else '❌ Ошибка'}\n"
            f"• Fal.ai (Wan & Flux): {'✅ Подключен' if FAL_KEY else '❌ Ошибка'}\n"
            f"• ElevenLabs Voice: {'✅ Подключен' if ELEVENLABS_API_KEY else '❌ Ошибка'}\n"
            f"• Настройка V2V Strength: 🎯 `{curr_str}`\n"
            f"• Система Защиты Лица: ✅ Включена"
        )
    await query.edit_message_text(text, parse_mode='Markdown')

async def handle_strength_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        curr_str = context.user_data.get('v2v_strength', DEFAULT_V2V_STRENGTH)
        await update.message.reply_text(f"Текущая сила трансформации: `{curr_str}`\nИзменить: `/strength 0.45` (диапазон от 0.2 до 0.8)", parse_mode='Markdown')
        return
    try:
        val = float(context.args[0])
        if 0.1 <= val <= 0.9:
            context.user_data['v2v_strength'] = val
            await update.message.reply_text(f"✅ Сила трансформации V2V установлена на: `{val}`", parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Введи число от 0.1 до 0.9.")
    except ValueError:
        await update.message.reply_text("⚠️ Неверный формат. Пример: `/strength 0.5`", parse_mode='Markdown')

async def handle_enhance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_idea = " ".join(context.args)
    if not raw_idea:
        await update.message.reply_text("Пример использования:\n`/enhance девушка на балконе на закате`", parse_mode='Markdown')
        return
    if not groq_agent:
        await update.message.reply_text("⚠️ Ошибка: Groq API недоступен.")
        return
    
    msg = await update.message.reply_text("🪄 Генерирую профессиональный английский промпт...")
    try:
        sys_prompt = "You are an expert prompt engineer. Translate and expand the user idea into a precise cinematic English prompt for AI video generation. Output ONLY the refined prompt text."
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
        await update.message.reply_text("Пример:\n`/image красиво одетая девушка, 8k, вечерний свет`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎨 Генерирую картинку (Flux Schnell)...")
    try:
        result = fal_client.subscribe("fal-ai/flux/schnell", arguments={"prompt": prompt})
        await update.message.reply_photo(photo=result['images'][0]['url'], caption=f"🖼 **Промпт:** {prompt}", parse_mode='Markdown')
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка создания картинки: {str(e)}")

async def handle_voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_speak = " ".join(context.args)
    if not text_to_speak:
        await update.message.reply_text("Пример:\n`/voice Привет! Обработка успешно завершена.`", parse_mode='Markdown')
        return
    msg = await update.message.reply_text("🎙 Озвучиваю текст через ElevenLabs...")
    try:
        audio = eleven_agent.generate(text=text_to_speak, voice="Rachel", model="eleven_multilingual_v2")
        await update.message.reply_voice(voice=audio)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка озвучки: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not groq_agent:
        await update.message.reply_text("⚠️ Ошибка: GROQ_API_KEY не задан.")
        return
    msg = await update.message.reply_text("💡 Думаю над ответом...")
    try:
        completion = groq_agent.chat.completions.create(
            messages=[{"role": "user", "content": update.message.text}],
            model="llama-3.3-70b-versatile",
        )
        await msg.edit_text(completion.choices[0].message.content)
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка Groq: {str(e)}")

async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_caption = update.message.caption or ""
    
    # Режим извлечения аудио
    if user_caption.strip().lower() == "/extract_audio":
        msg = await update.message.reply_text("🎵 Извлекаю аудиодорожку из видео...")
        local_video = "temp_video.mp4"
        local_audio = "extracted_audio.mp3"
        try:
            video_obj = await update.message.video.get_file()
            await video_obj.download_to_drive(local_video)
            clip = VideoFileClip(local_video)
            clip.audio.write_audiofile(local_audio, logger=None)
            clip.close()
            await update.message.reply_audio(audio=open(local_audio, 'rb'), caption="✅ Аудиофайлы вырезаны!")
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"⚠️ Ошибка вырезания звука: {str(e)}")
        finally:
            if os.path.exists(local_video): os.remove(local_video)
            if os.path.exists(local_audio): os.remove(local_audio)
        return

    # Обработка Video-to-Video
    msg = await update.message.reply_text("📹 **Видео получено!** Загружаю в облако Fal.ai...")
    local_file = "input_video.mp4"
    final_prompt = f"{MASTER_VIDEO_PROMPT} USER REQUEST: {user_caption}" if user_caption else MASTER_VIDEO_PROMPT
    strength_val = context.user_data.get('v2v_strength', DEFAULT_V2V_STRENGTH)

    try:
        video_obj = await update.message.video.get_file()
        await video_obj.download_to_drive(local_file)

        await msg.edit_text(f"⚡️ Перерабатываю ролик (Wan 2.2 V2V | strength: {strength_val})...")
        video_url = fal_client.upload_file(local_file)

        result = fal_client.subscribe(
            "fal-ai/wan/v2.2-a14b/video-to-video",
            arguments={
                "prompt": final_prompt,
                "video_url": video_url,
                "strength": strength_val
            }
        )

        await update.message.reply_video(
            video=result['video']['url'], 
            caption=f"✅ **Видео успешно переработано!**\n\n🎯 Сила изменения: `{strength_val}`\nЛицо и одежда зафиксированы."
        )
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка обработки видео: {str(e)}")
    finally:
        if os.path.exists(local_file): os.remove(local_file)

async def handle_photo_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_caption = update.message.caption or "Smooth camera orbit, high resolution, cinematic"
    msg = await update.message.reply_text("📷 **Фото получено!** Подготавливаю анимацию...")
    local_file = "input_photo.jpg"

    try:
        photo_obj = await update.message.photo[-1].get_file()
        await photo_obj.download_to_drive(local_file)

        await msg.edit_text("⚡️ **Оживляю фото через Luma Dream Machine...**")
        image_url = fal_client.upload_file(local_file)

        result = fal_client.subscribe(
            "fal-ai/luma-dream-machine/image-to-video",
            arguments={
                "prompt": user_caption,
                "image_url": image_url
            }
        )

        await update.message.reply_video(video=result['video']['url'], caption="✅ **Фото оживлено!**")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка анимации фото: {str(e)}")
    finally:
        if os.path.exists(local_file): os.remove(local_file)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", handle_image_command))
    app.add_handler(CommandHandler("voice", handle_voice_command))
    app.add_handler(CommandHandler("enhance", handle_enhance_command))
    app.add_handler(CommandHandler("strength", handle_strength_command))
    
    # Регистрация обработчиков сообщений
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_file))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_file))
    
    # Запуск бота
    app.run_polling()
