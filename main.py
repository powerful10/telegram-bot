import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import random

# .env fayldan tokenni olish
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Savollarni o‘qish (kategoriyalar bilan)
with open("questions.json", "r", encoding="utf-8") as f:
    questions_by_category = json.load(f)

# Leaderboard uchun fayl
SCORES_FILE = "scores.json"

if not os.path.exists(SCORES_FILE):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

# Foydalanuvchi holatini saqlash uchun
user_data = {}

# JSONdan leaderboardni o‘qish
def load_scores():
    with open(SCORES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# JSONga leaderboardni yozish
def save_scores(scores):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=4, ensure_ascii=False)

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_data[user_id] = {"score": 0, "current_q": 0, "order": [], "category": None}
    await update.message.reply_text(
        f"Salom, {user_name}! 👋\n\n"
        "🚀 Bu bot orqali dasturlash bo‘yicha quiz o‘ynashingiz mumkin!\n"
        "Quizni boshlash uchun /quiz buyrug‘ini bosing.\n\n"
        "📊 Reyting jadvalini ko‘rish uchun /leaderboard buyrug‘ini bosing."
    )

# /quiz komandasi — kategoriya tanlash
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in questions_by_category.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📂 Iltimos, kategoriya tanlang:", reply_markup=reply_markup)

# Savolni chiqarish
async def ask_question(update, context, user_id):
    q_index = user_data[user_id]["current_q"]
    order = user_data[user_id]["order"]
    category = user_data[user_id]["category"]

    if q_index < len(order):
        q = questions_by_category[category][order[q_index]]
        keyboard = [
            [InlineKeyboardButton(f"🔹 {opt}", callback_data=opt)]
            for opt in q["options"]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        progress = f"📊 Savol {q_index+1}/{len(order)}"

        if update.message:
            await update.message.reply_text(f"{progress}\n\n❓ {q['question']}", reply_markup=reply_markup)
        else:
            await update.callback_query.message.reply_text(f"{progress}\n\n❓ {q['question']}", reply_markup=reply_markup)
    else:
        score = user_data[user_id]["score"]
        total = len(order)

        # Natija baholash
        if score <= total // 3:
            feedback = "😅 Yana mashq qilish kerak!"
        elif score <= (2 * total) // 3:
            feedback = "👍 Yaxshi natija!"
        else:
            feedback = "🏆 Zo‘r! Siz pro dasturchisiz!"

        # Reytingni yangilash
        scores = load_scores()
        user_name = update.effective_user.first_name
        prev_best = scores.get(str(user_id), {"name": user_name, "best": 0})["best"]

        if score > prev_best:
            scores[str(user_id)] = {"name": user_name, "best": score}
            save_scores(scores)

        await update.callback_query.message.reply_text(
            f"✅ Quiz tugadi!\n\nSizning natijangiz: {score}/{total}\n{feedback}\n\n"
            "📊 Reytingni ko‘rish uchun /leaderboard ni bosing."
        )

# Javoblarni tekshirish va kategoriya tanlash
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Agar kategoriya tanlansa
    if query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        order = list(range(len(questions_by_category[category])))
        random.shuffle(order)
        user_data[user_id] = {"score": 0, "current_q": 0, "order": order, "category": category}
        await query.edit_message_text(f"✅ {category} tanlandi!\nQuiz boshlanmoqda...")
        await ask_question(update, context, user_id)
        return

    # Oddiy savolga javob bo‘lsa
    q_index = user_data[user_id]["current_q"]
    order = user_data[user_id]["order"]
    category = user_data[user_id]["category"]
    q = questions_by_category[category][order[q_index]]

    if query.data == q["answer"]:
        user_data[user_id]["score"] += 1
        await query.edit_message_text(f"✅ To‘g‘ri javob: {q['answer']}")
    else:
        await query.edit_message_text(f"❌ Noto‘g‘ri. To‘g‘ri javob: {q['answer']}")

    user_data[user_id]["current_q"] += 1
    await ask_question(update, context, user_id)

# /leaderboard komandasi
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = load_scores()
    if not scores:
        await update.message.reply_text("📊 Hozircha reyting bo‘sh.")
        return

    # Eng yaxshi 10 foydalanuvchini chiqarish
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]["best"], reverse=True)[:10]
    text = "🏆 Reyting jadvali:\n\n"
    for i, (user_id, info) in enumerate(sorted_scores, start=1):
        text += f"{i}. {info['name']} — {info['best']} ball\n"

    await update.message.reply_text(text)

# ---- HTTP server (Render health check) ----
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_http_server():
    port = int(os.environ.get("PORT", 10000))  # Render assigns $PORT
    server = HTTPServer(("", port), HealthHandler)
    print(f"✅ Health check server started on port {port}")
    server.serve_forever()

# Asosiy app
def main():
    # Start HTTP server in background thread
    threading.Thread(target=run_http_server, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
