from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from .main_menu import main_menu
from services.api import verify_telegram, get_order_by_id, getting_one_agent
from formatter.order_post import format_order_message
from handlers.order import get_order_buttons

# 🧭 /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args  # for deep link start/edit

    # 1️⃣ Check if user already registered in backend
    agent = getting_one_agent(user.id)
    if agent:
        context.user_data["agent"] = agent

    # 2️⃣ Handle deep-link like: /start edit_71
    if args and args[0].startswith("edit_"):
        try:
            order_id = int(args[0].split("_")[1])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Noto‘g‘ri buyurtma ID.")
            return

        # 🚀 fetch order from backend, always authenticated
        order = get_order_by_id(order_id, user.id)
        if not order:
            await update.message.reply_text("❌ Buyurtma topilmadi.")
            return

        # ⚠️ delivered already
        if order.get("is_delivered"):
            await update.message.reply_text("⚠️ Bu buyurtma allaqachon yetkazilgan va tahrir qilib bo‘lmaydi.")
            return

        message_text = format_order_message(order)
        buttons = get_order_buttons(order)
        sent_msg = await update.message.reply_text(
            text=message_text,
            parse_mode="HTML",
            reply_markup=buttons
        )

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
        return

    # 3️⃣ Normal registration flow
    if agent:
        await update.message.reply_text("✅ Siz allaqachon ro'yxatdan o'tgansiz.")
        await main_menu(update, context)
        return

    # 📨 Registration keyboard
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



from telegram import Update
from telegram.ext import ContextTypes
from .main_menu import main_menu
from services.api import verify_telegram

# 📲 Contact handler
async def recieve_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("Iltimos, telefon raqamingizni yuborish tugmasidan foydalaning 📞")
        return

    phone_number = contact.phone_number
    telegram_id = update.effective_user.id

    # Verify or attach telegram_id through backend
    agent = verify_telegram(phone_number, telegram_id)
    if agent:
        context.user_data["agent"] = agent
        await update.message.reply_text(
            f"✅ Salom {agent['first_name']}! Siz {agent['role']} sifatida ro‘yxatdan o‘tdingiz."
        )
        await main_menu(update, context)
    else:
        await update.message.reply_text(
            "❌ Telefon raqamingiz topilmadi. Admin bilan bog‘laning."
        )
