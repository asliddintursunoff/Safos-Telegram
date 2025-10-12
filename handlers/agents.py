from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters, 
    ConversationHandler
)
from datetime import datetime
from services.api import getting_all_agents,get_users_salary,adding_salary
AGENT_ACTION, SELECT_AGENT_FOR_SALARY, SELECT_SALARY_ACTION, INPUT_DATE, INPUT_DATE_RANGE, INPUT_SALARY_AMOUNT, CRUD_ACTION = range(50,57)
FIELD_MAP = {
    "Ism": "first_name",
    "Familiya": "last_name",
    "Telefon raqami": "phone_number",
    "Foiz (%)": "percentage",
    "Rol": "role"
}


async def agents_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    agents = getting_all_agents(telegram_id)

    if not agents:
        await update.message.reply_text("📭 Hozircha agentlar yo‘q.")
        return ConversationHandler.END

    # 🧾 Build a beautiful agent list
    message = "👥 <b>Agentlar ro‘yxati:</b>\n\n"
    for agent in agents:
        message += (
            f"🆔 <b>{agent['id']}</b> | "
            f"👤 {agent['first_name']} {agent['last_name']}\n"
            f"🪙 Qolgan maosh: <b>{agent['remaining_salary']:,} so'm</b>\n"
            f"🧭 Rol: <b>{agent['role']}</b>\n\n"
        )

    # 📌 Actions
    buttons = [
        ["💰 Pullar"], 
        ["🛠️ Agentlarni boshqarish"], 
        ["⬅️ Ortga"]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(
        message, 
        parse_mode="HTML", 
        reply_markup=reply_markup
    )
    return AGENT_ACTION


async def choose_agent_for_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    agents = getting_all_agents(telegram_id)

    keyboard = [
        [InlineKeyboardButton(f"{a['first_name']} {a['last_name']}", callback_data=f"agent_salary:{a['id']}")]
        for a in agents
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "💰 Agentni tanlang:",
        reply_markup=reply_markup
    )
    return SELECT_AGENT_FOR_SALARY

async def agent_salary_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    agent_id = int(query.data.split(":")[1])
    context.user_data["selected_agent_id"] = agent_id

    buttons = [
        ["📅 Zakaz pullari"], 
        ["➕ Oyliq qo‘shish"], 
        ["⬅️ Ortga"]
    ]
    await query.message.reply_text(
        "Tanlang:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return SELECT_SALARY_ACTION
async def salary_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.message.text
    telegram_id = update.effective_user.id
    agent_id = context.user_data.get("selected_agent_id")

    if action == "📅 Zakaz pullari":
        buttons = [
            ["📆 Bugun", "📅 Sana"], 
            ["📊 Oraliqdagi sana"], 
            ["⬅️ Ortga"]
        ]
        await update.message.reply_text(
            "Qaysi oraliqni tanlaysiz?",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        
        return INPUT_DATE

    elif action == "➕ Oyliq qo‘shish":
        await update.message.reply_text("🪙 Agentga qo‘shmoqchi bo‘lgan summani kiriting:")
        return INPUT_SALARY_AMOUNT
    elif action == "⬅️ Ortga":
        # 🔙 go back to agent list or admin menu
        await agents_entry(update, context)
        return AGENT_ACTION


def validate_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        return None

async def get_salary_for_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_input = update.message.text
    telegram_id = update.effective_user.id
    agent_id = context.user_data["selected_agent_id"]

    # 📅 Determine which query to use
    if date_input == "📆 Bugun":
        result = get_users_salary(telegram_id, agent_id, today_only=True)
    else:
        date_obj = validate_date(date_input)
        if not date_obj:
            await update.message.reply_text("❌ Sana noto‘g‘ri formatda. Masalan: 12-10-2025")
            return INPUT_DATE
        result = get_users_salary(telegram_id, agent_id, which_day=date_obj.strftime("%Y-%m-%d"))

    # 🧮 Handle different types of result (dict or int)
    amount = 0
    if isinstance(result, dict):
        amount = result.get("total_price", 0)
    elif isinstance(result, int) or isinstance(result, float):
        amount = result
    else:
        amount = 0

    await update.message.reply_text(
        f"🪙 <b>Agent zakaz pullari:</b> {amount:,} so'm",
        parse_mode="HTML"
    )

    return AGENT_ACTION


async def add_salary_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    agent_id = context.user_data["selected_agent_id"]

    try:
        amount = int(update.message.text)
        response = adding_salary(telegram_id, agent_id, amount)
        if response:
            await update.message.reply_text(f"✅ {amount:,} so‘m agentga qo‘shildi.")
        else:
            await update.message.reply_text("❌ Maosh qo‘shishda xatolik.")
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting.")
        return INPUT_SALARY_AMOUNT

    return AGENT_ACTION

async def crud_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        ["➕ Qo‘shish", "✏️ Tahrirlash", "🗑 O‘chirish"],
        ["⬅️ Ortga"]
    ]
    await update.message.reply_text(
        "🛠️ Agentlarni boshqarish menyusi:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return CRUD_ACTION

from .admin_menu import admin_menu
async def go_back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔙 Bosh menyuga qaytdingiz.")
    await admin_menu(update, context)  # 👈 show admin menu again
    return ConversationHandler.END


from services.api import deleting_agent,updating_agent,creating_agent
####################
CREATE_AGENT_FIRST, CREATE_AGENT_LAST, CREATE_AGENT_PHONE, CREATE_AGENT_PERCENT, CREATE_AGENT_ROLE, SELECT_AGENT_UPDATE, UPDATE_FIELD,UPDATE_VALUE, SELECT_AGENT_DELETE,DELETE_CONFIRM = range(57, 67)

async def create_agent_start(update, context):
    await update.message.reply_text("✍️ Agentning ismini kiriting:")
    return CREATE_AGENT_FIRST

async def create_agent_first(update, context):
    context.user_data["first_name"] = update.message.text
    await update.message.reply_text("✍️ Familiyani kiriting:")
    return CREATE_AGENT_LAST

async def create_agent_last(update, context):
    context.user_data["last_name"] = update.message.text
    await update.message.reply_text("📱 Telefon raqamini kiriting:")
    return CREATE_AGENT_PHONE

async def create_agent_phone(update, context):
    context.user_data["phone_number"] = update.message.text
    await update.message.reply_text("💰 Agent foizini kiriting (masalan 10):")
    return CREATE_AGENT_PERCENT

async def create_agent_percent(update, context):
    try:
        context.user_data["percentage"] = int(update.message.text)
        buttons = [["agent"], ["dostavchik"]]
        await update.message.reply_text("🧭 Agent rolini tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return CREATE_AGENT_ROLE
    except ValueError:
        await update.message.reply_text("❌ Iltimos, raqam kiriting:")
        return CREATE_AGENT_PERCENT

async def create_agent_role(update, context):
    telegram_id = update.effective_user.id
    data = context.user_data
    role = update.message.text

    response = creating_agent(
        telegram_id,
        data["first_name"],
        data["last_name"],
        data["phone_number"],
        data["percentage"],
        role
    )
    if response:
        await update.message.reply_text("✅ Agent muvaffaqiyatli qo‘shildi!")
    else:
        await update.message.reply_text("❌ Xatolik yuz berdi.")
    return await go_back_to_admin(update, context)


async def select_agent_to_update(update, context):
    telegram_id = update.effective_user.id
    agents = getting_all_agents(telegram_id)
    keyboard = [
        [InlineKeyboardButton(f"{a['first_name']} {a['last_name']}", callback_data=f"update:{a['id']}")]
        for a in agents
    ]
    await update.message.reply_text(
        "✏️ Agentni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_AGENT_UPDATE


async def update_agent_callback(update, context):
    query = update.callback_query
    await query.answer()
    agent_id = int(query.data.split(":")[1])
    context.user_data["update_agent_id"] = agent_id

    buttons = [
        ["Ism", "Familiya"],
        ["Telefon raqami", "Foiz (%)", "Rol"],
        ["⬅️ Ortga"]
    ]
    await query.message.reply_text(
        "✏️ Qaysi maydonni tahrirlaysiz?",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return UPDATE_FIELD


async def update_field(update, context):
    field_label = update.message.text
    if field_label == "⬅️ Ortga":
        return await crud_menu(update, context)

    if field_label not in FIELD_MAP:
        await update.message.reply_text("❌ Noto‘g‘ri tanlov.")
        return UPDATE_FIELD

    field = FIELD_MAP[field_label]
    context.user_data["update_field"] = field
    context.user_data["update_field_label"] = field_label

    await update.message.reply_text(f"✍️ Yangi qiymatni kiriting ({field_label}):")
    return UPDATE_VALUE

from services.api import getting_one_agent
async def update_agent_field(update, context):
    telegram_id = update.effective_user.id
    agent_id = context.user_data["update_agent_id"]
    field = context.user_data["update_field"]
    field_label = context.user_data["update_field_label"]
    new_value = update.message.text

    # Convert percentage to number if needed
    if field == "percentage":
        try:
            new_value = float(new_value)
        except ValueError:
            await update.message.reply_text("❌ Foiz uchun faqat raqam kiriting.")
            return UPDATE_VALUE

    # Get current agent data
    agent_data = getting_one_agent(telegram_id, agent_id)
    if not agent_data:
        await update.message.reply_text("❌ Agent topilmadi.")
        return AGENT_ACTION

    # Update payload
    updated_data = {
        "first_name": agent_data["first_name"],
        "last_name": agent_data["last_name"],
        "phone_number": agent_data["phone_number"],
        "percentage": agent_data["percentage"],
        "role": agent_data["role"]
    }
    updated_data[field] = new_value

    # Call update API
    result = updating_agent(
        telegram_id,
        agent_id,
        updated_data["first_name"],
        updated_data["last_name"],
        updated_data["phone_number"],
        updated_data["percentage"],
        updated_data["role"]
    )

    if result:
        await update.message.reply_text(f"✅ {field_label} yangilandi.")
    else:
        await update.message.reply_text("❌ Xatolik yuz berdi.")

    # 🔁 Show buttons again so user can update more fields
    buttons = [
        ["Ism", "Familiya"],
        ["Telefon raqami", "Foiz (%)", "Rol"],
        ["⬅️ Ortga"]
    ]
    await update.message.reply_text(
        "✏️ Qaysi maydonni yana tahrirlaysiz?",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return UPDATE_FIELD




async def select_agent_to_delete(update, context):
    telegram_id = update.effective_user.id
    agents = getting_all_agents(telegram_id)
    keyboard = [[InlineKeyboardButton(f"{a['first_name']} {a['last_name']}", callback_data=f"delete:{a['id']}")] for a in agents]
    await update.message.reply_text("🗑 O‘chirish uchun agentni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_AGENT_DELETE

async def delete_agent_callback(update, context):
    query = update.callback_query
    await query.answer()
    agent_id = int(query.data.split(":")[1])
    telegram_id = query.from_user.id

    response = deleting_agent(telegram_id, agent_id)
    if response:
        await query.message.reply_text("🗑 Agent muvaffaqiyatli o‘chirildi!")
    else:
        await query.message.reply_text("❌ Xatolik yuz berdi.")
    return await go_back_to_admin(update, context)





agent_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^👥 Agentlar$"), agents_entry)],
    states={
        AGENT_ACTION: [
            MessageHandler(filters.Regex("^💰 Pullar$"), choose_agent_for_salary),
            MessageHandler(filters.Regex("^🛠️ Agentlarni boshqarish$"), crud_menu),
        ],

        # 💰 Salary flow
        SELECT_AGENT_FOR_SALARY: [CallbackQueryHandler(agent_salary_callback, pattern="^agent_salary:")],
        SELECT_SALARY_ACTION: [MessageHandler(filters.TEXT, salary_actions)],
        INPUT_DATE: [MessageHandler(filters.TEXT, get_salary_for_date)],
        INPUT_SALARY_AMOUNT: [MessageHandler(filters.TEXT, add_salary_amount)],

        # ➕🗑✏️ CRUD main menu
        CRUD_ACTION: [
            MessageHandler(filters.Regex("^➕ Qo‘shish$"), create_agent_start),
            MessageHandler(filters.Regex("^✏️ Tahrirlash$"), select_agent_to_update),
            MessageHandler(filters.Regex("^🗑 O‘chirish$"), select_agent_to_delete),
        ],

        # ➕ Create flow
        CREATE_AGENT_FIRST: [MessageHandler(filters.TEXT, create_agent_first)],
        CREATE_AGENT_LAST: [MessageHandler(filters.TEXT, create_agent_last)],
        CREATE_AGENT_PHONE: [MessageHandler(filters.TEXT, create_agent_phone)],
        CREATE_AGENT_PERCENT: [MessageHandler(filters.TEXT, create_agent_percent)],
        CREATE_AGENT_ROLE: [MessageHandler(filters.TEXT, create_agent_role)],

        # ✏️ Update flow
        SELECT_AGENT_UPDATE: [CallbackQueryHandler(update_agent_callback, pattern="^update:")],
        UPDATE_FIELD: [MessageHandler(filters.TEXT & ~filters.Regex("^⬅️ Ortga$"), update_field)],
        UPDATE_VALUE: [MessageHandler(filters.TEXT & ~filters.Regex("^⬅️ Ortga$"), update_agent_field)],

        # 🗑 Delete flow
        SELECT_AGENT_DELETE: [CallbackQueryHandler(delete_agent_callback, pattern="^delete:")],
    },

    fallbacks=[MessageHandler(filters.Regex("(?i)^⬅️ *Ortga$"), go_back_to_admin)],
    allow_reentry=True
)

