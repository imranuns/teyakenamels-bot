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
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# --- የቋንቋዎች ዝርዝር ---
LANGUAGES = {
    'auto': 'Automatic Detection', 'af': 'Afrikaans', 'sq': 'Albanian', 'am': 'Amharic', 'ar': 'Arabic',
    'hy': 'Armenian', 'az': 'Azerbaijani', 'eu': 'Basque', 'be': 'Belarusian', 'bn': 'Bengali',
    'bs': 'Bosnian', 'bg': 'Bulgarian', 'ca': 'Catalan', 'ceb': 'Cebuano', 'ny': 'Chichewa',
    'zh': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)', 'co': 'Corsican', 'hr': 'Croatian',
    'cs': 'Czech', 'da': 'Danish', 'nl': 'Dutch', 'en': 'English', 'eo': 'Esperanto', 'et': 'Estonian',
    'tl': 'Filipino', 'fi': 'Finnish', 'fr': 'French', 'fy': 'Frisian', 'gl': 'Galician', 'ka': 'Georgian',
    'de': 'German', 'el': 'Greek', 'gu': 'Gujarati', 'ht': 'Haitian Creole', 'ha': 'Hausa',
    'haw': 'Hawaiian', 'he': 'Hebrew', 'hi': 'Hindi', 'hmn': 'Hmong', 'hu': 'Hungarian', 'is': 'Icelandic',
    'ig': 'Igbo', 'id': 'Indonesian', 'ga': 'Irish', 'it': 'Italian', 'ja': 'Japanese', 'jv': 'Javanese',
    'kn': 'Kannada', 'kk': 'Kazakh', 'km': 'Khmer', 'rw': 'Kinyarwanda', 'ko': 'Korean', 'ku': 'Kurdish',
    'ky': 'Kyrgyz', 'lo': 'Lao', 'la': 'Latin', 'lv': 'Latvian', 'lt': 'Lithuanian', 'lb': 'Luxembourgish',
    'mk': 'Macedonian', 'mg': 'Malagasy', 'ms': 'Malay', 'ml': 'Malayalam', 'mt': 'Maltese', 'mi': 'Maori',
    'mr': 'Marathi', 'mn': 'Mongolian', 'my': 'Myanmar (Burmese)', 'ne': 'Nepali', 'no': 'Norwegian',
    'or': 'Odia (Oriya)', 'om': 'Oromo', 'ps': 'Pashto', 'fa': 'Persian', 'pl': 'Polish', 'pt': 'Portuguese',
    'pa': 'Punjabi', 'ro': 'Romanian', 'ru': 'Russian', 'sm': 'Samoan', 'gd': 'Scots Gaelic',
    'sr': 'Serbian', 'st': 'Sesotho', 'sn': 'Shona', 'sd': 'Sindhi', 'si': 'Sinhala', 'sk': 'Slovak',
    'sl': 'Slovenian', 'so': 'Somali', 'es': 'Spanish', 'su': 'Sundanese', 'sw': 'Swahili',
    'sv': 'Swedish', 'tg': 'Tajik', 'ta': 'Tamil', 'tt': 'Tatar', 'te': 'Telugu', 'th': 'Thai',
    'tr': 'Turkish', 'tk': 'Turkmen', 'uk': 'Ukrainian', 'ur': 'Urdu', 'ug': 'Uyghur', 'uz': 'Uzbek',
    'vi': 'Vietnamese', 'cy': 'Welsh', 'xh': 'Xhosa', 'yi': 'Yiddish', 'yo': 'Yoruba', 'zu': 'Zulu'
}
SORTED_LANG_CODES = sorted(LANGUAGES.keys(), key=lambda k: LANGUAGES[k])

# --- የተጠቃሚ ሁኔታ መከታተያ ---
user_settings = {} # Stores {'source': 'auto', 'target': 'en', 'action': None}

