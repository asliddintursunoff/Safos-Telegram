from telegram.ext import ApplicationBuilder,CommandHandler,MessageHandler,filters,CallbackQueryHandler
from handlers.start import start,recieve_contact
from handlers.order import buyurtma_handler,edit_order_handler
from handlers.order_crud import callback_handler
from handlers.hisob_kitob_button import hisob_kitob_menu,hisob_kitob_conv
from handlers.admin_menu import admin_menu
from handlers.agents_total_order_price import agent_earnings_conv_handler
from handlers.admin_panel_products import products_conv_handler
from handlers.get_new_orders import existing_orders_handler
from config import BOT_TOKEN
from handlers.agents import agent_conv_handler
from handlers.order_info_prices import zakaz_hisobot_conv_handler
app = ApplicationBuilder().token(BOT_TOKEN).build()

#start
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.CONTACT, recieve_contact))
app.add_handler(buyurtma_handler)
app.add_handler(edit_order_handler)
app.add_handler(CallbackQueryHandler(callback_handler, pattern="^order_"))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🧮Hisob-Kitob$"), hisob_kitob_menu))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^👤Admin👤$"), admin_menu))

app.add_handler(agent_earnings_conv_handler)
app.add_handler(zakaz_hisobot_conv_handler)
app.add_handler(agent_conv_handler)
app.add_handler(products_conv_handler)

app.add_handler(existing_orders_handler)
app.add_handler(hisob_kitob_conv)

app.run_polling()
