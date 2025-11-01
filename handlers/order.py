from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from services.api import get_products, get_order_by_id, create_order, update_order, patch_update_order
from handlers.main_menu import main_menu
from keyboards.reply import back_button
from keyboards.inline import get_order_buttons
from formatter.order_post import format_order_message
from services.chanel import sending_post
from config import CHANEL_ID
from services.chanel import edit_message_in_channel
ASK_WHO, SELECT_PRODUCTS, ENTER_QUANTITY = range(3)

# ================= Helper functions =================


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)
    return ConversationHandler.END

def build_product_keyboard(order, products):
    keyboard = []
    row = []

    for p in products:
        existing_qty = next(
            (i['quantity'] for i in order['items'] if i['product_id'] == p['id']),
            0
        )
        button_text = f"{p['name']} (soni: {existing_qty})"
        row.append(button_text)

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


async def send_order_message(update, context, order):
    from formatter.order_post import format_order_message

    message_text = format_order_message(order)

    # 🧑 User message buttons (normal edit callback)
    user_buttons = get_order_buttons(order) if "id" in order else None

    # 📩 Send message to user
    if user_buttons:
        sent_msg = await update.message.reply_text(
            message_text,
            parse_mode="HTML",
            reply_markup=user_buttons
        )
    else:
        sent_msg = await update.message.reply_text(
            message_text,
            parse_mode="HTML"
        )

    # 📨 Send to channel with deep link buttons
    channel_message_id = None
    if "id" in order:
        channel_buttons = get_order_buttons(order, channel_mode=True)  # deep link edit
        ch_response = sending_post(message_text, channel_buttons)

        if ch_response and "result" in ch_response:
            channel_message_id = str(ch_response["result"]["message_id"])

        # 🛠 Update order record with message IDs
        patch_update_order(
            order_id=order["id"],
            telegram_id=update.effective_user.id,
            order_data={
                "user_chat_id": str(sent_msg.chat_id),
                "user_message_id": str(sent_msg.message_id),
                "channel_chat_id": str(CHANEL_ID) if channel_message_id else None,
                "channel_message_id": channel_message_id
            }
        )

    return sent_msg



# ================= Order Start =================

