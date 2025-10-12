import requests
import json
from config import CHANEL_ID,BOT_TOKEN

def sending_post(text,buttons):
    response = requests.post(
        url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHANEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": buttons.to_dict()  # 👈 convert InlineKeyboardMarkup to dict
        }
    )
    if response.status_code == 200:
        return response.json()
    return None



import requests
import json

def edit_message_in_channel(order, new_text, new_markup):
    """
    Edits both the user and channel messages for a given order.
    """
    inline_markup = json.dumps(new_markup.to_dict()) if new_markup else None

    # 1️⃣ Edit bot message
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
        json={
            "chat_id": order["user_chat_id"],
            "message_id": order["user_message_id"],
            "text": new_text,
            "parse_mode": "HTML",
            "reply_markup": inline_markup
        }
    )

    # 2️⃣ Edit channel message
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
        json={
            "chat_id": order["channel_chat_id"],
            "message_id": order["channel_message_id"],
            "text": new_text,
            "parse_mode": "HTML",
            "reply_markup": inline_markup
        }
    )

def delete_message_in_channel(order):
    user_chat_id = order.get("user_chat_id")
    user_message_id = order.get("user_message_id")
    channel_chat_id = order.get("channel_chat_id")
    channel_message_id = order.get("channel_message_id")

    if channel_chat_id and channel_message_id:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
            json={
                "chat_id": channel_chat_id,
                "message_id": channel_message_id
            }
        )

    if user_chat_id and user_message_id:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
            json={
                "chat_id": user_chat_id,
                "message_id": user_message_id
            }
        )
