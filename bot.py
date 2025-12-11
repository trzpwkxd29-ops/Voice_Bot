import os
import sqlite3
import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext

# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_KEY")
openai.api_key = OPENAI_KEY

updater = Updater(token=BOT_TOKEN, use_context=True)
dp = updater.dispatcher

# Database
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, usage_count INTEGER)''')
conn.commit()

# Female voice options
FEMALE_VOICES = {"1":"alloy","2":"aria","3":"bella","4":"clara"}

# Start command
def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("Join Group First", url="https://t.me/YOUR_GROUP_LINK")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome! Please join our group first.", reply_markup=reply_markup)

# Show voice options
def voices(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Voice 1", callback_data='1')],
        [InlineKeyboardButton("Voice 2", callback_data='2')],
        [InlineKeyboardButton("Voice 3", callback_data='3')],
        [InlineKeyboardButton("Voice 4", callback_data='4')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a female voice (Free trial 4 uses):", reply_markup=reply_markup)

# Handle button clicks
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id

    # Check usage
    c.execute("SELECT usage_count FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    if result is None:
        c.execute("INSERT INTO users (user_id, usage_count) VALUES (?,?)", (user_id,0))
        conn.commit()
        usage_count=0
    else:
        usage_count = result[0]

    if usage_count >= 4:
        query.edit_message_text("Free trial finished.\n1 day: ₹25\n1 week: ₹165\n1 month: ₹700\nUPI: 9864576845@fam")
        return

    context.user_data["chosen_voice"] = FEMALE_VOICES[query.data]
    query.edit_message_text("Send me your voice now, I will convert it into your chosen female voice.")

# Handle user voice
def voice_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    chosen_voice = context.user_data.get("chosen_voice")
    if not chosen_voice:
        update.message.reply_text("Please choose a female voice first using /voices")
        return

    file = update.message.voice.get_file()
    file.download("user_voice.ogg")

    # Convert with OpenAI TTS
    with open("user_voice.ogg", "rb") as f:
        audio_input = f.read()

    response = openai.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=chosen_voice,
        input="Your uploaded audio"
    )

    output_file = f"converted_{user_id}.mp3"
    with open(output_file, "wb") as f:
        f.write(response)

    update.message.reply_audio(audio=open(output_file, "rb"))

    # Update usage
    c.execute("UPDATE users SET usage_count = usage_count + 1 WHERE user_id=?", (user_id,))
    conn.commit()

# Handlers
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("voices", voices))
dp.add_handler(CallbackQueryHandler(button))
dp.add_handler(MessageHandler(Filters.voice, voice_handler))

# Run bot
updater.start_polling()
updater.idle()