async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = context.user_data.get('agent')
    if not agent:
        await update.message.reply_text("Boshlash uchun /start ni bosing!")
        return ConversationHandler.END

    keyboard = [["⬅️ Back"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text("Zakas egasini yozing:", reply_markup=reply_markup)
    return ASK_WHO

# ================= Ask for Who =================

async def ask_for_who(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(update, Update) and update.callback_query:
        query = update.callback_query
        await query.answer()
        reply_target = query.message
        user_id = query.from_user.id
        is_editing = "edit_order_id" in context.user_data
        for_who = context.user_data.get("order", {}).get("for_who", "")
    elif isinstance(update, Update) and update.message:
        reply_target = update.message
        user_id = update.effective_user.id
        is_editing = False
        for_who = update.message.text
    else:
        return ConversationHandler.END

    # 🆕 Initialize or update the order in context
    if not is_editing:
        context.user_data["order"] = {
            "agent_id": context.user_data["agent"]["id"],
            "for_who": for_who,
            "items": []
        }
    else:
        context.user_data["order"]["for_who"] = for_who

    # 📦 Fetch products
    products = get_products(user_id)
    context.user_data["products"] = products

    # 🧾 Build the nice 2-column product keyboard with quantities
    order = context.user_data["order"]
    product_keyboard = build_product_keyboard(order, products)

    # 💬 Send product selection message
    await reply_target.reply_text(
        "📦 Mahsulotni tanlang:",
        reply_markup=product_keyboard
    )
    return SELECT_PRODUCTS



# ================= Select Products =================
def order_items_equal(db_items, new_items):
    if len(db_items) != len(new_items):
        return False

    # Sort both lists by product id to avoid mismatch
    db_sorted = sorted(db_items, key=lambda x: x["product"]["id"])
    new_sorted = sorted(new_items, key=lambda x: x["product_id"])

    for a, b in zip(db_sorted, new_sorted):
        if a["product"]["id"] != b["product_id"] or a["quantity"] != b["quantity"]:
            return False
    return True
import logging as logger
async def select_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Log incoming update and user
    user_id = update.effective_user.id if update.effective_user else None
    text = update.message.text if update.message else None
    logger.info("select_products called by user=%s text=%r context_keys=%s", user_id, text, list(context.user_data.keys()))

    # Defensive checks: ensure order and products exist
    order = context.user_data.get('order')
    products = context.user_data.get('products')

    if order is None:
        logger.warning("select_products: missing context.user_data['order'] for user=%s", user_id)
        await update.message.reply_text("❌ Ichki xatolik: zakaz ma'lumotlari yo'q. Iltimos /start ni bosing va qaytadan urinib ko'ring.")
        return ConversationHandler.END

    if products is None:
        logger.warning("select_products: missing context.user_data['products'], fetching fresh for user=%s", user_id)
        # try to fetch products again as fallback
        products = get_products(user_id)
        if not products:
            await update.message.reply_text("❌ Mahsulotlar olinmadi. Iltimos keyinroq urinib ko'ring.")
            return ConversationHandler.END
        context.user_data['products'] = products

    if text == 'Cancel':
        await update.message.reply_text('Zakaz bekor qilindi.')
        context.user_data.pop('order', None)
        context.user_data.pop('edit_order_id', None)
        context.user_data.pop('edit_mode', None)
        await main_menu(update, context)
        return ConversationHandler.END

    if text == "Done":
        telegram_id = update.effective_user.id
        order = context.user_data["order"]

        # Remove zero quantity items
        order["items"] = [i for i in order["items"] if i["quantity"] > 0]
        if not order["items"]:
            await update.message.reply_text("❌ Hech qanday mahsulot tanlanmadi!")
            context.user_data.pop("order", None)
            context.user_data.pop("edit_order_id", None)
            await main_menu(update, context)
            return ConversationHandler.END

        # --- replace the existing "if 'edit_order_id' in context.user_data" block ---
        if "edit_order_id" in context.user_data:
            # Fetch the order from DB first
            order_to_edit = get_order_by_id(context.user_data["edit_order_id"], telegram_id)
            
            if not order_to_edit:
                await update.message.reply_text("❌ Zakas topilmadi yoki o'chirib yuborilgan!")
                context.user_data.pop("edit_order_id", None)
                return ConversationHandler.END

            if order_to_edit.get("is_delivered"):
                await update.message.reply_text("⚠️ Bu zakaz allaqachon yetqazib berilgan.")
                context.user_data.pop("edit_order_id", None)
                context.user_data.pop("order", None)
                return ConversationHandler.END

            if order_items_equal(order_to_edit["items"], order["items"]):
                await update.message.reply_text("ℹ️ Zakaz miqdori oldingisi bilan bir xil!.")
                await main_menu(update, context)
                return ConversationHandler.END

            # ✅ Safe to update
            response = update_order(context.user_data["edit_order_id"], telegram_id, order)

            # Defensive checks: ensure we got a valid response with IDs
            if not response:
                logger.error("update_order returned None for order=%s user=%s", context.user_data["edit_order_id"], telegram_id)
                await update.message.reply_text("❌ Serverga ulanishda xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.")
                return ConversationHandler.END

            user_chat_id = response.get("user_chat_id")
            user_message_id = response.get("user_message_id")

            if not user_chat_id or not user_message_id:
                logger.error("update_order response missing message ids: %s", response)
                await update.message.reply_text("❌ Serverdan noto'g'ri javob olindi (message ids yo'q).")
                return ConversationHandler.END

            try:
                user_chat_id = int(user_chat_id)
                user_message_id = int(user_message_id)
            except (TypeError, ValueError):
                logger.exception("Invalid message ids returned by update_order: %s", response)
                await update.message.reply_text("❌ Serverdan noto'g'ri javob olindi (message ids format xato).")
                return ConversationHandler.END

            # Edit the user's message safely
            try:
                await context.bot.edit_message_text(
                    chat_id=user_chat_id,
                    message_id=user_message_id,
                    text=format_order_message(response),
                    parse_mode="HTML",
                    reply_markup=get_order_buttons(response)
                )
            except Exception:
                logger.exception("Failed to edit user message for order %s", context.user_data["edit_order_id"])
                await update.message.reply_text("❌ Xabarni yangilashda xatolik yuz berdi.")
                return ConversationHandler.END

            edit_message_in_channel(response, format_order_message(response), get_order_buttons(response, channel_mode=True))
            context.user_data.pop("edit_order_id", None)



        else:
            # ✅ NEW order
            response = create_order(order, telegram_id)
            await send_order_message(update, context, response)

        context.user_data.pop("order", None)
        await main_menu(update, context)
        return ConversationHandler.END





    selected = next((p for p in products if text.startswith(p['name'])), None)
    if not selected:
        await update.message.reply_text('Noto\'g\'ri mahsulot tanlandi. Iltimos tugmalardan birini bosing!')
        return SELECT_PRODUCTS

    context.user_data['current_product'] = selected
    await update.message.reply_text(f'✍️ {selected["name"]} sonini kiriting (mahsulot bo\'masa 0 ni yozing):', reply_markup=back_button)
    return ENTER_QUANTITY

# ================= Enter Quantity =================

async def enter_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    order = context.user_data['order']
    products = context.user_data['products']

    if text == '⬅️ Back':
        keyboard = build_product_keyboard(order, products)
        await update.message.reply_text('🔙 Boshqa mahsulotni tanlang:', reply_markup=keyboard)
        return SELECT_PRODUCTS

    if not text.isdigit():
        await update.message.reply_text('⚠️ Mahsulot soni raqam bo\'lishi kerak!!!. Qaytadan o\'rining yoki orqaga qaytish uchun  ⬅️ Ortga tugmasini bosing!:')
        return ENTER_QUANTITY

    qty = int(text)
    product = context.user_data.pop('current_product')

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

# ================= Conversation Handler =================

# buyurtma_handler = ConversationHandler(
#     entry_points=[MessageHandler(filters.TEXT & filters.Regex('^📝Buyurtma📝$'), order_start)],
#     states={
#         ASK_WHO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_who)],
#         SELECT_PRODUCTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_products)],
#         ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_quantity)],
#     },
#     fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
# )
buyurtma_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & filters.Regex('^📝Buyurtma📝$'), order_start)],
    states={
        ASK_WHO: [
            MessageHandler(filters.TEXT & filters.Regex("^⬅️ Back$"), back_to_main),
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_who),
        ],
        SELECT_PRODUCTS: [
            MessageHandler(filters.TEXT & filters.Regex("^⬅️ Back$"), back_to_main),
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_products),
        ],
        ENTER_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_quantity),
        ],
    },
    fallbacks=[
        CommandHandler('cancel', lambda u, c: ConversationHandler.END),
        MessageHandler(filters.Regex("^⬅️ Back$"), back_to_main)
    ],
    per_user=True
)

