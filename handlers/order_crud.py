# Replace your existing callback_handler with this function
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from formatter.order_post import format_order_message
from keyboards.inline import get_order_buttons
from .order import ASK_WHO, ask_for_who
import logging
from services.api import (
    delivered_order, approve_order, disapprove_order,
    delete_order, get_order_by_id, patch_update_order
)
from services.chanel import delete_message_in_channel, edit_message_in_channel

logger = logging.getLogger(__name__)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return

    # answer quickly to clear UI spinner
    await query.answer()

    parts = query.data.split("_")
    if len(parts) < 3:
        await query.message.reply_text("❌ Noto'g'ri callback ma'lumotlari.")
        return ConversationHandler.END

    action = parts[1]
    try:
        order_id = int(parts[2])
    except ValueError:
        await query.message.reply_text("❌ Noto'g'ri zakaz ID.")
        return ConversationHandler.END

    # owner_id is optional but if present it's at index 3
    owner_id = None
    if len(parts) >= 4 and parts[3].isdigit():
        owner_id = int(parts[3])

    clicker_id = query.from_user.id
    logger.info("Callback received: user=%s action=%s order=%s owner=%s data=%s",
                clicker_id, action, order_id, owner_id, query.data)

    # If owner_id present and clicker is not owner, attempt to fetch order as clicker.
    # Backend will only return the order if clicker has permission. If not, block.
    if owner_id is not None and clicker_id != owner_id:
        # Try to fetch order as clicker (the backend should return None/403 if not allowed)
        order_for_clicker = get_order_by_id(order_id, clicker_id)
        if not order_for_clicker:
            # polite immediate UI alert
            await query.answer("🚫 Bu tugma siz uchun emas yoki sizda ruxsat yo'q.", show_alert=True)
            return ConversationHandler.END
        # If backend returned order_for_clicker, let clicker proceed (they have permission).

    # Determine the canonical fetch id for order data (prefer owner_id if clicker is owner, else clicker)
    # This is used when you want the owner-specific view; but for permission-sensitive fetching we already tried above.
    fetch_id = owner_id if (owner_id is not None and clicker_id == owner_id) else clicker_id

    # Fetch order data (for display / channel actions). For actions we rely on API responses for authorization.
    order_data = get_order_by_id(order_id, fetch_id)
    if not order_data and action != "edit":
        await query.message.reply_text("❌ Bu zakaz allaqachon o‘chirilgan yoki topilmadi!")
        return ConversationHandler.END

    # ---------- Handle actions ----------
    if action == "delivered":
        # expected callback_data: order_delivered_<order_id>_<owner_id>_<true|false>
        is_delivered = False
        if len(parts) >= 5:
            is_delivered = parts[4] == "true"

        response = delivered_order(order_id, is_delivered, clicker_id)
        # API returns e.g. {"error": True, "status_code": 403} on forbidden actions — handle that.
        if response and response.get("status_code") == 403:
            await query.message.reply_text("❌ Faqat admin va dostavchik bu funksiyani bajara oladi!")
            return ConversationHandler.END
        if response and response.get("status_code") == 400:
            await query.message.reply_text("❌ Bu zakaz tasdiqlanmagan!")
            return ConversationHandler.END

        # refresh and update message
        updated_order = get_order_by_id(order_id, fetch_id)
        if not updated_order:
            await query.message.reply_text("❌ Bu zakaz allaqachon o‘chirilgan!")
            return ConversationHandler.END

        new_text = format_order_message(updated_order)
        new_markup = get_order_buttons(updated_order)

        if new_text != query.message.text_html or new_markup != query.message.reply_markup:
            await query.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=new_markup)
            edit_message_in_channel(updated_order, new_text, get_order_buttons(updated_order, channel_mode=True))
        else:
            logger.warning("%s raqamli zakaz uchun hech qanday o'zgaritish bo'lmadi.", order_id)
            await query.message.reply_text("⚠️ zakaz uchun hech qanday o'zgaritish bo'lmadi.")

    elif action == "approve":
        # expected: order_approve_<order_id>_<owner_id>_<approve|disapprove>
        action_type = None
        if len(parts) >= 5:
            action_type = parts[4]

        if action_type not in ("approve", "disapprove"):
            await query.message.reply_text("❌ Noto'g'ri approve tugmasi.")
            return ConversationHandler.END

        response = approve_order(order_id, clicker_id) if action_type == "approve" else disapprove_order(order_id, clicker_id)
        if response and response.get("status_code") == 403:
            await query.message.reply_text("❌ Faqat admin va dostavchik bu funksiyani bajara oladi!.")
            return ConversationHandler.END
        if not response:
            await query.message.reply_text("❌ Serverdan noto'g'ri javob olindi.")
            return ConversationHandler.END

        updated_order = get_order_by_id(order_id, fetch_id)
        if not updated_order:
            await query.message.reply_text("❌ Bu zakaz allaqachon o‘chirilgan!")
            return ConversationHandler.END

        new_text = format_order_message(updated_order)
        new_markup = get_order_buttons(updated_order)

        if new_text != query.message.text_html or new_markup != query.message.reply_markup:
            await query.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=new_markup)
            edit_message_in_channel(updated_order, new_text, get_order_buttons(updated_order, channel_mode=True))
        else:
            logger.warning("%s raqamli zakaz uchun hech qanday o'zgaritish bo'lmadi.", order_id)
            await query.message.reply_text("⚠️ zakaz uchun hech qanday o'zgaritish bo'lmadi.")

    elif action == "delete":
        response = delete_order(order_id, clicker_id)
        # If backend returns 403 or error - show message
        if response and response.get("status_code") == 403:
            await query.message.reply_text("🚫 Siz bu buyurtmani o‘chira olmaysiz.")
            return ConversationHandler.END
        if response and response.get("error"):
            await query.message.reply_text("❌Tizimda xatolik — zakaz o'chirilmadi.")
            return ConversationHandler.END

        # success: edit message to show deletion and remove in channel
        await query.message.edit_text(text="🗑️ Zakaz muvaffaqqiyatli o'chirildi.", parse_mode="HTML", reply_markup=None)
        try:
            delete_message_in_channel(order_data)
        except Exception:
            logger.exception("Xatolik: kanal xabarini o'chirishda muammo yuz berdi.")
        return ConversationHandler.END

    elif action == "edit":
        # For edit: attempt to fetch order as clicker (this checks permission server-side)
        order_for_clicker = get_order_by_id(order_id, clicker_id)
        if not order_for_clicker:
            # clicker not allowed to edit this order
            await query.answer("🚫 Sizda bu zakazni tahrirlash huquqi yo'q.", show_alert=True)
            return ConversationHandler.END

        # If order delivered -> cannot edit
        if order_for_clicker.get("is_delivered"):
            await query.message.reply_text("⚠️ Bu zakaz allaqachon yetqazib berilgan,buni o'zgartirib bo'lmaydi")
            return ConversationHandler.END

        # Safe to populate user_data for this clicker
        context.user_data["agent"] = {"id": order_for_clicker["agent"]["telegram_id"], **order_for_clicker["agent"]}
        context.user_data["edit_order_id"] = order_id
        context.user_data["order"] = {
            "for_who": order_for_clicker["for_who"],
            "items": [
                {"product_id": item["product"]["id"], "quantity": item["quantity"]}
                for item in order_for_clicker["items"]
            ]
        }

        await query.message.reply_text(f"✏️ Edit products for order #{order_id}:")
        # Start the conversation flow (ask_for_who supports callback or message)
        return await ask_for_who(update=update, context=context)

    return ConversationHandler.END
