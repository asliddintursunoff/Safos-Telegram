from telegram import Update
from telegram.ext import ContextTypes,ConversationHandler
from formatter.order_post import format_order_message
from keyboards.inline import get_order_buttons
from .order import ASK_WHO,ask_for_who
import logging
from services.api import delivered_order, approve_order, disapprove_order, delete_order, get_order_by_id,patch_update_order
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)
from services.chanel import delete_message_in_channel,edit_message_in_channel
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    action = data[1]
    order_id = int(data[2])
    telegram_id = update.effective_user.id

    current_text = query.message.text_html
    current_markup = query.message.reply_markup

    # ✅ Check if order exists once at the top (except for actions like "edit" if needed)
    order_data = get_order_by_id(order_id, telegram_id)
    if not order_data and action != "edit":  # allow edit to handle its own logic if needed
        await query.message.reply_text("❌ Bu zakaz allaqachon o‘chirilgan!")
        return ConversationHandler.END

    if action == "delivered":
        is_delivered = data[3] == "true"
        response = delivered_order(order_id, is_delivered, telegram_id)
        if not response:
            await query.message.reply_text("❌ Faqat admin va dostavchik bu funksiyani bajara oladi!")
            return ConversationHandler.END

        updated_order = get_order_by_id(order_id, telegram_id)
        if not updated_order:
            await query.message.reply_text("❌ Bu zakaz allaqachon o‘chirilgan!")
            return ConversationHandler.END

        new_text = format_order_message(updated_order)
        new_markup = get_order_buttons(updated_order)

        if new_text != current_text or new_markup != current_markup:
            await query.message.edit_text(
                text=new_text,
                parse_mode="HTML",
                reply_markup=new_markup
            )
            edit_message_in_channel(updated_order, new_text, get_order_buttons(updated_order, channel_mode=True))
        else:
            logging.warning(f"{order_id} raqamli zakaz uchun hech qanday o'zgaritish bo'lmadi.")
            await query.message.reply_text("⚠️ zakaz uchun hech qanday o'zgaritish bo'lmadi.")

    elif action == "approve":
        action_type = data[3]
        response = (approve_order(order_id, telegram_id)
                    if action_type == "approve"
                    else disapprove_order(order_id, telegram_id))
        if not response:
            await query.message.reply_text("❌ Faqat admin va dostavchik bu funksiyani bajara oladi!.")
            return ConversationHandler.END

        updated_order = get_order_by_id(order_id, telegram_id)
        if not updated_order:
            await query.message.reply_text("❌ Bu zakaz allaqachon o‘chirilgan!")
            return ConversationHandler.END

        new_text = format_order_message(updated_order)
        new_markup = get_order_buttons(updated_order)

        if new_text != current_text or new_markup != current_markup:
            await query.message.edit_text(
                text=new_text,
                parse_mode="HTML",
                reply_markup=new_markup
            )
            edit_message_in_channel(updated_order, new_text, get_order_buttons(updated_order, channel_mode=True))
        else:
            logging.warning(f"{order_id} raqamli zakaz uchun hech qanday o'zgaritish bo'lmadi.")
            await query.message.reply_text("⚠️ zakaz uchun hech qanday o'zgaritish bo'lmadi.")

    elif action == "delete":
        response = delete_order(order_id, telegram_id)

        if response and not response.get("error"):
            await query.message.edit_text(
                text="🗑️ Zakaz muvaffaqqiyatli o'chirildi.",
                parse_mode="HTML",
                reply_markup=None
            )
            delete_message_in_channel(order_data)
        else:
            if response and response.get("status_code") == 403:
                await query.message.reply_text("🚫 Siz bu buyurtmani o‘chira olmaysiz.")
            else:
                await query.message.reply_text("❌Tizimda xatolik zakaz o'chirilmadi.")

    elif action == "edit":
        order = get_order_by_id(order_id, update.effective_user.id)
        if not order:
            await query.message.reply_text("❌ Zakaz mavjud emas yoki allaqachon o'chirib yuborilgan")
            return ConversationHandler.END

        if order.get("is_delivered"):
            await query.message.reply_text(
                "⚠️ Bu zakaz allaqachon yetqazib berilgan,buni o'zgartirib bo'lmaydi"
            )
            return ConversationHandler.END

        context.user_data["agent"] = {"id": order["agent"]["telegram_id"], **order["agent"]}
        context.user_data["edit_order_id"] = order_id
        context.user_data["order"] = {
            "for_who": order["for_who"],
            "items": [
                {"product_id": item["product"]["id"], "quantity": item["quantity"]}
                for item in order["items"]
            ]
        }

        await query.message.reply_text(f"✏️ Edit products for order #{order_id}:")
        await ask_for_who(update=update, context=context)

    return ConversationHandler.END