# --- Groq API የትርጉም ተግባር ---
def translate_text_with_groq(text: str, source_lang: str, target_lang: str) -> str:
    if not GROQ_API_KEY: return "Translation service is not configured."
    
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    source_language_name = f"'{LANGUAGES.get(source_lang, source_lang)}'" if source_lang != 'auto' else "the user's language"
    target_language_name = LANGUAGES.get(target_lang, target_lang)

    system_prompt = f"You are an expert translator. Your task is to translate text from {source_language_name} to {target_language_name}. Provide only the translated text."
    user_prompt = f"Translate the following text to {target_language_name}: \"{text}\""

    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=40)
        response.raise_for_status()
        result = response.json()
        translated_text = result['choices'][0]['message']['content'].strip()
        logger.info("Successfully translated text using Groq.")
        return translated_text
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return "An error occurred during translation."

# --- የቴሌግራም ትዕዛዝ እና መልዕክት ተቆጣጣሪዎች ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_settings[user_id] = {'source': 'auto', 'target': 'en'} # Default settings
    await update.message.reply_html(
        "Welcome! I am a powerful translator bot.\n\n"
        "My default setting is <b>Automatic Detection ➡️ English</b>.\n"
        "To change languages, use the /set command."
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Source Language (From)", callback_data='set_source')],
        [InlineKeyboardButton("Target Language (To)", callback_data='set_target')],
    ]
    await update.message.reply_text("Which language do you want to set?", reply_markup=InlineKeyboardMarkup(keyboard))

def create_language_keyboard(page: int, action: str) -> InlineKeyboardMarkup:
    buttons = []
    items_per_page = 20
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    
    page_langs = SORTED_LANG_CODES[start_index:end_index]

    for i in range(0, len(page_langs), 2):
        row = []
        row.append(InlineKeyboardButton(f"{LANGUAGES[page_langs[i]]}", callback_data=f"{action}_{page_langs[i]}"))
        if i + 1 < len(page_langs):
            row.append(InlineKeyboardButton(f"{LANGUAGES[page_langs[i+1]]}", callback_data=f"{action}_{page_langs[i+1]}"))
        buttons.append(row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{action}_{page-1}"))
    if end_index < len(SORTED_LANG_CODES):
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{action}_{page+1}"))
    buttons.append(nav_row)
    
    return InlineKeyboardMarkup(buttons)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith('set_'):
        action = data.split('_')[1] # source or target
        user_settings.setdefault(user_id, {})['action'] = action
        keyboard = create_language_keyboard(0, action)
        await query.edit_message_text(f"Please select the '{action.title()}' language (Page 1):", reply_markup=keyboard)
    
    elif data.startswith('page_'):
        _, action, page_str = data.split('_')
        page = int(page_str)
        keyboard = create_language_keyboard(page, action)
        await query.edit_message_text(f"Please select the '{action.title()}' language (Page {page+1}):", reply_markup=keyboard)

    elif data.startswith('source_') or data.startswith('target_'):
        action, lang_code = data.split('_', 1)
        if user_id not in user_settings: user_settings[user_id] = {}
        user_settings[user_id][action] = lang_code
        lang_name = LANGUAGES.get(lang_code, lang_code)
        
        source = user_settings[user_id].get('source', 'auto')
        target = user_settings[user_id].get('target', 'en')

        await query.edit_message_text(
            f"Settings updated!\n\n"
            f"<b>From:</b> {LANGUAGES.get(source, source)}\n"
            f"<b>To:</b> {LANGUAGES.get(target, target)}\n\n"
            "You can now send text to translate.",
            parse_mode='HTML'
        )

async def translate_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_settings:
        await start(update, context)
        return

    settings = user_settings[user_id]
    source_lang = settings.get('source', 'auto')
    target_lang = settings.get('target', 'en')
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    translated_text = translate_text_with_groq(update.message.text, source_lang, target_lang)
    await update.message.reply_text(translated_text)

# --- ዋናው የቴሌግራም አፕሊኬሽን ---
if not TELEGRAM_BOT_TOKEN: raise ValueError("BOT_TOKEN is not set!")
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("set", set_language))
application.add_handler(CallbackQueryHandler(button_callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text_message))

# --- ከ Vercel ጋር የሚያገናኙ ተግባራት ---
@app.route('/', methods=['POST'])
def webhook():
    async def _process():
        async with application:
            await application.process_update(Update.de_json(request.get_json(force=True), application.bot))
    asyncio.run(_process())
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook_route():
    async def _set():
        async with application:
            url = f"https://{request.host}/"
            await application.bot.set_webhook(url)
    asyncio.run(_set())
    return f"Webhook set to https://{request.host}/"
