import sqlite3
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== DATABASE =====
conn = sqlite3.connect("money.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    thu INTEGER,
    chi INTEGER,
    date TEXT
)
""")
conn.commit()

# ===== STATE =====
user_state = {}

# ===== TIME =====
def get_day():
    return datetime.now().strftime("%d/%m/%Y")

def get_time():
    return datetime.now().strftime("%H:%M")

# ===== FORMAT TIỀN =====
def fm(money):
    return f"{money:,}".replace(",", ".") + " VND"

# ===== MENU =====
def menu():
    keyboard = [
        ["📊 Hôm nay", "📅 Tháng"],
        ["✏️ Sửa chi/tiêu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== STATS =====
def get_stats(user_id, day):
    cursor.execute(
        "SELECT thu, chi FROM data WHERE user_id=? AND date=?",
        (user_id, day)
    )
    rows = cursor.fetchall()

    total_thu = 0
    total_chi = 0
    total_loi = 0

    for thu, chi in rows:
        total_thu += thu
        total_chi += chi
        total_loi += (thu - chi)

    return total_thu, total_chi, total_loi

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """🤖 BOT QUẢN LÝ TIỀN

👉 Gửi: 5000-1000
(Thu - Chi)

Ví dụ:
10000-2000
"""
    await update.message.reply_text(msg, reply_markup=menu())

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    day = get_day()
    chat_id = update.message.chat_id

    if text == "📊 Hôm nay":
        thu, chi, loi = get_stats(chat_id, day)

        msg = f"""📊 Hôm nay
💰 +{fm(thu)}
💸 -{fm(chi)}
💎 +{fm(loi)}

📈 Tổng lời ngày {day}: {fm(loi)}"""
        await update.message.reply_text(msg, reply_markup=menu())
        return

    if text == "📅 Tháng":
        cursor.execute(
            "SELECT date FROM data WHERE user_id=? GROUP BY date",
            (chat_id,)
        )
        days = cursor.fetchall()

        total = 0
        msg = "📅 THÁNG:\n"

        for d in days:
            d = d[0]
            thu, chi, loi = get_stats(chat_id, d)
            total += loi
            msg += f"\n{d} → 💎 {fm(loi)}"

        msg += f"\n\n💎 Tổng: {fm(total)}"

        await update.message.reply_text(msg, reply_markup=menu())
        return

    if text == "✏️ Sửa chi/tiêu":
        user_state[chat_id] = "edit"
        await update.message.reply_text(
            "✏️ Nhập lại dạng: 5000-1000 (ghi đè hôm nay)",
            reply_markup=menu()
        )
        return

    if "-" in text:
        try:
            thu, chi = map(int, text.split("-"))

            if user_state.get(chat_id) == "edit":
                cursor.execute(
                    "DELETE FROM data WHERE user_id=? AND date=?",
                    (chat_id, day)
                )
                user_state[chat_id] = None

            cursor.execute(
                "INSERT INTO data (user_id, thu, chi, date) VALUES (?, ?, ?, ?)",
                (chat_id, thu, chi, day)
            )
            conn.commit()

            t_thu, t_chi, total_loi = get_stats(chat_id, day)
            loi_lenh = thu - chi

            msg = f"""🌾 Lúa Về Đại Nhân ƠI
⏰ {day} - {get_time()}

💰 +{fm(thu)}   ( vừa nhận )
💸 -{fm(chi)}   ( vừa chi )
💎 +{fm(loi_lenh)}   ( lời )

📊 Hôm nay:
💰 Tổng nhận: {fm(t_thu)}
💸 Tổng chi : {fm(t_chi)}

📈 Tổng lời ngày {day}: {fm(total_loi)}
"""
            await update.message.reply_text(msg, reply_markup=menu())

        except:
            await update.message.reply_text(
                "❌ Nhập đúng dạng: 5000-1000",
                reply_markup=menu()
            )

# ===== RUN (SỬA CHO RENDER) =====
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ Chưa set TOKEN trên Render!")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

print("Bot đang chạy...")
app.run_polling()