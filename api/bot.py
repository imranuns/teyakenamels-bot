# -*- coding: utf-8 -*-
import os
import asyncio
import logging
import requests
import google.generativeai as genai
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import Forbidden

# --- Logging ማዋቀር ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Flask App ማዋቀር ---
app = Flask(__name__)

# --- API Keys እና ሌሎች ቅንብሮች ---
TELEGRAM_BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- የተጠቃሚ ሁኔታ መከታተያ ---
user_translation_state = {}

# --- Gemini AI ሞዴሎችን ማዘጋጀት ---
text_model = None
pro_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    text_model = genai.GenerativeModel('gemini-1.5-flash')
    pro_model = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- Gemini API የትርጉም ተግባራት ---
def translate_text_with_gemini(text: str, target_language: str) -> str:
    if not text_model:
        return "Text translation service is not configured."
    
    prompt = f"Translate the following text into {target_language}. Provide only the translated text, without any additional explanations or context. Text to translate: {text}"
    
    try:
        response = text_model.generate_content(prompt)
        translated_text = response.text.strip()
        logger.info(f"Successfully translated text '{text}' to '{translated_text}'")
        return translated_text
    except Exception as e:
        logger.error(f"Text translation failed: {e}")
        return "An error occurred during text translation."

# --- የቴሌግራም ትዕዛዝ እና መልዕክት ተቆጣጣሪዎች ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_message = (
        f"Hello {user.mention_html()}! 👋\n\n"
        "I am a language translator bot. I can translate text and voice messages.\n\n"
        "Type /menu to see the translation options."
    )
    await update.message.reply_html(welcome_message)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English ➡️ Amharic 🇪🇹", callback_data='en_am')],
        [InlineKeyboardButton("🇪🇹 Amharic ➡️ English 🇬🇧", callback_data='am_en')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose a translation direction:', reply_markup=reply_markup)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    lang_map = {
        'en_am': {'target': 'am', 'prompt': "You chose English to Amharic. Please send the English text or a voice message."},
        'am_en': {'target': 'en', 'prompt': "You chose Amharic to English. Please send the Amharic text or a voice message."}
    }

    if data in lang_map:
        option = lang_map[data]
        user_translation_state[user_id] = option['target']
        await query.edit_message_text(text=option['prompt'])
        logger.info(f"User {user_id} selected {data}.")

async def translate_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text_to_translate = update.message.text

    if user_id not in user_translation_state:
        await update.message.reply_text("Please select a translation direction from the /menu first.")
        return

    target_language = user_translation_state[user_id]
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    translated_text = translate_text_with_gemini(text_to_translate, target_language)
    await update.message.reply_text(translated_text)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_translation_state:
        await update.message.reply_text("Please select a translation direction from the /menu first before sending a voice message.")
        return

    if not pro_model:
        await update.message.reply_text("Voice processing service is not configured.")
        return

    target_language = user_translation_state[user_id]
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    await update.message.reply_text("Processing your voice message... 🎤")

    voice = update.message.voice
    try:
        voice_file = await voice.get_file()
    except Forbidden:
        logger.warning(f"Forbidden: Bot can't download file from user {user_id}.")
        await update.message.reply_text("I can't access this voice message. This might be because it was forwarded from a user with privacy settings enabled. Please try recording a new voice message instead.")
        return

    file_content_bytes = await voice_file.download_as_bytearray()
    
    try:
        # This is a synchronous call, so we run it in a separate thread
        def process_voice_data():
            logger.info(f"Processing voice data directly for target language: {target_language}")
            
            # Create the audio part for the prompt as a dictionary
            audio_part = {
                "mime_type": voice.mime_type,
                "data": file_content_bytes
            }

            # Create the full prompt
            prompt = [
                f"You are a bilingual translator. First, accurately transcribe the audio data. Then, translate the transcribed text into {target_language}. Provide only the final translated text as the answer, without any other text or labels.",
                audio_part
            ]
            
            response = pro_model.generate_content(prompt)
            return response.text.strip()

        translated_text = await asyncio.to_thread(process_voice_data)
        await update.message.reply_text(translated_text)

    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await update.message.reply_text("Sorry, I couldn't process your voice message at this time.")


# --- ዋናው የቴሌግራም አፕሊኬሽን ---
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", show_menu))
application.add_handler(CallbackQueryHandler(button_callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text_message))
application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

# --- ከ Vercel ጋር የሚያገናኙ ተግባራት ---
@app.route('/', methods=['POST'])
def webhook():
    async def _process():
        async with application:
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
    
    asyncio.run(_process())
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    async def _set():
        async with application:
            url = f"https://{request.host}/"
            await application.bot.set_webhook(url)
    
    asyncio.run(_set())
    url = f"https://{request.host}/"
    return f"Webhook set to {url}"
