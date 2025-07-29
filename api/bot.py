# -*- coding: utf-8 -*-
import os
import telegram
import random
from flask import Flask, request

# Flask app መጀመር
app = Flask(__name__)

# የቴሌግራም ቶክን ከ Vercel Environment Variable መውሰድ
TOKEN = os.environ.get('BOT_TOKEN')
bot = telegram.Bot(token=TOKEN)

# የጥያቄና መልስ ዳታቤዝ (ለጊዜው)
QUESTIONS = {
    "የኢትዮጵያ ዋና ከተማ ማን ትባላለች?": "አዲስ አበባ",
    "በአለም ላይ ትልቁ ውቅያኖስ የትኛው ነው?": "ፓሲፊክ",
    "የአለማችን ረጅሙ ወንዝ ማን ይባላል?": "አባይ"
}

# የተጠቃሚውን ሁኔታ መከታተያ (ለጊዜው)
# የትኛው ተጠቃሚ የትኛውን ጥያቄ እየመለሰ እንደሆነ ለማወቅ
user_state = {}

@app.route('/', methods=['POST'])
def respond():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            msg_text = update.message.text.strip()

            # ለ /start ኮማንድ ምላሽ መስጠት
            if msg_text == '/start':
                bot.send_message(chat_id=chat_id, text="ሰላም! ወደ ጥያቄና መልስ ቦት እንኳን በደህና መጡ።\nጥያቄ ለመጀመር /quiz ብለው ይላኩ።")
            
            # ለ /quiz ኮማንድ ምላሽ መስጠት
            elif msg_text == '/quiz':
                # በዘፈቀደ አንድ ጥያቄ መምረጥ
                question = random.choice(list(QUESTIONS.keys()))
                # ትክክለኛውን መልስ ለዚህ ተጠቃሚ ማስታወሻ መያዝ
                user_state[chat_id] = QUESTIONS[question]
                
                bot.send_message(chat_id=chat_id, text=question)

            # ለሌሎች መልዕክቶች (ለመልሶች) ምላሽ መስጠት
            else:
                # ተጠቃሚው ጥያቄ እየመለሰ ከሆነ ማረጋገጥ
                if chat_id in user_state:
                    correct_answer = user_state[chat_id]
                    # የተጠቃሚውን መልስ ከትክክለኛው ጋር ማወዳደር
                    if msg_text.lower() == correct_answer.lower():
                        bot.send_message(chat_id=chat_id, text="✅ ትክክል ነው! ጎበዝ!")
                    else:
                        bot.send_message(chat_id=chat_id, text=f"❌ ስህተት ነው! ትክክለኛው መልስ '{correct_answer}' ነበር።")
                    
                    # ጥያቄውን ስለመለሰ ከማስታወሻው ላይ ማስወገድ
                    del user_state[chat_id]
                else:
                    bot.send_message(chat_id=chat_id, text="ምን ማለት እንደፈለጉ አልገባኝም። ጥያቄ ለመጀመር /quiz ብለው ይላኩ።")

    except Exception as e:
        print(f"ERROR: {e}")

    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    VERCEL_URL = f"https://{request.host}"
    webhook = bot.set_webhook(f'{VERCEL_URL}/')
    if webhook:
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"
