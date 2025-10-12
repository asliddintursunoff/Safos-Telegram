from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from .main_menu import main_menu
from services.api import getting_one_agent, verify_telegram, get_order_by_id
from formatter.order_post import format_order_message
from handlers.order import get_order_buttons

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    # ✅ Step 1: check if user has agent_id saved
    agent_id = context.user_data.get("agent_id")
    agent = None
    if agent_id:
        agent = getting_one_agent(user.id, agent_id)

    # ✅ Step 2: if agent not found in memory, you can try to retrieve from backend (optional if backend allows)
    # If your backend can get agent by telegram_id directly, do it here.
    # Otherwise user must register again.

    # 🧭 Handle deep-link
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
            context.user_data["agent_id"] = agent_data.get("id")
            context.user_data["agent"] = agent_data
        else:
            context.user_data["agent_id"] = agent_id
            context.user_data["agent"] = agent

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

    # 🧍 Step 3: normal registration flow
    if agent:
        await update.message.reply_text("✅ Siz allaqachon ro'yxatdan o'tgansiz.")
        await main_menu(update, context)
        return

    # 🔐 Step 4: ask for phone number if not registered
    keyboard = [[KeyboardButton("📞 Raqamni yuborish", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Salom! Ro‘yxatdan o‘tish uchun telefon raqamingizni yuboring 📲",
        reply_markup=reply_markup
    )



from telegram import Update
from telegram.ext import ContextTypes
from .main_menu import main_menu
from services.api import verify_telegram

async def recieve_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("Iltimos, telefon raqamingizni yuborish tugmasidan foydalaning 📞")
        return

    phone_number = contact.phone_number
    telegram_id = update.effective_user.id

    # ✅ verify and attach telegram id
    agent = verify_telegram(phone_number, telegram_id)
    if agent:
        context.user_data["agent_id"] = agent["id"]
        context.user_data["agent"] = agent
        await update.message.reply_text(
            f"✅ Salom {agent['first_name']}! Siz {agent['role']} sifatida ro‘yxatdan o‘tdingiz."
        )
        await main_menu(update, context)
    else:
        await update.message.reply_text(
            "❌ Telefon raqamingiz topilmadi. Admin bilan bog‘laning."
        )
