from datetime import datetime
from html import escape

# Telegram does not accept messages longer than 4096 characters
MAX_MESSAGE_LEN = 4096


def _fmt_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).strftime("%d-%m-%Y %H:%M")
    except (TypeError, ValueError):
        return str(value)


def _full_name(person):
    if not person:
        return None
    return escape(f"{person.get('first_name') or ''} {person.get('last_name') or ''}".strip())


def _num(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{int(value):,}" if value.is_integer() else f"{value:,}"


def format_order_message(order: dict):
    status_approved = "" if order.get("is_approved") else "#Yaroqsiz❌"
    status_delivered = "#yetqazib berildi✅" if order.get("is_delivered") else "#yetqazilmagan❌"

    order_date = _fmt_date(order.get("order_date")) or "Noma'lum"
    agent_fullname = _full_name(order.get("agent")) or "Noma'lum agent"
    dostavchik_name = _full_name(order.get("dostavchik"))
    delivered_date = _fmt_date(order.get("delivered_date"))
    for_who = escape(order.get("for_who") or "Noma'lum")

    text = f"{status_approved}\n{status_delivered}\n"
    text += f"🧾 <b>Buyurtma tafsilotlari:</b>\n\n"
    text += f"🧾 <b>Buyurtmani oldi:</b> {agent_fullname}\n"
    text += f"👤 <b>Buyurtma egasi:</b> {for_who}\n"
    if dostavchik_name:
        text += f"🚚 <b>Yetqazib berdi:</b> {dostavchik_name}\n"
    text+="\n"
    text += f"⏰ <b>Buyurtma vaqti:</b> {order_date}\n"
    if delivered_date:
        text += f"🚚⏰ <b>Yetqazib berilgan vaqti:</b> {delivered_date}\n\n"

    total_price = order.get("get_total_price") or 0
    footer = f"\n🟢 <b>Umumiy narx:</b> {_num(total_price)} so'm ✅"

    item_lines = []
    for item in order.get("items") or []:
        product = item.get("product") or {}
        item_lines.append(
            f"📦 {escape(str(product.get('name', '')))} {escape(str(product.get('unit', '')))} x {_num(item.get('quantity'))} × {_num(product.get('price'))} = {_num(item.get('total_price'))} so'm\n"
        )

    body = "".join(item_lines)
    if len(text) + len(body) + len(footer) > MAX_MESSAGE_LEN:
        # very big order: shorter item lines so the message still fits in one Telegram message
        item_lines = []
        for item in order.get("items") or []:
            product = item.get("product") or {}
            item_lines.append(f"• {escape(str(product.get('name', '')))} x {_num(item.get('quantity'))} = {_num(item.get('total_price'))}\n")
        body = ""
        for i, line in enumerate(item_lines):
            rest = f"… va yana {len(item_lines) - i} ta mahsulot\n"
            if len(text) + len(body) + len(line) + len(rest) + len(footer) > MAX_MESSAGE_LEN:
                body += rest
                break
            body += line

    return text + body + footer
