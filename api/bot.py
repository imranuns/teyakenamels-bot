# -*- coding: utf-8 -*-
import os
import telegram
import json
import google.generativeai as genai
from flask import Flask, request

print("--- Cold Start: Loading function code ---")

# Flask app መጀመር
app = Flask(__name__)

# --- API Keys ማዘጋጀት ---
TELEGRAM_BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

print(f"BOT_TOKEN loaded: {bool(TELEGRAM_BOT_TOKEN)}")
print(f"GEMINI_API_KEY loaded: {bool(GEMINI_API_KEY)}")

# --- ሰርቪሶችን ማዘጋጀት ---
bot = None
model = None

try:
    if TELEGRAM_BOT_TOKEN:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        print("Telegram Bot initialized successfully.")
    else:
        print("ERROR: BOT_TOKEN environment variable not found.")
except Exception as e:
    print(f"ERROR initializing Telegram Bot: {e}")

try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("Google AI Model initialized successfully.")
    else:
        print("ERROR: GEMINI_API_KEY environment variable not found.")
except Exception as e:
    print(f"ERROR initializing Google AI Model: {e}")

# የተጠቃሚውን ሁኔታ መከታተያ
user_state = {}

def clean_json_from_text(text):
    try:
        start = text.index('{')
        end = text.rindex('}') + 1
        json_str = text[start:end]
        print(f"Cleaned JSON string: {json_str}")
        return json_str
    except ValueError:
        print("ERROR: Could not find JSON object in AI response.")
        return None

@app.route('/', methods=['POST'])
def respond():
    print("\n--- New Request Received ---")
    if not bot or not model:
        print("CRITICAL ERROR: Bot or AI Model is not initialized. Aborting request.")
        return "ok"

    try:
        request_data = request.get_json(force=True)
        print(f"Incoming request data: {request_data}")
        update = telegram.Update.de_json(request_data, bot)

        if not (update.message and update.message.text):
            print("Request is not a text message. Ignoring.")
            return "ok"

        chat_id = update.message.chat.id
        msg_text = update.message.text.strip()
        print(f"Received message from chat_id {chat_id}: '{msg_text}'")

        if msg_text.lower() == '/start':
            print("Handling /start command.")
            bot.send_message(chat_id=chat_id, text="Welcome to the AI English Learning Bot!\nTo get a new question, type /quiz")

        elif msg_text.lower() == '/quiz':
            print("Handling /quiz command.")
            bot.send_message(chat_id=chat_id, text="Generating a new question from AI... 🧠")
            
            prompt = "Create a simple English quiz question for an Amharic speaker learning English. The question can be about vocabulary, translation, or simple grammar. Return the response ONLY as a JSON object with two keys: \"question\" and \"answer\". Example: {\"question\": \"What is the English word for 'ውሃ'?\", \"answer\": \"Water\"}"
            print("Sending prompt to AI...")
            
            try:
                response = model.generate_content(prompt)
                print(f"Raw response from AI: {response.text}")
                
                cleaned_json_str = clean_json_from_text(response.text)
                
                if cleaned_json_str:
                    quiz_data = json.loads(cleaned_json_str)
                    question = quiz_data.get("question")
                    answer = quiz_data.get("answer")

                    if question and answer:
                        print(f"Generated question: '{question}', Answer: '{answer}'")
                        user_state[chat_id] = answer
                        bot.send_message(chat_id=chat_id, text=question)
                    else:
                        print("ERROR: AI response JSON is missing 'question' or 'answer'.")
                        bot.send_message(chat_id=chat_id, text="Sorry, the AI returned an incomplete response. Please try again.")
                else:
                    bot.send_message(chat_id=chat_id, text="Sorry, I couldn't understand the AI's response. Please try again.")

            except Exception as ai_error:
                print(f"CRITICAL AI Error during generation: {ai_error}")
                bot.send_message(chat_id=chat_id, text="An error occurred with the AI service. Please try again later.")

        else:
            print("Handling a potential answer.")
            if chat_id in user_state:
                correct_answer = user_state[chat_id]
                print(f"Checking user answer '{msg_text}' against correct answer '{correct_answer}'.")
                if msg_text.lower() == correct_answer.lower():
                    bot.send_message(chat_id=chat_id, text="✅ Correct! Well done! Type /quiz for the next question.")
                else:
                    bot.send_message(chat_id=chat_id, text=f"❌ Incorrect! The correct answer was '{correct_answer}'.\nType /quiz for the next question.")
                del user_state[chat_id]
            else:
                print("User sent text, but no question is pending.")
                bot.send_message(chat_id=chat_id, text="I don't understand. Please type /quiz to start.")

    except Exception as e:
        print(f"CRITICAL General Error in respond() function: {e}")

    print("--- Request Finished ---")
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    print("Attempting to set webhook...")
    if bot:
        VERCEL_URL = f"https://{request.host}"
        print(f"Setting webhook to: {VERCEL_URL}")
        webhook = bot.set_webhook(f'{VERCEL_URL}/')
        if webhook:
            print("Webhook setup successful.")
            return "Webhook setup ok"
        else:
            print("Webhook setup failed.")
            return "Webhook setup failed"
    print("Cannot set webhook, bot not initialized.")
    return "Bot not initialized"