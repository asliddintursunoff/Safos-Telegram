from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from formatter.order_post import format_order_message
from keyboards.inline import get_order_buttons, get_delete_confirm_buttons
import logging
from services.api import (
    delivered_order, approve_order, disapprove_order,
    delete_order, get_order_by_id,
)
from services.chanel import delete_message_in_channel, edit_message_in_channel, safe_edit_message

logger = logging.getLogger(__name__)


async def _refresh_messages(query, context, order_id, clicker_id):
    """Show the new state on the clicked message, the owner's message and the channel post."""
    updated_order = get_order_by_id(order_id, clicker_id)
    if not updated_order:
        await query.message.reply_text("❌ Bu zakaz allaqachon o‘chirilgan!")
        return
    new_text = format_order_message(updated_order)
    user_markup = get_order_buttons(updated_order)
    channel_markup = get_order_buttons(updated_order, channel_mode=True)

    is_channel_post = str(query.message.chat_id) == str(updated_order.get("channel_chat_id")) \
        and str(query.message.message_id) == str(updated_order.get("channel_message_id"))
    await safe_edit_message(context.bot, query.message.chat_id, query.message.message_id, new_text,
                            channel_markup if is_channel_post else user_markup)
    await edit_message_in_channel(context.bot, updated_order, new_text, user_markup, channel_markup)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return

    parts = query.data.split("_")
    if len(parts) < 3:
        await query.answer("❌ Noto'g'ri callback ma'lumotlari.", show_alert=True)
        return

    action = parts[1]
    if action == "edit":
        # handled by the order conversation (handlers/order.py)
        return

    try:
        order_id = int(parts[2])
    except ValueError:
        await query.answer("❌ Noto'g'ri zakaz ID.", show_alert=True)
        return

    owner_id = parts[3] if len(parts) >= 4 else "0"
    clicker_id = query.from_user.id
    logger.info("Callback received: user=%s action=%s order=%s data=%s", clicker_id, action, order_id, query.data)

    # the backend only returns the order if the clicker is allowed to see it
    order_data = get_order_by_id(order_id, clicker_id)
    if not order_data:
        await query.answer("🚫 Zakaz topilmadi yoki sizda ruxsat yo'q.", show_alert=True)
        return

    # ---------- Handle actions ----------
    if action == "delivered":
        # expected callback_data: order_delivered_<order_id>_<owner_id>_<true|false>
        is_delivered = len(parts) >= 5 and parts[4] == "true"

        response = delivered_order(order_id, is_delivered, clicker_id)
        status = response.get("status_code") if response and response.get("error") else None
        if status == 403:
            await query.answer("❌ Faqat admin va dostavchik bu funksiyani bajara oladi!", show_alert=True)
            return
        if status == 400:
            await query.answer("❌ Bu zakaz tasdiqlanmagan!", show_alert=True)
            return
        if status:
            await query.answer("❌ Serverda xatolik, qaytadan urinib ko'ring.", show_alert=True)
            return
        await query.answer("✅ Saqlandi")
        await _refresh_messages(query, context, order_id, clicker_id)

    elif action == "approve":
        # expected: order_approve_<order_id>_<owner_id>_<approve|disapprove>
        action_type = parts[4] if len(parts) >= 5 else None
        if action_type not in ("approve", "disapprove"):
            await query.answer("❌ Noto'g'ri approve tugmasi.", show_alert=True)
            return

        response = approve_order(order_id, clicker_id) if action_type == "approve" else disapprove_order(order_id, clicker_id)
        if response and response.get("status_code") == 403:
            await query.answer("❌ Faqat admin va dostavchik bu funksiyani bajara oladi!.", show_alert=True)
            return
        if not response:
            await query.answer("❌ Serverdan noto'g'ri javob olindi.", show_alert=True)
            return
        await query.answer("✅ Saqlandi")
        await _refresh_messages(query, context, order_id, clicker_id)

    elif action == "delete":
        # ask first: one accidental tap used to delete the order for good
        await query.answer()
        try:
            await query.message.edit_reply_markup(reply_markup=get_delete_confirm_buttons(order_id, owner_id))
        except BadRequest:
            await query.message.reply_text(
                f"🗑️ {order_id}-zakazni o'chirishni tasdiqlaysizmi?",
                reply_markup=get_delete_confirm_buttons(order_id, owner_id),
            )

    elif action == "delcancel":
        await query.answer("Bekor qilindi")
        await _refresh_messages(query, context, order_id, clicker_id)

    elif action == "delconfirm":
        response = delete_order(order_id, clicker_id)
        if response and response.get("status_code") == 403:
            await query.answer("🚫 Siz bu buyurtmani o‘chira olmaysiz.", show_alert=True)
            return
        if response and response.get("error"):
            await query.answer("❌Tizimda xatolik — zakaz o'chirilmadi.", show_alert=True)
            return
        await query.answer("🗑️ O'chirildi")

        try:
            await query.message.edit_text(text="🗑️ Zakaz muvaffaqqiyatli o'chirildi.", parse_mode="HTML", reply_markup=None)
        except BadRequest:
            pass
        await delete_message_in_channel(context.bot, order_data)

    else:
        await query.answer()
