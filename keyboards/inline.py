from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from formatter.printer_check import get_order_print_url
def get_order_buttons(order, channel_mode=False):
    is_delivered = order.get("is_delivered", False)
    is_approved = order.get("is_approved", False)

    delivered_label = "✅Yetqazilgan" if not is_delivered else "❌Yetqazilmagan"
    approve_label = "✅Tasdiqlash" if not is_approved else "❌ Tasdiqlanmagan"

    if channel_mode:
        # Deep link to bot
        edit_button = InlineKeyboardButton(
            "✏️Tahrirlash",
            url=f"https://t.me/safos_tgbot?start=edit_{order['id']}"
        )
    else:
        # Normal callback when inside bot chat
        edit_button = InlineKeyboardButton(
            "✏️Tahrirlash",
            callback_data=f"order_edit_{order['id']}"
        )
    print_url = get_order_print_url(order)
    print_button = InlineKeyboardButton("🖨 Print", url=print_url)
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
                "🗑️O'chirish",
                callback_data=f"order_delete_{order['id']}"
            ),
        ],
         [print_button]
    ]
    return InlineKeyboardMarkup(buttons)
