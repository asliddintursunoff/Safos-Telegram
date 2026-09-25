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
from services.api import get_agents_earnings
from datetime import datetime


def _to_iso(date_str):
    """dd-mm-yyyy -> yyyy-mm-dd, or None if the text is not a valid date."""
    try:
        return datetime.strptime((date_str or "").strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def get_agent_earnings_today(telegram_id):
    return get_agents_earnings(telegram_id, today_only="true")


def get_agent_earnings_by_date(telegram_id, date_str):
    return get_agents_earnings(telegram_id, which_day=_to_iso(date_str))


def get_agent_earnings_between(telegram_id, start_str, end_str):
    # end date is inclusive (whole last day)
    return get_agents_earnings(telegram_id, start_date=f"{_to_iso(start_str)}T00:00:00", end_date=f"{_to_iso(end_str)}T23:59:59")

# 👉 Step 1: show options
async def agent_earnings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        ["📆 Bugun", "📅 Sana"],
        ["📊 Oraliqdagi sana"],
        ["⬅️ Admin menyu"]
    ]
    await update.message.reply_text(
        "💵 Agent daromadlarini qaysi oraliq bo‘yicha ko‘rasiz?",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return AGENT_EARNINGS_ACTION


# 👉 Step 2: action selection
async def agent_earnings_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "⬅️ Admin menyu":
        return await agent_earnings_go_back(update, context)


    if text == "📆 Bugun":
        data = get_agent_earnings_today(update.effective_user.id)
        message = format_earnings_message(data, "📆 Bugun")
        await update.message.reply_text(message, parse_mode="HTML")

        # Keep conversation alive to allow choosing another option
        buttons = [
            ["📆 Bugun", "📅 Sana"],
            ["📊 Oraliqdagi sana"],
            ["⬅️ Admin menyu"]
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
    if not _to_iso(date_str):
        await update.message.reply_text("❌ Sana noto‘g‘ri formatda. Masalan: 12-10-2025")
        return AGENT_EARNINGS_DATE
    data = get_agent_earnings_by_date(update.effective_user.id, date_str)
    message = format_earnings_message(data, f"📅 {date_str}")
    await update.message.reply_text(message, parse_mode="HTML")

    # keep conversation alive
    buttons = [
        ["📆 Bugun", "📅 Sana"],
        ["📊 Oraliqdagi sana"],
        ["⬅️ Admin menyu"]
    ]
    await update.message.reply_text(
        "💵 Yana biror oraliqni tanlang:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return AGENT_EARNINGS_ACTION



# 👉 Step 4: start date
async def agent_earnings_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _to_iso(update.message.text):
        await update.message.reply_text("❌ Sana noto‘g‘ri formatda. Masalan: 01-10-2025")
        return AGENT_EARNINGS_START_DATE
    context.user_data["start_date"] = update.message.text.strip()
    await update.message.reply_text("📅 Tugash sanasini kiriting (masalan: 12-10-2025):")
    return AGENT_EARNINGS_END_DATE


# 👉 Step 5: end date
async def agent_earnings_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    end_date = update.message.text.strip()
    start_date = context.user_data.get("start_date")
    if not _to_iso(end_date):
        await update.message.reply_text("❌ Sana noto‘g‘ri formatda. Masalan: 12-10-2025")
        return AGENT_EARNINGS_END_DATE
    if not _to_iso(start_date):
        await update.message.reply_text("⏳ Boshlanish sanasini kiriting (masalan: 01-10-2025):")
        return AGENT_EARNINGS_START_DATE
    data = get_agent_earnings_between(update.effective_user.id, start_date, end_date)
    message = format_earnings_message(data, f"📊 {start_date} - {end_date}")
    await update.message.reply_text(message, parse_mode="HTML")

    # Keep the conversation alive for new selections
    buttons = [
        ["📆 Bugun", "📅 Sana"],
        ["📊 Oraliqdagi sana"],
        ["⬅️ Admin menyu"]
    ]
    await update.message.reply_text(
        "💵 Yana biror oraliqni tanlang:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return AGENT_EARNINGS_ACTION



# 🧾 Helper to format output
def format_earnings_message(data, title):
    if not isinstance(data, dict) or not data.get("results"):
        return f"{title}\n❌ Hech qanday daromad topilmadi."

    lines = [f"💵 <b>{title}</b>\n"]
    for row in data["results"]:
        earnings = f"{int(row.get('earnings') or 0):,}".replace(",", " ")
        lines.append(f"👤 {row['full_name']} ({row['role']}) — 💰 {earnings} so‘m")
    return "\n".join(lines)

from .main_menu import main_menu
from telegram import ReplyKeyboardRemove

async def agent_earnings_go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Remove keyboard so no other handler is accidentally triggered
    await update.message.reply_text("🔙 Bosh menyuga qaytdingiz.", reply_markup=ReplyKeyboardRemove())

    # Go to main menu
    await admin_menu(update, context)

    # End the conversation explicitly
    return ConversationHandler.END


# 👉 Conversation handler
agent_earnings_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^💵 Agent daromadlari$"), agent_earnings_start)],
    states={
        AGENT_EARNINGS_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, agent_earnings_action)],
        AGENT_EARNINGS_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^⬅️ Admin menyu$"), agent_earnings_by_date)],
        AGENT_EARNINGS_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^⬅️ Admin menyu$"), agent_earnings_start_date)],
        AGENT_EARNINGS_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^⬅️ Admin menyu$"), agent_earnings_end_date)],
    },
    fallbacks=[MessageHandler(filters.Regex("^⬅️ Admin menyu$"), agent_earnings_go_back)],  # ✅ changed here
    allow_reentry=True
)
