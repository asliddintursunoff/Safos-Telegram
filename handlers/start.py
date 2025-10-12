from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from .main_menu import main_menu
from services.api import verify_telegram, get_order_by_id
from formatter.order_post import format_order_message
from handlers.order import ask_for_who, get_order_buttons

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args  # arguments from deep link

    # 1️⃣ Handle deep-link like: /start edit_71
    if args and args[0].startswith("edit_"):
        try:
            order_id = int(args[0].split("_")[1])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Noto‘g‘ri buyurtma ID.")
            return

        order = get_order_by_id(order_id, user.id)
        if not order:
            await update.message.reply_text("❌ Buyurtma topilmadi.")
            return

        # ⚠️ If delivered — just inform
        if order.get("is_delivered"):
            await update.message.reply_text("⚠️ Bu buyurtma allaqachon yetkazilgan va tahrir qilib bo‘lmaydi.")
            return

        # 📨 Send order message to the user — just view mode, not edit mode yet
        message_text = format_order_message(order)
        buttons = get_order_buttons(order)
        sent_msg = await update.message.reply_text(
            text=message_text,
            parse_mode="HTML",
            reply_markup=buttons
        )

        # Store order context for later editing (if user clicks edit)
        agent_data = order.get("agent")
        if agent_data:
            context.user_data["agent"] = {"id": agent_data.get("telegram_id"), **agent_data}
        else:
            context.user_data["agent"] = {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name or "",
                "username": user.username or ""
            }

        context.user_data["bot_message_id"] = sent_msg.message_id
        context.user_data["user_chat_id"] = sent_msg.chat.id
        context.user_data["edit_order_id"] = order_id
        context.user_data["order"] = {
            "for_who": order["for_who"],
            "items": [
                {"product_id": item["product"]["id"], "quantity": item["quantity"]}
                for item in order["items"]
            ]
        }

        # ✅ Notice: No edit mode here — just showing order to the user
        return

    # 2️⃣ Normal registration flow
    if "agent" in context.user_data:
        await update.message.reply_text("✅ Siz allaqachon ro'yxatdan o'tgansiz.")
        return

    # 🔐 Registration keyboard
    keyboard = [[KeyboardButton("📞 Raqamni yuborish", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(
        "Salom! Ro‘yxatdan o‘tish uchun telefon raqamingizni yuboring 📲",
        reply_markup=reply_markup
    )



async def recieve_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("Please use the button to send your phone number.")
        return
    
    phone_number = contact.phone_number
    telegram_id = update.effective_user.id

    agent = verify_telegram(phone_number, telegram_id)
    if agent:
        context.user_data["agent"] = agent
        await update.message.reply_text(
            f"Hello {agent['first_name']}! You are verified as {agent['role']}"
        )
        await main_menu(update, context)
    else:
        await update.message.reply_text("Phone number not found. Contact admin.")
