from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from handlers.admin_menu import admin_menu
from services.api import (
    get_total_orders_price_today,
    get_total_orders_price_by_date,
    get_total_orders_price_between
)
from datetime import datetime

# 📌 States
(
    ZAKAZ_HISOBOT_ACTION,
    ZAKAZ_HISOBOT_DATE,
    ZAKAZ_HISOBOT_START_DATE,
    ZAKAZ_HISOBOT_END_DATE
) = range(4)


# 📅 Helper: convert dd-mm-yyyy to yyyy-mm-dd
def convert_date_format(date_str: str) -> str | None:
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


# 🧭 Step 1 — Show menu
async def zakaz_hisobot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        ["📆 Bugun", "📅 Sana"],
        ["📊 Oraliqdagi sana"],
        ["⬅️ Ortga"]
    ]
    await update.message.reply_text(
        "📊 Qaysi oraliqni tanlaysiz?",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return ZAKAZ_HISOBOT_ACTION


# 🧭 Step 2 — Handle action
async def zakaz_hisobot_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "⬅️ Ortga":
        await admin_menu(update, context)
        return ConversationHandler.END

    if text == "📆 Bugun":
        result = get_total_orders_price_today(update.effective_user.id)
        total = (result.get("total_price") or 0) if isinstance(result, dict) else (result or 0)
        await update.message.reply_text(
            f"📅 Bugungi zakazlar umumiy summasi: 💰 {total:,.0f} so‘m"
        )
        return ConversationHandler.END

    if text == "📅 Sana":
        await update.message.reply_text("📅 Sanani kiriting (masalan: 12-10-2025):")
        return ZAKAZ_HISOBOT_DATE

    if text == "📊 Oraliqdagi sana":
        await update.message.reply_text("⏳ Boshlanish sanasini kiriting (masalan: 01-10-2025):")
        return ZAKAZ_HISOBOT_START_DATE


# 🧭 Step 3 — Sana bo‘yicha hisob
async def zakaz_hisobot_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    converted = convert_date_format(date_str)
    if not converted:
        await update.message.reply_text("❌ Sana noto‘g‘ri formatda. Masalan: 12-10-2025")
        return ZAKAZ_HISOBOT_DATE

    result = get_total_orders_price_by_date(update.effective_user.id, converted)
    total = (result.get("total_price") or 0) if isinstance(result, dict) else (result or 0)
    await update.message.reply_text(
        f"📅 {date_str} sanasidagi zakazlar summasi: 💰 {total:,.0f} so‘m"
    )
    return ConversationHandler.END


# 🧭 Step 4 — Start date for range
async def zakaz_hisobot_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    converted = convert_date_format(date_str)
    if not converted:
        await update.message.reply_text("❌ Sana noto‘g‘ri formatda. Masalan: 12-10-2025")
        return ZAKAZ_HISOBOT_START_DATE

    context.user_data["start_date"] = converted
    context.user_data["start_date_display"] = date_str
    await update.message.reply_text("📅 Tugash sanasini kiriting (masalan: 12-10-2025):")
    return ZAKAZ_HISOBOT_END_DATE


# 🧭 Step 5 — End date for range
async def zakaz_hisobot_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    converted = convert_date_format(date_str)
    if not converted:
        await update.message.reply_text("❌ Sana noto‘g‘ri formatda. Masalan: 12-10-2025")
        return ZAKAZ_HISOBOT_END_DATE

    start_date = context.user_data.get("start_date")
    start_display = context.user_data.get("start_date_display")

    result = get_total_orders_price_between(update.effective_user.id, start_date, converted)
    total = (result.get("total_price") or 0) if isinstance(result, dict) else (result or 0)

    await update.message.reply_text(
        f"📊 {start_display} dan {date_str} gacha bo‘lgan zakazlar summasi: 💰 {total:,.0f} so‘m"
    )
    return ConversationHandler.END


async def zakaz_hisobot_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_menu(update, context)
    return ConversationHandler.END


NOT_BACK = ~filters.Regex("^⬅️ Ortga$")

# 🧭 Conversation handler
zakaz_hisobot_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^💰 Zakaz hisobot$"), zakaz_hisobot_start)],
    states={
        ZAKAZ_HISOBOT_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, zakaz_hisobot_action)],
        ZAKAZ_HISOBOT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & NOT_BACK, zakaz_hisobot_by_date)],
        ZAKAZ_HISOBOT_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & NOT_BACK, zakaz_hisobot_start_date)],
        ZAKAZ_HISOBOT_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & NOT_BACK, zakaz_hisobot_end_date)],
    },
    fallbacks=[MessageHandler(filters.Regex("^⬅️ Ortga$"), zakaz_hisobot_back)],
    allow_reentry=True
)


