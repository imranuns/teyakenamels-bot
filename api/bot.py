# -*- coding: utf-8 -*-
import os
import telegram
from flask import Flask, request

# Flask app መጀመር
app = Flask(__name__)

# የቴሌግራም ቶክን ከ Vercel Environment Variable መውሰድ
# Vercel ላይ ስናሰማራ እናስገባዋለን
TOKEN = os.environ.get('BOT_TOKEN')
bot = telegram.Bot(token=TOKEN)

# ይህ ፋንክሽን የሚጠራው ቴሌግራም መልዕክት ሲልክልን ነው
@app.route('/', methods=['POST'])
def respond():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message and update.message.text:
        chat_id = update.message.chat.id
        msg_text = update.message.text

        # ለ /start ኮማንድ ምላሽ መስጠት
        if msg_text == '/start':
            bot.send_message(chat_id=chat_id, text="ሰላም! ወደ ጥያቄና መልስ ቦት እንኳን በደህና መጡ።")
        else:
            # ለሌሎች መልዕክቶች ምላሽ መስጠት
            bot.send_message(chat_id=chat_id, text=f"የላኩት መልዕክት '{msg_text}' ደርሶኛል።")

    return 'ok'

# ይህ ፋንክሽን የቦቱን Webhook ለማዘጋጀት ነው
# ቦቱ ከተሰማራ በኋላ አንድ ጊዜ ብቻ ነው የምንጠቀመው
@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    # የ Vercel deployment URL
    # ይህንን URL Vercel ከሰጠን በኋላ እናስተካክለዋለን
    VERCEL_URL = f"https://{request.host}"
    
    # ለቴሌግራም የኛን URL መንገር
    webhook = bot.set_webhook(f'{VERCEL_URL}/')
    
    if webhook:
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"

# ይህ ኮድ በቀጥታ ስናሄደው እንዳይሰራ (ለ Vercel ብቻ እንዲሆን)
if __name__ != '__main__':
    # Flask app ን ለ Vercel ማዘጋጀት
    app.run(debug=True)
