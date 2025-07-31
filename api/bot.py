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
ADMIN_ID = os.environ.get('ADMIN_ID')

# --- የቋንቋዎች ዝርዝር ---
LANGUAGES = {
    'af': 'Afrikaans', 'sq': 'Albanian', 'am': 'Amharic', 'ar': 'Arabic', 'hy': 'Armenian', 'az': 'Azerbaijani',
    'eu': 'Basque', 'be': 'Belarusian', 'bn': 'Bengali', 'bs': 'Bosnian', 'bg': 'Bulgarian', 'ca': 'Catalan',
    'ceb': 'Cebuano', 'ny': 'Chichewa', 'zh': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)',
    'co': 'Corsican', 'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish', 'nl': 'Dutch', 'en': 'English',
    'eo': 'Esperanto', 'et': 'Estonian', 'tl': 'Filipino', 'fi': 'Finnish', 'fr': 'French', 'fy': 'Frisian',
    'gl': 'Galician', 'ka': 'Georgian', 'de': 'German', 'el': 'Greek', 'gu': 'Gujarati', 'ht': 'Haitian Creole',
    'ha': 'Hausa', 'haw': 'Hawaiian', 'he': 'Hebrew', 'hi': 'Hindi', 'hmn': 'Hmong', 'hu': 'Hungarian',
    'is': 'Icelandic', 'ig': 'Igbo', 'id': 'Indonesian', 'ga': 'Irish', 'it': 'Italian', 'ja': 'Japanese',
    'jv': 'Javanese', 'kn': 'Kannada', 'kk': 'Kazakh', 'km': 'Khmer', 'rw': 'Kinyarwanda', 'ko': 'Korean',
    'ku': 'Kurdish', 'ky': 'Kyrgyz', 'lo': 'Lao', 'la': 'Latin', 'lv': 'Latvian', 'lt': 'Lithuanian',
    'lb': 'Luxembourgish', 'mk': 'Macedonian', 'mg': 'Malagasy', 'ms': 'Malay', 'ml': 'Malayalam',
    'mt': 'Maltese', 'mi': 'Maori', 'mr': 'Marathi', 'mn': 'Mongolian', 'my': 'Myanmar (Burmese)',
    'ne': 'Nepali', 'no': 'Norwegian', 'or': 'Odia (Oriya)', 'om': 'Oromo', 'ps': 'Pashto', 'fa': 'Persian',
    'pl': 'Polish', 'pt': 'Portuguese', 'pa': 'Punjabi', 'ro': 'Romanian', 'ru': 'Russian', 'sm': 'Samoan',
    'gd': 'Scots Gaelic', 'sr': 'Serbian', 'st': 'Sesotho', 'sn': 'Shona', 'sd': 'Sindhi', 'si': 'Sinhala',
    'sk': 'Slovak', 'sl': 'Slovenian', 'so': 'Somali', 'es': 'Spanish', 'su': 'Sundanese', 'sw': 'Swahili',
    'sv': 'Swedish', 'tg': 'Tajik', 'ta': 'Tamil', 'tt': 'Tatar', 'te': 'Telugu', 'th': 'Thai', 'tr': 'Turkish',
    'tk': 'Turkmen', 'uk': 'Ukrainian', 'ur': 'Urdu', 'ug': 'Uyghur', 'uz': 'Uzbek', 'vi': 'Vietnamese',
    'cy': 'Welsh', 'xh': 'Xhosa', 'yi': 'Yiddish', 'yo': 'Yoruba', 'zu': 'Zulu'
}
SORTED_LANG_CODES = sorted(LANGUAGES.keys(), key=lambda k: LANGUAGES[k])

# --- የተጠቃሚ ሁኔታ መከታተያ ---
user_settings = {} # Stores {'target': 'en', 'mode': 'translate'}

