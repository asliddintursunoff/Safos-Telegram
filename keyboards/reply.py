from telegram import ReplyKeyboardMarkup
BACK_BUTTON = [["⬅️ Back"]]
back_button = ReplyKeyboardMarkup(
        BACK_BUTTON,
        resize_keyboard=True,
        one_time_keyboard=False
    )

HISOB_KITOB_BUTTON = [["💰 BUGUNGI ZAKASLARIM PULI"], ["📆BELGILANGAN SANADAGI" , "📊 SANA ORALIG'IDAGI"] ,["📕Hisobim"],["⬅️ Ortga"]]
hisob_kitob_button = ReplyKeyboardMarkup(
    HISOB_KITOB_BUTTON,
    resize_keyboard = True,
    one_time_keyboard=True
)