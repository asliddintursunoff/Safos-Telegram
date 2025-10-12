from telegram import Update, ReplyKeyboardMarkup,CopyTextButton
from telegram.ext import ContextTypes

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = context.user_data.get("agent")
    if not agent:
        await update.message.reply_text("You must register first with /start")
        return

    if agent["role"] == "agent":
        buttons = [["📝Buyurtma📝"],["🧮Hisob-Kitob"]]
    elif agent["role"] == "dostavchik":
        buttons = [["📝Buyurtma📝"], ["📦 Mavjud zakaslar"],["🧮Hisob-Kitob"]]

    elif agent["role"] == "admin":
        buttons = [["📝Buyurtma📝"],["📦 Mavjud zakaslar"],["👤Admin👤"],["🧮Hisob-Kitob"]]

    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text("Siz bosh menyudasiz!\nTugmalardan birini tanlang:", reply_markup=reply_markup)

    

