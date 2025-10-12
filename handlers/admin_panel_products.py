from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from services.api import get_products, creating_product, update_product, delete_product
from .admin_menu import admin_menu

# States for ConversationHandler
PRODUCTS_MENU = 20
SELECT_PRODUCT = 21
UPDATE_FIELD = 22
UPDATE_VALUE = 23
DELETE_PRODUCT = 24
ADD_PRODUCT = 25


async def products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    buttons = [
        ["Qo'shish"],
        ["O'zgartirish"],
        ["O'chirish"],
        ["⬅️ Ortga"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    products = get_products(update.effective_user.id)
    products_text = "📦 <b>Mahsulotlar:</b>\n\n" + "\n".join([
                        f"🆔 {p['id']} — <b>{p['name'].capitalize()}</b>\n"
                        f"💰 {p['price']:,.0f} so'm / {p['unit']}"
                        for p in products
                    ]) if products else "❌ Hech qanday mahsulot topilmadi."

    await update.message.reply_text(
        f"🛠️ Siz Mahsulotlar bo'limidasiz!\n{products_text}\n\nTugmalardan birini tanlang:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return PRODUCTS_MENU

async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Qo'shish":
        await update.message.reply_text(
            "Yangi mahsulot qo'shish uchun quyidagi ma'lumotlarni kiriting:\n"
            "Nomi, narxi va o'lchov birligini vergul bilan ajratib yozing <b>(masalan: Olma, 10000, kg):\nbirlik faqat dona va kg!,\b>",parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_PRODUCT
    elif update.message.text == "O'zgartirish":
        products = get_products(update.effective_user.id)
        if not products:
            await update.message.reply_text(
                "O'zgartirish uchun mahsulotlar topilmadi.",
                reply_markup=ReplyKeyboardMarkup([["⬅️ Ortga"]], resize_keyboard=True)
            )
            return PRODUCTS_MENU
        buttons = [[f"{p['id']} - {p['name']}"] for p in products] + [["⬅️ Ortga"]]
        reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        await update.message.reply_text(
            "O'zgartirmoqchi bo'lgan mahsulotni tanlang:",
            reply_markup=reply_markup
        )
        return SELECT_PRODUCT
    elif update.message.text == "O'chirish":
        products = get_products(update.effective_user.id)
        if not products:
            await update.message.reply_text(
                "O'chirish uchun mahsulotlar topilmadi.",
                reply_markup=ReplyKeyboardMarkup([["⬅️ Ortga"]], resize_keyboard=True)
            )
            return PRODUCTS_MENU
        buttons = [[f"{p['id']} - {p['name']}"] for p in products] + [["⬅️ Ortga"]]
        reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        context.user_data["valid_product_ids"] = [str(p['id']) for p in products]  # Store valid IDs
        await update.message.reply_text(
            "O'chirmoqchi bo'lgan mahsulotni tanlang:",
            reply_markup=reply_markup
        )
        return DELETE_PRODUCT
    elif update.message.text == "⬅️ Ortga":
        await admin_menu(update, context)
        return ConversationHandler.END
    return PRODUCTS_MENU

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        name, price, unit = [x.strip() for x in update.message.text.split(",")]
        price = float(price)
        telegram_id = update.effective_user.id
        result = creating_product(telegram_id, name, price, unit)
        if result:
            await update.message.reply_text(
                f"Mahsulot muvaffaqiyatli qo'shildi: {name} ({price} {unit})"
            )
        else:
            await update.message.reply_text("Xatolik yuz berdi, mahsulot qo'shilmadi.")
    except ValueError:
        await update.message.reply_text(
            "Noto'g'ri format. Iltimos, nomi, narxi va o'lchov birligini vergul bilan ajrating (masalan: Olma, 10000, kg):"
        )
        return ADD_PRODUCT
    return await products_menu(update, context)


async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "⬅️ Ortga":
        return await products_menu(update, context)

    try:
        product_id_str = text.split(" - ")[0].strip()
        products = get_products(update.effective_user.id)
        if product_id_str not in [str(p['id']) for p in products]:
            raise ValueError("Invalid product ID")

        context.user_data["selected_product_id"] = int(product_id_str)

        buttons = [["name"], ["price"], ["unit"], ["⬅️ Ortga"]]
        reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "O'zgartirmoqchi bo'lgan maydonni tanlang:",
            reply_markup=reply_markup
        )
        return UPDATE_FIELD

    except (ValueError, IndexError):
        products = get_products(update.effective_user.id)
        buttons = [[f"{p['id']} - {p['name']}"] for p in products] + [["⬅️ Ortga"]]
        await update.message.reply_text(
            "❌ Noto'g'ri tanlov. Iltimos, ro'yxatdan mahsulotni tugma orqali tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
        )
        return SELECT_PRODUCT


async def update_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "⬅️ Ortga":
        return await products_menu(update, context)

    context.user_data["field_to_update"] = text
    field_name = {"name": "nomi", "price": "narxi", "unit": "o'lchov birligi"}[text]

    if text == "unit":
        buttons = [["kg", "dona"], ["⬅️ Ortga"]]
        reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            f"Yangi {field_name} ni tanlang:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"Yangi {field_name} ni kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )

    return UPDATE_VALUE



async def update_product_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    product_id = context.user_data.get("selected_product_id")
    field = context.user_data.get("field_to_update")

    if not product_id or not field:
        await update.message.reply_text("⚠️ Xatolik. Iltimos, mahsulotni qayta tanlang.")
        return await products_menu(update, context)

    products = get_products(telegram_id)
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        await update.message.reply_text("❌ Mahsulot topilmadi.")
        return await products_menu(update, context)

    name = product["name"]
    price = product["price"]
    unit = product["unit"]

    if field == "name":
        name = update.message.text.strip()

    elif field == "price":
        try:
            price = float(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("❌ Narx raqam bo'lishi kerak.")
            return UPDATE_VALUE

    elif field == "unit":
        new_unit = update.message.text.strip()
        if new_unit not in ["kg", "dona"]:
            buttons = [["kg", "dona"], ["⬅️ Ortga"]]
            await update.message.reply_text(
                "❌ Noto'g'ri o'lchov birligi. Iltimos, 'kg' yoki 'dona' ni tanlang:",
                reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
            )
            return UPDATE_VALUE
        unit = new_unit

    # Call your API
    result = update_product(telegram_id, product_id, name, price, unit)
    if result:
        await update.message.reply_text(f"✅ {field} muvaffaqiyatli o'zgartirildi.")
    else:
        await update.message.reply_text("❌ Xatolik yuz berdi, o'zgarish amalga oshmadi.")

    return await products_menu(update, context)


async def delete_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "⬅️ Ortga":
        return await products_menu(update, context)
    try:
        product_id_str = update.message.text.split(" - ")[0]
        if product_id_str not in context.user_data.get("valid_product_ids", []):
            raise ValueError("Invalid product ID")
        product_id = int(product_id_str)
        telegram_id = update.effective_user.id
        result = delete_product(telegram_id, product_id)
        if result:
            await update.message.reply_text("Mahsulot muvaffaqiyatli o'chirildi.")
        else:
            await update.message.reply_text("Xatolik yuz berdi, mahsulot o'chirilmadi.")
    except (ValueError, IndexError):
        products = get_products(update.effective_user.id)
        buttons = [[f"{p['id']} - {p['name']}"] for p in products] + [["⬅️ Ortga"]]
        await update.message.reply_text(
            "Noto'g'ri tanlov. Iltimos, ro'yxatdan mahsulotni tugma orqali tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return DELETE_PRODUCT
    return await products_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Amal bekor qilindi.",
        reply_markup=ReplyKeyboardRemove()
    )
    return await products_menu(update, context)
from telegram.ext import Application, ConversationHandler, MessageHandler, filters
products_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("🍎 Mahsulotlar"), products_menu)
    ],
    states={
        PRODUCTS_MENU: [
            MessageHandler(
                filters.Regex("^(Qo'shish|O'zgartirish|O'chirish|⬅️ Ortga)$"),
                start_add_product
            )
        ],
        ADD_PRODUCT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_product)
        ],
        SELECT_PRODUCT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_product)
        ],
        UPDATE_FIELD: [
            MessageHandler(filters.Regex("^(name|price|unit|⬅️ Ortga)$"), update_field)
        ],
        UPDATE_VALUE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, update_product_field)
        ],
        DELETE_PRODUCT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, delete_product_handler)
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex("^(cancel|⬅️ Ortga)$"), cancel)
    ],
    allow_reentry=True
)