# --- Groq API የትርጉም ተግባር ---
def translate_text_with_groq(text: str, target_lang: str) -> str:
    if not GROQ_API_KEY: return "Translation service is not configured."
    
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    target_language_name = LANGUAGES.get(target_lang, target_lang)
    system_prompt = f"You are an expert translator. Your task is to auto-detect the source language of the user's text and translate it to {target_language_name}. Provide only the translated text."
    user_prompt = f"Translate the following text to {target_language_name}: \"{text}\""

    payload = {"model": "llama3-70b-8192", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.2}

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
    if user_id not in user_settings:
        user_settings[user_id] = {'target': 'en'} # Default settings
    
    await update.message.reply_html(
        "Welcome! I am a powerful translator bot.\n\n"
        "I will automatically detect the language of your text and translate it to <b>English</b> by default.\n"
        "To change the target language, use the /set command.\n"
        "For help, use the /support command."
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = create_language_keyboard(0, 'target')
    await update.message.reply_text("Please select the target language (the language to translate TO):", reply_markup=keyboard)

def create_language_keyboard(page: int, action: str) -> InlineKeyboardMarkup:
    buttons, items_per_page = [], 20
    start_index, end_index = page * items_per_page, (page + 1) * items_per_page
    page_langs = SORTED_LANG_CODES[start_index:end_index]

    for i in range(0, len(page_langs), 2):
        row = [InlineKeyboardButton(f"{LANGUAGES[page_langs[i]]}", callback_data=f"{action}_{page_langs[i]}")]
        if i + 1 < len(page_langs):
            row.append(InlineKeyboardButton(f"{LANGUAGES[page_langs[i+1]]}", callback_data=f"{action}_{page_langs[i+1]}"))
        buttons.append(row)

    nav_row = []
    if page > 0: nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{action}_{page-1}"))
    if end_index < len(SORTED_LANG_CODES): nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{action}_{page+1}"))
    buttons.append(nav_row)
    
    return InlineKeyboardMarkup(buttons)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith('page_'):
        _, action, page_str = data.split('_')
        page = int(page_str)
        keyboard = create_language_keyboard(page, action)
        await query.edit_message_text(f"Please select the '{action.title()}' language (Page {page+1}):", reply_markup=keyboard)

    elif data.startswith('target_'):
        action, lang_code = data.split('_', 1)
        user_settings.setdefault(user_id, {})[action] = lang_code
        target = user_settings[user_id].get('target', 'en')
        await query.edit_message_text(
            f"Settings updated!\n\nI will now translate everything TO: <b>{LANGUAGES.get(target, target)}</b>.\n\nYou can now send text to translate.",
            parse_mode='HTML'
        )
    elif data == 'cancel_support':
        user_settings.setdefault(user_id, {})['mode'] = 'translate'
        await query.edit_message_text("Support session cancelled. You are now back in translation mode.")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_settings: await start(update, context)

    mode = user_settings.get(user_id, {}).get('mode', 'translate')

    if mode == 'support':
        if not ADMIN_ID:
            await update.message.reply_text("Support system is not configured by the admin.")
            return
        await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
        await update.message.reply_text("Your message has been sent to the administrator. They will reply to you here.")
    
    else: # mode == 'translate'
        settings = user_settings[user_id]
        target_lang = settings.get('target', 'en')
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        translated_text = translate_text_with_groq(update.message.text, 'auto', target_lang)
        await update.message.reply_text(translated_text)
    
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_settings.setdefault(user_id, {})['mode'] = 'support'
    keyboard = [[InlineKeyboardButton("🚫 Cancel", callback_data='cancel_support')]]
    await update.message.reply_html(
        "📞 You are now in direct contact with our Administrator.\n"
        "Send here any message you want to submit, you will receive the answer directly here in chat!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Admin Commands ---
async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if ADMIN_ID and user_id == ADMIN_ID:
        user_count = len(user_settings)
        await update.message.reply_text(f"📊 Bot Status:\n\nTotal unique users: {user_count}")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

async def broadcast_logic(context: ContextTypes.DEFAULT_TYPE, message_text: str = None, photo_id: str = None):
    """Helper function to perform the broadcast."""
    all_user_ids = list(user_settings.keys())
    sent_count, failed_count = 0, 0
    
    for chat_id in all_user_ids:
        try:
            if photo_id:
                await context.bot.send_photo(chat_id=chat_id, photo=photo_id, caption=message_text)
            elif message_text:
                await context.bot.send_message(chat_id=chat_id, text=message_text)
            sent_count += 1
            await asyncio.sleep(0.1) # To avoid hitting rate limits
        except Exception as e:
            logger.error(f"Failed to send broadcast to {chat_id}: {e}")
            failed_count += 1
    return sent_count, failed_count

async def admin_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if ADMIN_ID and user_id == ADMIN_ID:
        message_to_send = " ".join(context.args)
        if not message_to_send:
            await update.message.reply_text("Usage: /broadcast <your message>")
            return
        
        await update.message.reply_text(f"Starting text broadcast to {len(user_settings)} users...")
        sent, failed = await broadcast_logic(context, message_text=message_to_send)
        await update.message.reply_text(f"📢 Text Broadcast finished!\n\nSent: {sent}\nFailed: {failed}")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

async def admin_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if ADMIN_ID and user_id == ADMIN_ID:
        if not update.message.caption or not update.message.caption.startswith("/broadcast"):
            return # Ignore photos without the broadcast command

        message_to_send = update.message.caption.replace("/broadcast", "").strip()
        photo_id = update.message.photo[-1].file_id
        
        await update.message.reply_text(f"Starting photo broadcast to {len(user_settings)} users...")
        sent, failed = await broadcast_logic(context, message_text=message_to_send, photo_id=photo_id)
        await update.message.reply_text(f"🖼️ Photo Broadcast finished!\n\nSent: {sent}\nFailed: {failed}")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.reply_to_message and update.message.reply_to_message.forward_from:
        original_user_id = update.message.reply_to_message.forward_from.id
        await context.bot.send_message(chat_id=original_user_id, text=f"<b>Admin Reply:</b>\n{update.message.text}", parse_mode='HTML')
        await update.message.reply_text("Your reply has been sent to the user.")

# --- ዋናው የቴሌግራም አፕሊኬሽን ---
if not TELEGRAM_BOT_TOKEN: raise ValueError("BOT_TOKEN is not set!")
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("set", set_language))
application.add_handler(CommandHandler("support", support))
application.add_handler(CommandHandler("status", admin_status))
application.add_handler(CommandHandler("broadcast", admin_broadcast_text))
application.add_handler(CallbackQueryHandler(button_callback_handler))
# Admin handlers
application.add_handler(MessageHandler(filters.REPLY & filters.User(user_id=int(ADMIN_ID)) if ADMIN_ID else filters.NONE, handle_admin_reply))
application.add_handler(MessageHandler(filters.PHOTO & filters.User(user_id=int(ADMIN_ID)) if ADMIN_ID else filters.NONE, admin_broadcast_photo))
# General text handler (must be last)
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

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