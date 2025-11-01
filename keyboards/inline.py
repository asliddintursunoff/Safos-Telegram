# inline.py (replace get_order_buttons)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from formatter.printer_check import get_order_print_url

def get_order_buttons(order, channel_mode=False):
    is_delivered = order.get("is_delivered", False)
    is_approved = order.get("is_approved", False)

    delivered_label = "✅Yetqazilgan" if not is_delivered else "❌Yetqazilmagan"
    approve_label = "✅Tasdiqlash" if not is_approved else "❌ Tasdiqlanmagan"

    # determine owner id (agent's telegram id if available)
    owner_id = 0
    try:
        owner_id = int(order.get("agent", {}).get("telegram_id") or 0)
    except Exception:
        owner_id = 0

    if channel_mode:
        # Deep link to bot (channel mode keeps original behaviour)
        edit_button = InlineKeyboardButton(
            "✏️Tahrirlash",
            url=f"https://t.me/safos_tgbot?start=edit_{order['id']}"
        )
    else:
        # include owner_id in callback_data (position 3)
        edit_button = InlineKeyboardButton(
            "✏️Tahrirlash",
            callback_data=f"order_edit_{order['id']}_{owner_id}"
        )

    print_url = get_order_print_url(order)
    print_button = InlineKeyboardButton("🖨 Print", url=print_url)

    buttons = [
        [
            InlineKeyboardButton(
                delivered_label,
                # order_delivered_<order_id>_<owner_id>_<true|false>
                callback_data=f"order_delivered_{order['id']}_{owner_id}_{'true' if not is_delivered else 'false'}"
            ),
            edit_button,
        ],
        [
            InlineKeyboardButton(
                approve_label,
                # order_approve_<order_id>_<owner_id>_<approve|disapprove>
                callback_data=f"order_approve_{order['id']}_{owner_id}_{'approve' if not is_approved else 'disapprove'}"
            ),
            InlineKeyboardButton(
                "🗑️O'chirish",
                # order_delete_<order_id>_<owner_id>
                callback_data=f"order_delete_{order['id']}_{owner_id}"
            ),
        ],
        [print_button]
    ]
    return InlineKeyboardMarkup(buttons)
