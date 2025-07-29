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
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# የተጠቃሚውን ሁኔታ መከታተያ
user_state = {}

@app.route('/', methods=['POST'])
def respond():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            msg_text = update.message.text.strip()

            # ለ /start ኮማንድ ምላሽ መስጠት
            if msg_text.lower() == '/start':
                bot.send_message(chat_id=chat_id, text="Welcome to the AI English Learning Bot!\nTo get a new question, type /quiz")
            
            # ለ /quiz ኮማንድ ምላሽ መስጠት
            elif msg_text.lower() == '/quiz':
                # ለተጠቃሚው ጥያቄ እየተዘጋጀ መሆኑን ማሳወቅ
                bot.send_message(chat_id=chat_id, text="Generating a new question from AI... 🧠")
                
                # ለ AI የምንልከው ጥያቄ (Prompt)
                prompt = """
                Create a simple English quiz question for an Amharic speaker learning English.
                The question can be about vocabulary, translation, or simple grammar.
                Return the response ONLY as a JSON object with two keys: "question" and "answer".
                Example: {"question": "What is the English word for 'ውሃ'?", "answer": "Water"}
                """
                
                try:
                    # ከ AI ምላሽ መጠበቅ
                    response = model.generate_content(prompt)
                    
                    # የ AI ምላሽን ወደ JSON መቀየር
                    quiz_data = json.loads(response.text)
                    question = quiz_data.get("question")
                    answer = quiz_data.get("answer")

                    if question and answer:
                        # ትክክለኛውን መልስ ለዚህ ተጠቃሚ ማስታወሻ መያዝ
                        user_state[chat_id] = answer
                        # ጥያቄውን ለተጠቃሚው መላክ
                        bot.send_message(chat_id=chat_id, text=question)
                    else:
                        bot.send_message(chat_id=chat_id, text="Sorry, I couldn't generate a question right now. Please try again.")

                except Exception as ai_error:
                    print(f"AI Error: {ai_error}")
                    bot.send_message(chat_id=chat_id, text="An error occurred with the AI service. Please try again later.")

            # ለሌሎች መልዕክቶች (ለመልሶች) ምላሽ መስጠት
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
    VERCEL_URL = f"https://{request.host}"
    webhook = bot.set_webhook(f'{VERCEL_URL}/')
    if webhook:
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"
