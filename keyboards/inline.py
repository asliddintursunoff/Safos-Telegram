from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_order_buttons(order, channel_mode=False):
    is_delivered = order.get("is_delivered", False)
    is_approved = order.get("is_approved", False)

    delivered_label = "✅ Delivered" if not is_delivered else "❌ Undelivered"
    approve_label = "✅ Approve" if not is_approved else "❌ Disapprove"

    if channel_mode:
        # Deep link to bot
        edit_button = InlineKeyboardButton(
            "✏️ Edit",
            url=f"https://t.me/safos_tgbot?start=edit_{order['id']}"
        )
    else:
        # Normal callback when inside bot chat
        edit_button = InlineKeyboardButton(
            "✏️ Edit",
            callback_data=f"order_edit_{order['id']}"
        )

    buttons = [
        [
            InlineKeyboardButton(
                delivered_label,
                callback_data=f"order_delivered_{order['id']}_{'true' if not is_delivered else 'false'}"
            ),
            edit_button,
        ],
        [
            InlineKeyboardButton(
                approve_label,
                callback_data=f"order_approve_{order['id']}_{'approve' if not is_approved else 'disapprove'}"
            ),
            InlineKeyboardButton(
                "🗑️ Delete",
                callback_data=f"order_delete_{order['id']}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(buttons)
