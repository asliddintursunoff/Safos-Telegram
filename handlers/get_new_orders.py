from telegram import Update
from telegram.ext import ContextTypes
from services.api import get_new_orders,calculating_new_orders_quantity
from formatter.order_post import format_order_message
from keyboards.inline import get_order_buttons
from .main_menu import main_menu
from telegram.ext import filters,MessageHandler

async def show_existing_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    orders = get_new_orders(telegram_id)  # 👈 your API call to get existing orders

    if not orders:
        await update.message.reply_text("📭 Sizda mavjud zakazlar yo‘q.")
        return

    for order in orders:
        message_text = format_order_message(order)
        buttons = get_order_buttons(order)
        await update.message.reply_text(
            message_text,
            parse_mode="HTML",
            reply_markup=buttons
        )
    
    orders_quantity_json = calculating_new_orders_quantity()
    if orders ==None:
        await update.effective_message.reply_text("Tizimda muammo bor!, Hisoblashda adashdim!")
    else:
        message_for_orders_quantity = "Mavjud zakaslar soni:\n"
        for key,value in orders_quantity_json.items():
            message_for_orders_quantity+= f"<b>{key}</b> -- {value}\n"

        await update.effective_message.reply_text(message_for_orders_quantity,parse_mode="HTML")
    await main_menu(update,context)
    return


existing_orders_handler = MessageHandler(filters.TEXT & filters.Regex("^📦 Mavjud zakaslar$"), show_existing_orders)

