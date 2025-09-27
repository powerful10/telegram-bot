import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# .env fayldan tokenni olish
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Savollarni o‘qish
with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# Foydalanuvchi holatini saqlash uchun
user_data = {}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"score": 0, "current_q": 0}
    await update.message.reply_text("Salom! 🖐 Quiz boshlash uchun /quiz yozing.")

# /quiz komandasi
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"score": 0, "current_q": 0}
    await ask_question(update, context, user_id)

# Savolni chiqarish
async def ask_question(update, context, user_id):
    q_index = user_data[user_id]["current_q"]
    if q_index < len(questions):
        q = questions[q_index]
        keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in q["options"]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(q["question"], reply_markup=reply_markup)
        else:
            await update.callback_query.message.reply_text(q["question"], reply_markup=reply_markup)
    else:
        score = user_data[user_id]["score"]
        await update.callback_query.message.reply_text(f"🏆 Quiz tugadi! Sizning natijangiz: {score}/{len(questions)}")

# Javoblarni tekshirish
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    q_index = user_data[user_id]["current_q"]
    q = questions[q_index]

    if query.data == q["answer"]:
        user_data[user_id]["score"] += 1
        await query.edit_message_text(f"✅ To‘g‘ri javob: {q['answer']}")
    else:
        await query.edit_message_text(f"❌ Noto‘g‘ri. To‘g‘ri javob: {q['answer']}")

    user_data[user_id]["current_q"] += 1
    await ask_question(update, context, user_id)

# Asosiy app
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()