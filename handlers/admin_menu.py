from telegram import Update,ReplyKeyboardMarkup
from telegram.ext import ContextTypes,ConversationHandler
from services.profile import get_profile
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = await get_profile(update, context)
    if not agent or agent.get("role") != "admin":
        await update.effective_message.reply_text("🚫 Bu bo'lim faqat admin uchun.")
        return

    buttons = [
        ["💰 Zakaz hisobot", "💵 Agent daromadlari"],  # row 1
        ["🚚 Dostavchiklar", "👥 Agentlar"],[ "🍎 Mahsulotlar"],  # row 2
        ["⬅️ Ortga"]  # back button in its own row
    ]
    reply_markup = ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
    
    )
    await update.effective_message.reply_text(
        "🛠️ Siz Admin paneldasiz!\nTugmalardan birini tanlang:", 
        reply_markup=reply_markup
    )

# async def products_menu(update:Update,context:ContextTypes.DEFAULT_TYPE):
#     products = get_products(update.effective_user.id)
#     await update.effective_message.reply_text(f"{products}")
#     buttons = [["Qo'shish"],["O'zgartirish"],["O'chirish"],["⬅️ Ortga"]]
#     await update.message.reply_text(
#         "🛠️ Siz Mahsulotlar bo'limidasiz!\nTugmalardan birini tanlang:", 
#         reply_markup=buttons
#     )


