from telegram.ext import ContextTypes
from telegram import Update
from telegram.ext import ConversationHandler
from services.api import getting_my_orders_price,remaining_salary
from keyboards.reply import hisob_kitob_button
from .main_menu import main_menu
from telegram.ext import MessageHandler, filters
async def hisob_kitob_menu(update:Update,context:ContextTypes.DEFAULT_TYPE):
    reply_markup = hisob_kitob_button
    await update.effective_message.reply_text("Sizga kerak vazifani tanlab tugmani bosing!",reply_markup=reply_markup)



ASK_START_DATE, ASK_END_DATE = range(200,202)  # states for conversation
ASK_WHICH_DAY = 10
async def hisob_kitob_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    telegram_id = update.effective_user.id

    valid_buttons = [
        "💰 BUGUNGI ZAKASLARIM PULI",
        "📆BELGILANGAN SANADAGI",
        "📊 SANA ORALIG'IDAGI",
        "⬅️ Ortga",
        "📕Hisobim"
    ]

    if text not in valid_buttons:
        # Ignore invalid messages instead of replying
        return  # Do nothing

    if text == "💰 BUGUNGI ZAKASLARIM PULI":
        result = getting_my_orders_price(telegram_id=telegram_id, today_only=True)
        total = result.get("total_price", 0) if result else 0
        await update.message.reply_text(
            f"💰 Bugungi zakazlaringizning jami narxi: <b>{total:,}</b> so'm",
            parse_mode="HTML"
        )
        await main_menu(update, context)
        return ConversationHandler.END

    if text == "📆BELGILANGAN SANADAGI":
        await update.message.reply_text(
            "Iltimos, sanani kiriting (format dd-mm-yyyy):"
        )
        return ASK_WHICH_DAY

    elif text == "📊 SANA ORALIG'IDAGI":
        await update.message.reply_text("Boshlanish sanasini kiriting (format dd-mm-yyyy):")
        return ASK_START_DATE

    elif text == "⬅️ Ortga":
        await main_menu(update, context)
        return ConversationHandler.END

    elif text == "📕Hisobim":
        result = remaining_salary(telegram_id=telegram_id)
        total = result.get("remaining_salary", 0) if result else 0
        await update.message.reply_text(
            f"💰 Bugungi zakazlaringizning jami narxi: <b>{total:,}</b> so'm",
            parse_mode="HTML"
        )
        await main_menu(update, context)
        return ConversationHandler.END

    

from datetime import datetime

from datetime import datetime, timedelta

async def start_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    try:
        # parse user input
        start_date = datetime.strptime(date_text, "%d-%m-%Y")
        # convert to API format with start of day
        context.user_data["start_date"] = start_date.strftime("%Y-%m-%dT00:00:00")
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format! Iltimos dd-mm-yyyy formatida kiriting.")
        return ASK_START_DATE

    await update.message.reply_text("Tugash sanasini kiriting (format dd-mm-yyyy):")
    return ASK_END_DATE

async def end_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    try:
        end_date = datetime.strptime(date_text, "%d-%m-%Y")
        # end of the day for API
        context.user_data["end_date"] = end_date.strftime("%Y-%m-%dT23:59:59")
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format! Iltimos dd-mm-yyyy formatida kiriting.")
        return ASK_END_DATE

    telegram_id = update.effective_user.id
    start_date_api = context.user_data.get("start_date")
    end_date_api = context.user_data.get("end_date")

    # Call API
    result = getting_my_orders_price(
        telegram_id=telegram_id, 
        start_date=start_date_api, 
        end_date=end_date_api
    )
    total = result.get("total_price", 0) if result else 0
    await update.message.reply_text(f"📊 Tanlangan davr bo‘yicha zakazlaringizning jami narxi: <b>{total:,}</b> so'm",parse_mode="HTML")
    await main_menu(update, context)
    return ConversationHandler.END

async def which_day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    telegram_id = update.effective_user.id

    try:
        # Parse user input
        selected_date = datetime.strptime(date_text, "%d-%m-%Y")
        # Convert to API format
        which_day = selected_date.strftime("%Y-%m-%d")
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri format! Iltimos dd-mm-yyyy formatida kiriting."
        )
        return ASK_WHICH_DAY

    # Call your API
    result = getting_my_orders_price(
        telegram_id=telegram_id,
        which_day=which_day
    )
    total = result.get("total_price", 0) if result else 0

    await update.message.reply_text(
        f"📆 {date_text} sanasidagi zakazlaringizning jami narxi: <b>{total:,}</b> so'm",parse_mode="HTML"
    )
    await main_menu(update, context)
    return ConversationHandler.END


from telegram.ext import CommandHandler
valid_buttons = ["💰 BUGUNGI ZAKASLARIM PULI", "📆BELGILANGAN SANADAGI", "📊 SANA ORALIG'IDAGI", "⬅️ Ortga", "📕Hisobim"]

hisob_kitob_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(f"^({'|'.join(valid_buttons)})$"), hisob_kitob_handler)],
    states={
        ASK_START_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), start_date_handler)],
        ASK_END_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), end_date_handler)],
        ASK_WHICH_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, which_day_handler)],
    },
    fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
)
