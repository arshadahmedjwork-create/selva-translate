import logging
import os
import tempfile
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from src.config import settings

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    welcome_text = (
        "Welcome to the Translation Assistant.\n\n"
        "Send any Tamil message to get English.\n"
        "Send any English message to get Tamil.\n"
        "You can also send Voice Notes!\n\n"
        "Use /enhance to edit or process your last voice transcript using Mistral AI."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /help command."""
    help_text = (
        "Supported Languages:\n"
        "• Tamil\n"
        "• English\n\n"
        "Commands:\n"
        "/enhance [instructions] - Enhance your last voice note transcript.\n\n"
        "Simply send a text message or a voice note. The translation will be returned automatically."
    )
    await update.message.reply_text(help_text)

async def enhance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /enhance or /enhance_api command."""
    message = update.effective_message
    chat_id = update.effective_chat.id
    
    last_transcript = context.user_data.get("last_transcript")
    if not last_transcript:
        await message.reply_text("No recent voice note transcript found. Please send a voice note first!")
        return

    # Check if user sent instructions inline (e.g., /enhance summarize this)
    args = context.args
    if args:
        instruction = " ".join(args).strip()
        await process_enhancement(message, last_transcript, instruction)
    else:
        # Prompt user for instruction and set state
        context.user_data["awaiting_enhance_instruction"] = True
        prompt_text = (
            f"🎤 **Last Transcript:**\n`{last_transcript}`\n\n"
            "What would you like me to do with this transcript? "
            "(e.g., 'summarize this', 'make it sound formal', 'translate it to French')"
        )
        await message.reply_text(prompt_text, parse_mode="Markdown")

async def process_enhancement(message, transcript: str, instruction: str):
    """Call Mistral to enhance the transcript and reply with result."""
    from src.services.mistral import mistral_service
    await message.reply_text("🔄 Processing enhancement using Mistral AI...")
    try:
        enhanced_text = await asyncio.to_thread(
            mistral_service.enhance_transcript, transcript, instruction
        )
        await message.reply_text(f"✨ **Enhanced Transcript:**\n\n{enhanced_text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in enhancement: {e}")
        await message.reply_text(f"Enhancement failed: {str(e)}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for incoming text messages."""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    if not text:
        return

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)

    # Check if we are waiting for an enhancement instruction
    if context.user_data.get("awaiting_enhance_instruction"):
        context.user_data["awaiting_enhance_instruction"] = False
        last_transcript = context.user_data.get("last_transcript")
        if not last_transcript:
            await message.reply_text("No recent voice note transcript found.")
            return
        await process_enhancement(message, last_transcript, text)
        return

    # Otherwise, perform translation
    logger.info(f"Processing text translation synchronously for user {user_id}")
    from src.services.translation import translation_service
    try:
        # Call translation service in a thread pool to avoid blocking the event loop
        translated_text, _, _ = await asyncio.to_thread(
            translation_service.translate_message, text
        )
        await message.reply_text(translated_text)
    except Exception as e:
        logger.error(f"Error in translation: {e}")
        await message.reply_text("Translation service is currently unavailable. Please try again later.")

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for incoming voice notes."""
    message = update.effective_message
    if not message or not message.voice:
        return

    file_id = message.voice.file_id
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    logger.info(f"Processing voice transcription synchronously for user {user_id}")
    
    from src.services.translation import translation_service
    from src.services.transcription import transcription_service
    
    local_path = None
    try:
        # 1. Retrieve file path from Telegram
        telegram_file = await context.bot.get_file(file_id)
        
        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        local_path = os.path.join(temp_dir, f"{file_id}.ogg")
        
        # 2. Download audio file
        await telegram_file.download_to_drive(local_path)
        
        # 3. Transcribe audio (run in threadpool)
        transcribed_text = await asyncio.to_thread(
            transcription_service.transcribe_audio, local_path
        )
        
        # Cache transcript in user session for /enhance commands
        context.user_data["last_transcript"] = transcribed_text
        context.user_data["awaiting_enhance_instruction"] = False
        
        # 4. Translate transcript (run in threadpool)
        translated_text, _, _ = await asyncio.to_thread(
            translation_service.translate_message, transcribed_text
        )
        
        # Reply to user
        response_text = (
            f"🎤 **Transcript:**\n{transcribed_text}\n\n"
            f"🔄 **Translation:**\n{translated_text}"
        )
        await message.reply_text(response_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in voice processing: {e}")
        await message.reply_text(f"Error processing voice: {str(e)}")
    finally:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as clean_err:
                logger.warning(f"Failed to delete local temp audio file: {clean_err}")

async def handle_invalid_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for unsupported message attachments/types."""
    await update.effective_message.reply_text("Please send a text message or voice note for translation.")

# Initialize the Application
bot_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

# Register handlers
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("help", help_command))
# Register /enhance and /enhance_api commands
bot_app.add_handler(CommandHandler("enhance", enhance_command))
bot_app.add_handler(CommandHandler("enhance_api", enhance_command))

bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
bot_app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
bot_app.add_handler(MessageHandler(
    (filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Sticker.ALL) & ~filters.COMMAND,
    handle_invalid_media
))
