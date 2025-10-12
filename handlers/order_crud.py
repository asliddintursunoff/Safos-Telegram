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

    if action == "delivered":
        is_delivered = data[3] == "true"
        response = delivered_order(order_id, is_delivered, telegram_id)
        if not response:
            await query.message.reply_text("❌ Failed to update delivery status.")
            return ConversationHandler.END
        
        # Fetch the latest order
        response = get_order_by_id(order_id, telegram_id)
        if not response:
            await query.message.reply_text("❌ Failed to fetch updated order data.")
            return ConversationHandler.END

        new_text = format_order_message(response)
        new_markup = get_order_buttons(response)

        if new_text != current_text or new_markup != current_markup:
            await query.message.edit_text(
                text=new_text,
                parse_mode="HTML",
              
            )
            # 👇 Added: update channel too
            edit_message_in_channel(response, new_text, new_markup,get_order_buttons(response,channel_mode=True))
        else:
            logging.warning(f"No changes detected for order {order_id} delivery update.")
            await query.message.reply_text("⚠️ No changes made to delivery status.")

    elif action == "approve":
        action_type = data[3]
        response = (approve_order(order_id, telegram_id) if action_type == "approve"
                    else disapprove_order(order_id, telegram_id))
        if not response:
            await query.message.reply_text("❌ Failed to update approval status.")
            return ConversationHandler.END
        
        response = get_order_by_id(order_id, telegram_id)
        if not response:
            await query.message.reply_text("❌ Failed to fetch updated order data.")
            return ConversationHandler.END

        new_text = format_order_message(response)
        new_markup = get_order_buttons(response)

        if new_text != current_text or new_markup != current_markup:
            await query.message.edit_text(
                text=new_text,
                parse_mode="HTML",
       
            )
            # 👇 Added: update channel too
            edit_message_in_channel(response, new_text, get_order_buttons(response,channel_mode=True))
        else:
            logging.warning(f"No changes detected for order {order_id} approval update.")
            await query.message.reply_text("⚠️ No changes made to approval status.")

    elif action == "delete":
        # 1️⃣ Fetch order first before deleting in DB
        order_data = get_order_by_id(order_id, telegram_id)
        if not order_data:
            await query.message.reply_text("❌ Order not found.")
            return ConversationHandler.END

        # 2️⃣ Delete message from channel
        delete_message_in_channel(order_data)

        # 3️⃣ Delete the order from the DB
        response = delete_order(order_id, telegram_id)

        if response is not None:
            await query.message.edit_text(
                text="🗑️ Order deleted successfully.",
                parse_mode="HTML",
                reply_markup=None
            )
        else:
            await query.message.reply_text("❌ Failed to delete order.")

    # query = update.callback_query
    # await query.answer()
    
    # data = query.data  # e.g., "order_edit_123"
    
    # # split by '_'
    # parts = data.split("_")
    # action = parts[1]  # delivered / edit / approve / delete
    # order_id = parts[2]  # id

    if action == "edit":
        order = get_order_by_id(order_id, update.effective_user.id)
        if not order:
            await query.message.reply_text("❌ Order not found!")
            return ConversationHandler.END

        # STOP if delivered
        if order.get("is_delivered"):
            await query.message.reply_text(
                "⚠️ This order has already been delivered and cannot be edited."
            )
            return ConversationHandler.END  # immediately exit

        # Only safe to edit
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
