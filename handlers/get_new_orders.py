import asyncio
import logging
from html import escape

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from services.api import get_new_orders,calculating_new_orders_quantity
from services.chanel import send_order_text
from formatter.order_post import format_order_message
from keyboards.inline import get_order_buttons
from .main_menu import main_menu
from telegram.ext import filters,MessageHandler

logger = logging.getLogger(__name__)


async def show_existing_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    orders = get_new_orders(telegram_id)

    if orders is None:
        await update.message.reply_text("❌ Zakazlarni olishda xatolik. Keyinroq urinib ko'ring.")
        return
    if not orders:
        await update.message.reply_text("📭 Sizda mavjud zakazlar yo‘q.")
        return

    for index, order in enumerate(orders):
        try:
            await send_order_text(context.bot, update.effective_chat.id, format_order_message(order), get_order_buttons(order))
        except TelegramError:
            # one bad order must not stop the whole list
            logger.exception("Zakaz %s ni yuborib bo'lmadi", order.get("id"))
            await update.message.reply_text(f"⚠️ {order.get('id')}-zakazni ko'rsatib bo'lmadi.")
        if index % 20 == 19:
            await asyncio.sleep(1)  # stay under Telegram's flood limits for long lists

    # total money of all listed orders
    total_money = sum(float(order.get("get_total_price") or 0) for order in orders)
    total_line = f"\n💰 <b>Jami summa ({len(orders)} ta zakaz):</b> {total_money:,.0f} so'm"

    orders_quantity_json = calculating_new_orders_quantity()
    if not isinstance(orders_quantity_json, dict):
        await update.effective_message.reply_text("Tizimda muammo bor!, Hisoblashda adashdim!" + total_line, parse_mode="HTML")
    else:
        message_for_orders_quantity = "Mavjud zakaslar soni:\n"
        for key,value in orders_quantity_json.items():
            message_for_orders_quantity+= f"<b>{escape(str(key))}</b> -- {escape(str(value))}\n"

        message_for_orders_quantity = message_for_orders_quantity[:4096 - len(total_line)] + total_line
        await update.effective_message.reply_text(message_for_orders_quantity,parse_mode="HTML")
    await main_menu(update,context)
    return


existing_orders_handler = MessageHandler(filters.TEXT & filters.Regex("^📦 Mavjud zakaslar$"), show_existing_orders)
