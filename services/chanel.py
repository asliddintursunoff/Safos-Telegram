import asyncio
import logging

from telegram.error import BadRequest, RetryAfter, TelegramError

from config import CHANEL_ID
from keyboards.inline import without_print, is_markup_too_long, has_print_button

logger = logging.getLogger(__name__)


async def _retry(call, *args, **kwargs):
    """Run a Telegram call, waiting once if Telegram asks us to slow down (flood control)."""
    try:
        return await call(*args, **kwargs)
    except RetryAfter as e:
        await asyncio.sleep(float(getattr(e.retry_after, "total_seconds", lambda: e.retry_after)()) + 1)
        return await call(*args, **kwargs)


async def send_order_text(bot, chat_id, text, markup):
    """Send an order message; if the keyboard is rejected, send it again without the print button."""
    try:
        return await _retry(bot.send_message, chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=markup)
    except BadRequest as e:
        if not (is_markup_too_long(e) and has_print_button(markup)):
            raise
        logger.warning("Markup rejected (%s), sending without print button", e)
        return await _retry(bot.send_message, chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=without_print(markup))


async def sending_post(bot, text, buttons):
    """Send the order post to the channel. Returns the sent Message or None."""
    if not CHANEL_ID:
        return None
    try:
        return await send_order_text(bot, CHANEL_ID, text, buttons)
    except TelegramError:
        logger.exception("Kanalga xabar yuborilmadi")
        return None


async def safe_edit_message(bot, chat_id, message_id, text, markup) -> bool:
    if not chat_id or not message_id:
        return False
    try:
        await _retry(bot.edit_message_text, chat_id=chat_id, message_id=int(message_id),
                     text=text, parse_mode="HTML", reply_markup=markup)
        return True
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return True
        if is_markup_too_long(e) and has_print_button(markup):
            return await safe_edit_message(bot, chat_id, message_id, text, without_print(markup))
        logger.warning("Xabarni tahrirlab bo'lmadi chat=%s msg=%s: %s", chat_id, message_id, e)
        return False
    except (TelegramError, ValueError, TypeError):
        logger.exception("Xabarni tahrirlashda xatolik chat=%s msg=%s", chat_id, message_id)
        return False


async def edit_message_in_channel(bot, order, new_text, new_markup_user, new_markup_channel):
    """
    Edits both the user (bot chat) and channel messages for a given order.
    """
    user_ok = await safe_edit_message(bot, order.get("user_chat_id"), order.get("user_message_id"), new_text, new_markup_user)
    await safe_edit_message(bot, order.get("channel_chat_id"), order.get("channel_message_id"), new_text, new_markup_channel)
    return user_ok


async def delete_message_in_channel(bot, order):
    for chat_key, msg_key in (("channel_chat_id", "channel_message_id"), ("user_chat_id", "user_message_id")):
        chat_id, message_id = order.get(chat_key), order.get(msg_key)
        if chat_id and message_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=int(message_id))
            except (TelegramError, ValueError, TypeError) as e:
                logger.warning("Xabarni o'chirib bo'lmadi chat=%s msg=%s: %s", chat_id, message_id, e)
