from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from .main_menu import main_menu
from services.api import verify_telegram, get_order_by_id
from services.profile import get_profile, remember_profile
from services.chanel import send_order_text
from formatter.order_post import format_order_message
from keyboards.inline import get_order_buttons

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    # ✅ own profile (from backend, so it also works after the bot restarts)
    agent = await get_profile(update, context, refresh=True)

    # 🧭 Handle deep-link (✏️Tahrirlash button in the channel)
    if args and args[0].startswith("edit_"):
        try:
            order_id = int(args[0].split("_")[1])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Noto‘g‘ri buyurtma ID.")
            return

        order = get_order_by_id(order_id, user.id)
        if not order:
            await update.message.reply_text("❌ Buyurtma topilmadi yoki sizda ruxsat yo'q.")
            return

        if order.get("is_delivered"):
            await update.message.reply_text("⚠️ Bu buyurtma allaqachon yetkazilgan va tahrir qilib bo‘lmaydi.")
            return

        # only show the order with its buttons; editing starts with the ✏️ button.
        # The user's own profile is NOT replaced with the order owner's profile.
        await send_order_text(context.bot, update.effective_chat.id, format_order_message(order), get_order_buttons(order))
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


async def recieve_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("Iltimos, telefon raqamingizni yuborish tugmasidan foydalaning 📞")
        return

    # only the user's own contact can be used to log in (not a forwarded contact of someone else)
    if contact.user_id != update.effective_user.id:
        await update.message.reply_text("❌ Iltimos, o'zingizning raqamingizni tugma orqali yuboring 📞")
        return

    phone_number = contact.phone_number
    telegram_id = update.effective_user.id

    # ✅ verify and attach telegram id
    agent = verify_telegram(phone_number, telegram_id)
    if agent:
        remember_profile(context, agent)
        await update.message.reply_text(
            f"✅ Salom {agent['first_name']}! Siz {agent['role']} sifatida ro‘yxatdan o‘tdingiz."
        )
        await main_menu(update, context)
    else:
        await update.message.reply_text(
            "❌ Telefon raqamingiz topilmadi. Admin bilan bog‘laning."
        )