# ================= Callback for Edit =================

async def start_edit_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    logger.info("start_edit_order called by user=%s data=%r", query.from_user.id if query.from_user else None, query.data)

    order_id = int(query.data.split("_")[2])
    order = get_order_by_id(order_id, query.from_user.id)
    if not order:
        await query.message.reply_text("❌ Zakaz o'chirib yuborilgan yoki mavjud emas!")
        return ConversationHandler.END
    if order.get("is_delivered"):
        await query.message.reply_text("⚠️ Bu zakaz yetqazib berilgan!\nZakazni o'zgartirib bo'lmaydi!")
        return ConversationHandler.END

    # Prefill context.user_data for editing
    context.user_data["agent"] = {"id": order["agent"]["telegram_id"], **order["agent"]}
    context.user_data["edit_order_id"] = order_id
    context.user_data["order"] = {
        "for_who": order["for_who"],
        "items": [{"product_id": i["product"]["id"], "quantity": i["quantity"]} for i in order["items"]],
    }

    logger.info("start_edit_order populated context.user_data for user=%s edit_order_id=%s", query.from_user.id, order_id)

    await query.message.reply_text(f"✏️ {order_id} Sonli zakazni o'zgartirishga kirdingiz:")
    # Start ASK_WHO state -- this will call ask_for_who which sets products and sends keyboard
    return await ask_for_who(update, context)


from telegram.ext import CallbackQueryHandler
edit_order_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_edit_order, pattern=r"^order_edit_\d+$")],
    states={
        ASK_WHO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_who)],
        SELECT_PRODUCTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_products)],
        ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_quantity)],
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    per_user=True,
    per_message=True
    
      # make sure callback query triggers the handler
)
