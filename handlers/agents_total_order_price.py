(
    ZAKAZ_HISOBOT_ACTION,
    ZAKAZ_HISOBOT_DATE,
    ZAKAZ_HISOBOT_START_DATE,
    ZAKAZ_HISOBOT_END_DATE,

    AGENT_EARNINGS_ACTION,
    AGENT_EARNINGS_DATE,
    AGENT_EARNINGS_START_DATE,
    AGENT_EARNINGS_END_DATE
) = range(8)


from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ConversationHandler, MessageHandler, filters, ContextTypes

from handlers.admin_menu import admin_menu
from config import API_URL

import requests
def get_agent_earnings_today(telegram_id):
    r = requests.get(
        f"{API_URL}/agents/earnings",
        params={"today_only": "true"},   # 👈 fix here
        headers={"x-telegram-id": str(telegram_id)}
    )
    return r.json()


def get_agent_earnings_by_date(telegram_id, date_str):
    d, m, y = date_str.split("-")
    iso_date = f"{y}-{m}-{d}"
    r = requests.get(
        f"{API_URL}/agents/earnings",
        params={"which_day": iso_date},
        headers={"x-telegram-id": str(telegram_id)}
    )
    return r.json()


def get_agent_earnings_between(telegram_id, start_str, end_str):
    d1, m1, y1 = start_str.split("-")
    d2, m2, y2 = end_str.split("-")
    start_iso = f"{y1}-{m1}-{d1}"
    end_iso = f"{y2}-{m2}-{d2}"
    r = requests.get(
        f"{API_URL}/agents/earnings",
        params={"start_date": start_iso, "end_date": end_iso},
        headers={"x-telegram-id": str(telegram_id)}
    )
    return r.json()

# 👉 Step 1: show options
async def agent_earnings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        ["📆 Bugun", "📅 Sana"],
        ["📊 Oraliqdagi sana"],
        ["⬅️ Ortga"]
    ]
    await update.message.reply_text(
        "💵 Agent daromadlarini qaysi oraliq bo‘yicha ko‘rasiz?",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return AGENT_EARNINGS_ACTION


# 👉 Step 2: action selection
async def agent_earnings_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "⬅️ Ortga":
        return await admin_menu(update, context)

    if text == "📆 Bugun":
        data = get_agent_earnings_today(update.effective_user.id)
        message = format_earnings_message(data, "📆 Bugun")
        await update.message.reply_text(message, parse_mode="HTML")

        # Keep conversation alive to allow choosing another option
        buttons = [
            ["📆 Bugun", "📅 Sana"],
            ["📊 Oraliqdagi sana"],
            ["⬅️ Ortga"]
        ]
        await update.message.reply_text(
            "💵 Yana biror oraliqni tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return AGENT_EARNINGS_ACTION


    if text == "📅 Sana":
        await update.message.reply_text("📅 Sanani kiriting (masalan: 12-10-2025):")
        return AGENT_EARNINGS_DATE

    if text == "📊 Oraliqdagi sana":
        await update.message.reply_text("⏳ Boshlanish sanasini kiriting (masalan: 01-10-2025):")
        return AGENT_EARNINGS_START_DATE


# 👉 Step 3: specific date
async def agent_earnings_by_date(update, context):
    date_str = update.message.text.strip()
    data = get_agent_earnings_by_date(update.effective_user.id, date_str)
    message = format_earnings_message(data, f"📅 {date_str}")
    await update.message.reply_text(message, parse_mode="HTML")

    # keep conversation alive
    buttons = [
        ["📆 Bugun", "📅 Sana"],
        ["📊 Oraliqdagi sana"],
        ["⬅️ Ortga"]
    ]
    await update.message.reply_text(
        "💵 Yana biror oraliqni tanlang:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return AGENT_EARNINGS_ACTION



# 👉 Step 4: start date
async def agent_earnings_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["start_date"] = update.message.text.strip()
    await update.message.reply_text("📅 Tugash sanasini kiriting (masalan: 12-10-2025):")
    return AGENT_EARNINGS_END_DATE


# 👉 Step 5: end date
async def agent_earnings_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    end_date = update.message.text.strip()
    start_date = context.user_data.get("start_date")
    data = get_agent_earnings_between(update.effective_user.id, start_date, end_date)
    message = format_earnings_message(data, f"📊 {start_date} - {end_date}")
    await update.message.reply_text(message, parse_mode="HTML")

    # Keep the conversation alive for new selections
    buttons = [
        ["📆 Bugun", "📅 Sana"],
        ["📊 Oraliqdagi sana"],
        ["⬅️ Ortga"]
    ]
    await update.message.reply_text(
        "💵 Yana biror oraliqni tanlang:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return AGENT_EARNINGS_ACTION



# 🧾 Helper to format output
def format_earnings_message(data, title):
    if "results" not in data or not data["results"]:
        return f"{title}\n❌ Hech qanday daromad topilmadi."

    lines = [f"💵 <b>{title}</b>\n"]
    for row in data["results"]:
        earnings = f"{int(row['earnings']):,}".replace(",", " ")
        lines.append(f"👤 {row['full_name']} ({row['role']}) — 💰 {earnings} so‘m")
    return "\n".join(lines)

from .main_menu import main_menu
async def agent_earnings_go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔙 Bosh menyuga qaytdingiz.")
    await main_menu(update, context)
    return ConversationHandler.END

# 👉 Conversation handler
agent_earnings_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^💵 Agent daromadlari$"), agent_earnings_start)],
    states={
        AGENT_EARNINGS_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, agent_earnings_action)],
        AGENT_EARNINGS_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agent_earnings_by_date)],
        AGENT_EARNINGS_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agent_earnings_start_date)],
        AGENT_EARNINGS_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agent_earnings_end_date)],
    },
    fallbacks=[MessageHandler(filters.Regex("^⬅️ Ortga$"), agent_earnings_go_back)],
    allow_reentry=True
)
