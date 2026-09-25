# inline.py (replace get_order_buttons)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from formatter.printer_check import get_order_print_url

# The receipt is put inside the url. Every item adds ~500 characters (the "█" separator
# lines are 9 bytes each when url-encoded), so big orders become longer than Telegram
# accepts ("Reply markup is too long"). Above this size we use the short link from the
# backend, which redirects to exactly the same print page with the same data.
MAX_DIRECT_PRINT_URL = 2000
PRINT_TEXT = "🖨 Print"


def get_print_url(order):
    try:
        direct = get_order_print_url(order)
    except Exception:
        direct = None
    if direct and len(direct) <= MAX_DIRECT_PRINT_URL:
        return direct
    return order.get("print_url") or direct


def without_print(markup):
    """Same keyboard without the print button (used if Telegram still rejects the markup)."""
    if markup is None:
        return None
    rows = [[b for b in row if b.text != PRINT_TEXT] for row in markup.inline_keyboard]
    return InlineKeyboardMarkup([r for r in rows if r])


def has_print_button(markup) -> bool:
    return markup is not None and any(b.text == PRINT_TEXT for row in markup.inline_keyboard for b in row)


def is_markup_too_long(error) -> bool:
    text = str(error).lower()
    return "reply markup is too long" in text or ("url" in text and "invalid" in text)

def get_order_buttons(order, channel_mode=False):
    is_delivered = order.get("is_delivered", False)
    is_approved = order.get("is_approved", False)

    delivered_label = "✅Yetqazilgan" if not is_delivered else "❌Yetqazilmagan"
    approve_label = "✅Tasdiqlash" if not is_approved else "❌ Tasdiqlanmagan"

    # determine owner id (agent's telegram id if available)
    owner_id = 0
    try:
        owner_id = int((order.get("agent") or {}).get("telegram_id") or 0)
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

    print_url = get_print_url(order)

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
    ]
    if print_url:
        buttons.append([InlineKeyboardButton(PRINT_TEXT, url=print_url)])
    return InlineKeyboardMarkup(buttons)


def get_delete_confirm_buttons(order_id, owner_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"order_delconfirm_{order_id}_{owner_id}"),
        InlineKeyboardButton("❌ Yo'q", callback_data=f"order_delcancel_{order_id}_{owner_id}"),
    ]])
