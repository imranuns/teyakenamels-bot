# -*- coding: utf-8 -*-
import os
import telegram
import json
import google.generativeai as genai
from flask import Flask, request

# Flask app መጀመር
app = Flask(__name__)

# --- API Keys ማዘጋጀት ---
TELEGRAM_BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- ሰርቪሶችን ማዘጋጀት ---
bot = None
model = None

# API ቁልፎቹ በትክክል መኖራቸውን ማረጋገጥ
if TELEGRAM_BOT_TOKEN:
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
else:
    print("ERROR: BOT_TOKEN environment variable not found.")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("ERROR: GEMINI_API_KEY environment variable not found.")

# የተጠቃሚውን ሁኔታ መከታተያ
user_state = {}

def clean_json_from_text(text):
    """Extracts a JSON object from a string, even if it's embedded in other text."""
    try:
        start = text.index('{')
        end = text.rindex('}') + 1
        return text[start:end]
    except ValueError:
        return None

@app.route('/', methods=['POST'])
def respond():
    # ቦቱ ወይም ሞዴሉ ካልተዘጋጀ እንዳይቀጥል ማድረግ
    if not bot or not model:
        print("ERROR: Bot or AI Model is not initialized due to missing API keys.")
        return "ok"

    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            msg_text = update.message.text.strip()

            if msg_text.lower() == '/start':
                bot.send_message(chat_id=chat_id, text="Welcome to the AI English Learning Bot!\nTo get a new question, type /quiz")
            
            elif msg_text.lower() == '/quiz':
                bot.send_message(chat_id=chat_id, text="Generating a new question from AI... 🧠")
                
                prompt = """
                Create a simple English quiz question for an Amharic speaker learning English.
                The question can be about vocabulary, translation, or simple grammar.
                Return the response ONLY as a JSON object with two keys: "question" and "answer".
                Example: {"question": "What is the English word for 'ውሃ'?", "answer": "Water"}
                """
                
                try:
                    response = model.generate_content(prompt)
                    
                    cleaned_json_str = clean_json_from_text(response.text)
                    
                    if cleaned_json_str:
                        quiz_data = json.loads(cleaned_json_str)
                        question = quiz_data.get("question")
                        answer = quiz_data.get("answer")

                        if question and answer:
                            user_state[chat_id] = answer
                            bot.send_message(chat_id=chat_id, text=question)
                        else:
                            bot.send_message(chat_id=chat_id, text="Sorry, the AI returned an incomplete response. Please try again.")
                    else:
                        print(f"AI returned non-JSON response: {response.text}")
                        bot.send_message(chat_id=chat_id, text="Sorry, I couldn't understand the AI's response. Please try again.")

                except Exception as ai_error:
                    print(f"AI Error: {ai_error}")
                    bot.send_message(chat_id=chat_id, text="An error occurred with the AI service. Please try again later.")

            else:
                if chat_id in user_state:
                    correct_answer = user_state[chat_id]
                    if msg_text.lower() == correct_answer.lower():
                        bot.send_message(chat_id=chat_id, text="✅ Correct! Well done! Type /quiz for the next question.")
                    else:
                        bot.send_message(chat_id=chat_id, text=f"❌ Incorrect! The correct answer was '{correct_answer}'.\nType /quiz for the next question.")
                    del user_state[chat_id]
                else:
                    bot.send_message(chat_id=chat_id, text="I don't understand. Please type /quiz to start.")

    except Exception as e:
        print(f"General Error: {e}")

    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    if bot:
        VERCEL_URL = f"https://{request.host}"
        webhook = bot.set_webhook(f'{VERCEL_URL}/')
        if webhook:
            return "Webhook setup ok"
        else:
            return "Webhook setup failed"
    return "Bot not initialized"