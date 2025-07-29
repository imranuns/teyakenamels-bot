# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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
WEBHOOK_URL = "" # Vercel ላይ ሲሆን በራሱ ይሞላል

# --- የተጠቃሚ ሁኔታ መከታተያ ---
user_translation_state = {}

# --- Gemini API የትርጉም ተግባር ---
def translate_text_with_gemini(text: str, target_language: str) -> str:
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set.")
        return "Translation service is not configured."

    prompt = f"Translate the following text into {target_language}. Provide only the translated text, without any additional explanations or context. Text to translate: {text}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()

        if result and result.get('candidates') and result['candidates'][0].get('content'):
            translated_text = result['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"Successfully translated '{text}' to '{translated_text}'")
            return translated_text.strip()
        else:
            logger.error(f"Translation failed: Unexpected API response format: {result}")
            return "Translation failed: Could not parse the response."
    except requests.exceptions.RequestException as e:
        logger.error(f"Translation failed due to an API error: {e}")
        return f"Translation failed due to an API error."
    except Exception as e:
        logger.error(f"An unexpected error occurred during translation: {e}")
        return f"An unexpected error occurred."

# --- የቴሌግራም ትዕዛዝ እና መልዕክት ተቆጣጣሪዎች ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_message = (
        f"Hello {user.mention_html()}! 👋\n\n"
        "I am a language translator bot powered by Gemini AI.\n\n"
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
        'en_am': {'source': 'English', 'target': 'am', 'prompt': "You chose English to Amharic. Please send the English text."},
        'am_en': {'source': 'Amharic', 'target': 'en', 'prompt': "You chose Amharic to English. Please send the Amharic text."}
    }

    if data in lang_map:
        option = lang_map[data]
        user_translation_state[user_id] = option['target']
        await query.edit_message_text(text=option['prompt'])
        logger.info(f"User {user_id} selected {data}.")
    else:
        await query.edit_message_text(text="Unknown option selected.")

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text_to_translate = update.message.text

    if user_id not in user_translation_state:
        await update.message.reply_text("Please select a translation direction from the /menu first.")
        return

    target_language = user_translation_state.pop(user_id)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    translated_text = translate_text_with_gemini(text_to_translate, target_language)
    await update.message.reply_text(translated_text)

# --- ዋናው የቴሌግራም አፕሊኬሽን ---
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", show_menu))
application.add_handler(CallbackQueryHandler(button_callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))

# --- ከ Vercel ጋር የሚያገናኙ ተግባራት ---

@app.route('/', methods=['POST'])
def webhook():
    asyncio.run(application.process_update(
        Update.de_json(request.get_json(force=True), application.bot)
    ))
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    global WEBHOOK_URL
    WEBHOOK_URL = f"https://{request.host}/"
    asyncio.run(application.bot.set_webhook(WEBHOOK_URL))
    return f"Webhook set to {WEBHOOK_URL}"

@app.route('/deletewebhook', methods=['GET', 'POST'])
def delete_webhook():
    asyncio.run(application.bot.delete_webhook())
    return "Webhook deleted"
# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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
WEBHOOK_URL = "" # Vercel ላይ ሲሆን በራሱ ይሞላል

# --- የተጠቃሚ ሁኔታ መከታተያ ---
user_translation_state = {}

# --- Gemini API የትርጉም ተግባር ---
def translate_text_with_gemini(text: str, target_language: str) -> str:
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set.")
        return "Translation service is not configured."

    prompt = f"Translate the following text into {target_language}. Provide only the translated text, without any additional explanations or context. Text to translate: {text}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()

        if result and result.get('candidates') and result['candidates'][0].get('content'):
            translated_text = result['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"Successfully translated '{text}' to '{translated_text}'")
            return translated_text.strip()
        else:
            logger.error(f"Translation failed: Unexpected API response format: {result}")
            return "Translation failed: Could not parse the response."
    except requests.exceptions.RequestException as e:
        logger.error(f"Translation failed due to an API error: {e}")
        return f"Translation failed due to an API error."
    except Exception as e:
        logger.error(f"An unexpected error occurred during translation: {e}")
        return f"An unexpected error occurred."

# --- የቴሌግራም ትዕዛዝ እና መልዕክት ተቆጣጣሪዎች ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_message = (
        f"Hello {user.mention_html()}! 👋\n\n"
        "I am a language translator bot powered by Gemini AI.\n\n"
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
        'en_am': {'source': 'English', 'target': 'am', 'prompt': "You chose English to Amharic. Please send the English text."},
        'am_en': {'source': 'Amharic', 'target': 'en', 'prompt': "You chose Amharic to English. Please send the Amharic text."}
    }

    if data in lang_map:
        option = lang_map[data]
        user_translation_state[user_id] = option['target']
        await query.edit_message_text(text=option['prompt'])
        logger.info(f"User {user_id} selected {data}.")
    else:
        await query.edit_message_text(text="Unknown option selected.")

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text_to_translate = update.message.text

    if user_id not in user_translation_state:
        await update.message.reply_text("Please select a translation direction from the /menu first.")
        return

    target_language = user_translation_state.pop(user_id)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    translated_text = translate_text_with_gemini(text_to_translate, target_language)
    await update.message.reply_text(translated_text)

# --- ዋናው የቴሌግራም አፕሊኬሽን ---
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", show_menu))
application.add_handler(CallbackQueryHandler(button_callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))

# --- ከ Vercel ጋር የሚያገናኙ ተግባራት ---

@app.route('/', methods=['POST'])
def webhook():
    asyncio.run(application.process_update(
        Update.de_json(request.get_json(force=True), application.bot)
    ))
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    global WEBHOOK_URL
    WEBHOOK_URL = f"https://{request.host}/"
    asyncio.run(application.bot.set_webhook(WEBHOOK_URL))
    return f"Webhook set to {WEBHOOK_URL}"

@app.route('/deletewebhook', methods=['GET', 'POST'])
def delete_webhook():
    asyncio.run(application.bot.delete_webhook())
    return "Webhook deleted"
