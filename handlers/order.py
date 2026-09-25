import logging
import re

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from services.api import get_products, get_order_by_id, create_order, update_order, patch_update_order
from services.profile import get_profile
from handlers.main_menu import main_menu
from keyboards.reply import back_button
from keyboards.inline import get_order_buttons
from formatter.order_post import format_order_message
from services.chanel import sending_post, send_order_text, edit_message_in_channel
from config import CHANEL_ID

logger = logging.getLogger(__name__)

ASK_WHO, SELECT_PRODUCTS, ENTER_QUANTITY = range(3)

# keys of context.user_data used by the order flow (never the user's own "agent" profile)
ORDER_KEYS = ("order", "edit_order_id", "edit_base_update_date", "current_product", "products", "edit_mode")


def clear_order_state(context):
    for key in ORDER_KEYS:
        context.user_data.pop(key, None)

# ================= Helper functions =================


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_order_state(context)
    await main_menu(update, context)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_order_state(context)
    await update.effective_message.reply_text("Bekor qilindi.")
    await main_menu(update, context)
    return ConversationHandler.END


def _product_button_text(product, qty):
    return f"{product['name']} (soni: {qty})"


def build_product_keyboard(order, products):
    keyboard = []
    row = []

    for p in products:
        existing_qty = next(
            (i['quantity'] for i in order['items'] if i['product_id'] == p['id']),
            0
        )
        row.append(_product_button_text(p, existing_qty))

        # If we have 2 buttons in this row, add it to keyboard and reset
        if len(row) == 2:
            keyboard.append(row)
            row = []

    # If there's an odd number of products, add the last row too
    if row:
        keyboard.append(row)

    # Add the bottom action row
    keyboard.append(["Done", "Cancel"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


_BUTTON_RE = re.compile(r"^(.*) \(soni: [^)]*\)$")


def find_product_by_button(text, products):
    """Exact match of the pressed button (startswith() picked "Non" for "Non katta")."""
    m = _BUTTON_RE.match(text or "")
    name = m.group(1) if m else (text or "").strip()
    return next((p for p in products if p['name'] == name), None)


def order_items_from_api(order):
    return [
        {"product_id": i["product"]["id"], "quantity": i["quantity"]}
        for i in order.get("items") or []
        if i.get("product")
    ]


async def send_order_message(update, context, order):
    message_text = format_order_message(order)

    # 📩 Send message to user
    sent_msg = await send_order_text(context.bot, update.effective_chat.id, message_text, get_order_buttons(order))

    # 📨 Send to channel with deep link buttons
    ch_msg = await sending_post(context.bot, message_text, get_order_buttons(order, channel_mode=True))

    # 🛠 Save message IDs so the messages can be updated later
    patch_update_order(
        order_id=order["id"],
        telegram_id=update.effective_user.id,
        order_data={
            "user_chat_id": str(sent_msg.chat_id),
            "user_message_id": sent_msg.message_id,
            "channel_chat_id": str(CHANEL_ID) if ch_msg else None,
            "channel_message_id": ch_msg.message_id if ch_msg else None,
        }
    )
    return sent_msg



# ================= Order Start =================

async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = await get_profile(update, context)
    if not agent:
        await update.message.reply_text("Boshlash uchun /start ni bosing!")
        return ConversationHandler.END

    # a new order must never continue an old (unfinished) edit
    clear_order_state(context)

    keyboard = [["⬅️ Back"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text("Zakas egasini yozing:", reply_markup=reply_markup)
    return ASK_WHO

# ================= Ask for Who =================

async def ask_for_who(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        reply_target = update.callback_query.message
        user_id = update.callback_query.from_user.id
    elif update.message:
        reply_target = update.message
        user_id = update.effective_user.id
        for_who = (update.message.text or "").strip()
        if not for_who:
            await update.message.reply_text("Zakas egasini yozing:")
            return ASK_WHO
        if "edit_order_id" in context.user_data and context.user_data.get("order"):
            context.user_data["order"]["for_who"] = for_who
        else:
            context.user_data["order"] = {"for_who": for_who, "items": []}
    else:
        return ConversationHandler.END

    if not context.user_data.get("order"):
        await reply_target.reply_text("❌ Zakaz ma'lumotlari topilmadi. Qaytadan boshlang.")
        return ConversationHandler.END

    # 📦 Fetch products
    products = get_products(user_id)
    if not products:
        await reply_target.reply_text("❌ Mahsulotlar olinmadi. Iltimos keyinroq urinib ko'ring.")
        clear_order_state(context)
        return ConversationHandler.END
    context.user_data["products"] = products

    await reply_target.reply_text(
        "📦 Mahsulotni tanlang:",
        reply_markup=build_product_keyboard(context.user_data["order"], products)
    )
    return SELECT_PRODUCTS



# ================= Select Products =================
def order_items_equal(db_items, new_items):
    db_q = {}
    for i in db_items or []:
        if i.get("product"):
            db_q[i["product"]["id"]] = db_q.get(i["product"]["id"], 0) + i["quantity"]
    new_q = {}
    for i in new_items:
        new_q[i["product_id"]] = new_q.get(i["product_id"], 0) + i["quantity"]
    return db_q == new_q


async def _finish_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, order):
    telegram_id = update.effective_user.id
    order_id = context.user_data["edit_order_id"]

    current = get_order_by_id(order_id, telegram_id)
    if not current:
        await update.message.reply_text("❌ Zakas topilmadi yoki o'chirib yuborilgan!")
        return

    if current.get("is_delivered"):
        await update.message.reply_text("⚠️ Bu zakaz allaqachon yetqazib berilgan.")
        return

    if order_items_equal(current["items"], order["items"]) and (current.get("for_who") or "") == (order.get("for_who") or ""):
        await update.message.reply_text("ℹ️ Zakaz miqdori oldingisi bilan bir xil!.")
        return

    payload = {"for_who": order.get("for_who"), "items": order["items"]}
    if context.user_data.get("edit_base_update_date"):
        payload["base_update_date"] = context.user_data["edit_base_update_date"]

    response = update_order(order_id, telegram_id, payload)
    if not response or response.get("error"):
        status = (response or {}).get("status_code")
        if status == 409:
            await update.message.reply_text(
                "⚠️ Siz tahrirlayotgan paytda bu zakazni boshqa foydalanuvchi o'zgartirdi.\n"
                "O'zgarishlaringiz saqlanmadi. Mana zakazning hozirgi holati — qaytadan ✏️Tahrirlash tugmasini bosing:"
            )
            await send_order_text(context.bot, update.effective_chat.id, format_order_message(current), get_order_buttons(current))
        elif status == 406:
            await update.message.reply_text("⚠️ Bu zakaz allaqachon yetqazib berilgan.")
        elif status == 403:
            await update.message.reply_text("🚫 Sizda bu zakazni tahrirlash huquqi yo'q.")
        else:
            detail = (response or {}).get("detail")
            await update.message.reply_text(f"❌ Zakaz saqlanmadi. {detail or 'Serverga ulanishda xatolik.'}")
        return

    text = format_order_message(response)
    user_ok = await edit_message_in_channel(
        context.bot, response, text, get_order_buttons(response), get_order_buttons(response, channel_mode=True)
    )
    # the editor always sees the result (the original message may be in another person's chat)
    if not user_ok or str(response.get("user_chat_id")) != str(update.effective_chat.id):
        await send_order_text(context.bot, update.effective_chat.id, text, get_order_buttons(response))
    await update.message.reply_text("✅ Zakaz yangilandi.")


async def select_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else None
    text = update.message.text if update.message else None

    order = context.user_data.get('order')
    products = context.user_data.get('products')

    if order is None:
        logger.warning("select_products: missing order for user=%s", user_id)
        await update.message.reply_text("❌ Ichki xatolik: zakaz ma'lumotlari yo'q. Iltimos qaytadan boshlang.")
        await main_menu(update, context)
        return ConversationHandler.END

    if not products:
        products = get_products(user_id)
        if not products:
            await update.message.reply_text("❌ Mahsulotlar olinmadi. Iltimos keyinroq urinib ko'ring.")
            return SELECT_PRODUCTS
        context.user_data['products'] = products

    if text == 'Cancel':
        clear_order_state(context)
        await update.message.reply_text('Zakaz bekor qilindi.')
        await main_menu(update, context)
        return ConversationHandler.END

    if text == "Done":
        # Remove zero quantity items
        order["items"] = [i for i in order["items"] if i["quantity"] > 0]
        if not order["items"]:
            await update.message.reply_text("❌ Hech qanday mahsulot tanlanmadi!")
            clear_order_state(context)
            await main_menu(update, context)
            return ConversationHandler.END

        if context.user_data.get("edit_order_id"):
            await _finish_edit(update, context, order)
        else:
            # ✅ NEW order
            response = create_order({"for_who": order.get("for_who"), "items": order["items"]}, update.effective_user.id)
            if not response:
                await update.message.reply_text("❌ Zakaz saqlanmadi (serverda xatolik). Iltimos qaytadan urinib ko'ring.")
            else:
                await send_order_message(update, context, response)

        clear_order_state(context)
        await main_menu(update, context)
        return ConversationHandler.END

    selected = find_product_by_button(text, products)
    if not selected:
        await update.message.reply_text('Noto\'g\'ri mahsulot tanlandi. Iltimos tugmalardan birini bosing!')
        return SELECT_PRODUCTS

    context.user_data['current_product'] = selected
    await update.message.reply_text(f'✍️ {selected["name"]} sonini kiriting (mahsulot bo\'masa 0 ni yozing):', reply_markup=back_button)
    return ENTER_QUANTITY

# ================= Enter Quantity =================

async def enter_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    order = context.user_data.get('order')
    products = context.user_data.get('products') or []

    if order is None:
        await update.message.reply_text("❌ Zakaz ma'lumotlari topilmadi. Qaytadan boshlang.")
        await main_menu(update, context)
        return ConversationHandler.END

    if text == '⬅️ Back':
        context.user_data.pop('current_product', None)
        keyboard = build_product_keyboard(order, products)
        await update.message.reply_text('🔙 Boshqa mahsulotni tanlang:', reply_markup=keyboard)
        return SELECT_PRODUCTS

    if not text.isdigit():
        await update.message.reply_text('⚠️ Mahsulot soni raqam bo\'lishi kerak!!!. Qaytadan o\'rining yoki orqaga qaytish uchun  ⬅️ Back tugmasini bosing!:')
        return ENTER_QUANTITY

    qty = int(text)
    product = context.user_data.pop('current_product', None)
    if not product:
        await update.message.reply_text('Mahsulotni tanlang:', reply_markup=build_product_keyboard(order, products))
        return SELECT_PRODUCTS

    # Update only selected product
    existing_item = next((i for i in order['items'] if i['product_id'] == product['id']), None)
    if existing_item:
        if qty == 0:
            order['items'].remove(existing_item)
        else:
            existing_item['quantity'] = qty
    elif qty > 0:
        order['items'].append({'product_id': product['id'], 'quantity': qty})

    keyboard = build_product_keyboard(order, products)
    await update.message.reply_text(f'✅ {product["name"]} soni yangilandi!.\nKeyingi mahsulotni tanlang! \n<b>Tugatish uchun Done tugmasini bosing!</b>:', parse_mode="HTML",reply_markup=keyboard)
    return SELECT_PRODUCTS

# ================= Callback for Edit =================
async def start_edit_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # parse callback parts: order_edit_<order_id> or order_edit_<order_id>_<owner_id>
    parts = query.data.split("_")
    try:
        order_id = int(parts[2])
    except (ValueError, IndexError):
        await query.answer("❌ Noto'g'ri zakaz ID.", show_alert=True)
        return ConversationHandler.END

    clicker_id = query.from_user.id
    if not await get_profile(update, context):
        await query.answer("Boshlash uchun /start ni bosing!", show_alert=True)
        return ConversationHandler.END

    # fetched as the clicker: the backend checks if this user may see/edit the order
    order = get_order_by_id(order_id, clicker_id)
    if not order:
        await query.answer("🚫 Zakaz topilmadi yoki sizda bu zakazni tahrirlash huquqi yo'q.", show_alert=True)
        return ConversationHandler.END

    if order.get("is_delivered"):
        await query.answer("⚠️ Bu zakaz yetqazib berilgan va tahrir qilib bo'lmaydi!", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    logger.info("start_edit_order user=%s order=%s", clicker_id, order_id)

    # only order data is stored; the user's own profile ("agent") is not touched
    clear_order_state(context)
    context.user_data["edit_order_id"] = order_id
    context.user_data["edit_base_update_date"] = order.get("update_date")
    context.user_data["order"] = {
        "for_who": order.get("for_who"),
        "items": order_items_from_api(order),
    }

    await query.message.reply_text(f"✏️ {order_id} Sonli zakazni o'zgartirishga kirdingiz:")
    return await ask_for_who(update, context)


BACK_FILTER = filters.TEXT & filters.Regex("^⬅️ Back$")
# main menu buttons leave the order flow instead of being taken as a customer name / product
MENU_FILTER = filters.TEXT & filters.Regex("^(🧮Hisob-Kitob|👤Admin👤|📦 Mavjud zakaslar)$")


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.start import start
    clear_order_state(context)
    await start(update, context)
    return ConversationHandler.END

# one conversation for new orders and edits: two separate conversations could both be
# active for the same user and steal each other's messages
buyurtma_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.TEXT & filters.Regex('^📝Buyurtma📝$'), order_start),
        CallbackQueryHandler(start_edit_order, pattern=r"^order_edit_\d+(_\d+)?$"),
    ],
    states={
        ASK_WHO: [
            MessageHandler(BACK_FILTER | MENU_FILTER, back_to_main),
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_who),
        ],
        SELECT_PRODUCTS: [
            MessageHandler(BACK_FILTER | MENU_FILTER, back_to_main),
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_products),
        ],
        ENTER_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_quantity),
        ],
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('start', restart),
        MessageHandler(BACK_FILTER, back_to_main)
    ],
    per_user=True,
    allow_reentry=True,
)
