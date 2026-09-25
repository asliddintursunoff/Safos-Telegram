from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from services.profile import get_profile

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = await get_profile(update, context, refresh=True)
    if not agent:
        await update.effective_message.reply_text("You must register first with /start")
        return

    role = agent.get("role")
    if role == "dostavchik":
        buttons = [["📝Buyurtma📝"], ["📦 Mavjud zakaslar"],["🧮Hisob-Kitob"]]

    elif role == "admin":
        buttons = [["📝Buyurtma📝"],["📦 Mavjud zakaslar"],["👤Admin👤"],["🧮Hisob-Kitob"]]
    else:
        buttons = [["📝Buyurtma📝"],["🧮Hisob-Kitob"]]

    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.effective_message.reply_text("Siz bosh menyudasiz!\nTugmalardan birini tanlang:", reply_markup=reply_markup)
