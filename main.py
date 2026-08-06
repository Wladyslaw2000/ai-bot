# Актуальная модель обработки/генерации видео (Hunyuan Video)
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption or "High quality video animation"
    msg = await update.message.reply_text("📹 **Видео принято!** Отправляю в облако Fal.ai, подожди 1-2 минуты...")
    try:
        result = fal_client.subscribe(
            "fal-ai/hunyuan-video",
            arguments={"prompt": caption}
        )
        await update.message.reply_video(video=result['video']['url'], caption="✅ **Готово!**")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"⚠️ Ошибка обработки видео: {str(e)}")
