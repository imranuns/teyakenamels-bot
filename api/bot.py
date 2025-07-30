# -*- coding: utf-8 -*-
import os
import asyncio
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
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

# --- የተጠቃሚ ሁኔታ መከታተያ ---
user_translation_state = {}

# --- DeepSeek API የትርጉም ተግባር ---
def translate_text_with_deepseek(text: str, target_language: str) -> str:
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY is not set.")
        return "Text translation service is not configured. The API Key might be missing."

    api_url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful bilingual translator."},
            {"role": "user", "content": f"Translate the following text into {target_language}. Provide only the translated text, without any additional explanations or context. Text to translate: {text}"}
        ]
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=20)
        response.raise_for_status() # Check for HTTP errors
        
        result = response.json()
        
        if result and result.get('choices') and result['choices'][0].get('message'):
            translated_text = result['choices'][0]['message']['content']
            logger.info(f"Successfully translated text '{text}' to '{translated_text}' using DeepSeek.")
            return translated_text.strip()
        else:
            logger.error(f"DeepSeek API call failed: Unexpected response format: {result}")
            return "An error occurred: Could not parse the translation."

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"DeepSeek API call failed with HTTP error: {http_err}")
        if response.status_code == 401:
            return "Translation failed: The API key is not valid. Please check the configuration."
        return f"Translation failed due to a server error ({response.status_code})."
    except Exception as e:
        logger.error(f"DeepSeek API call failed with an unexpected error: {e}")
        return "An unexpected error occurred during translation."

# --- የቴሌግራም ትዕዛዝ እና መልዕክት ተቆጣጣሪዎች ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_message = (
        f"Hello {user.mention_html()}! 👋\n\n"
        "I am a language translator bot powered by DeepSeek AI.\n\n"
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
        'en_am': {'target': 'am', 'prompt': "You chose English to Amharic. Please send the English text you want to translate."},
        'am_en': {'target': 'en', 'prompt': "You chose Amharic to English. Please send the Amharic text you want to translate."}
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
    
    translated_text = translate_text_with_deepseek(text_to_translate, target_language)
    await update.message.reply_text(translated_text)

# --- ዋናው የቴሌግራም አፕሊኬሽን ---
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", show_menu))
application.add_handler(CallbackQueryHandler(button_callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text_message))

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