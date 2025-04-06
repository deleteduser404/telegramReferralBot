from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
import json

with open('config.json') as f:
    config = json.load(f)

ADMIN_IDS = config["ADMIN_IDS"]

# Функция для получения inline-клавиатуры
def getInlineKeyboardBut(uid):
    inlineKeyboardBut = [
        [InlineKeyboardButton("⭐ Заработать звезды", callback_data='earn')],
        [InlineKeyboardButton("📢 Купить рекламу", callback_data='buy')],
        [InlineKeyboardButton("💸 Вывести звезды", callback_data='withdraw')],
        [InlineKeyboardButton("👥 Партнёры", callback_data='partners')],
    ]

    return InlineKeyboardMarkup(inlineKeyboardBut)

def getAdminPanelKeyboard(uid, owner_id):
    keyboard = [
        [InlineKeyboardButton("📥 Заявки на вывод", callback_data="admin_withdraws")],
        [InlineKeyboardButton("👥 Партнёры", callback_data="partners")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")]
    ]

    # Добавляем дополнительные кнопки, если пользователь является владельцем
    if uid == owner_id:
        keyboard.append([InlineKeyboardButton("📊 Добавить админа", callback_data="admin_add")])
        keyboard.append([InlineKeyboardButton("💲 Изменить цену за заход по рефералке", callback_data="admin_set_price_referred")])
        keyboard.append([InlineKeyboardButton("💲 Изменить цену за приглашенного", callback_data="admin_set_price_inviter")])

    return InlineKeyboardMarkup(keyboard)

def getKeyboardBut(uid):
    keyboard = [
        [KeyboardButton("📊 Моя статистика")],
        [KeyboardButton("ℹ️ Информация")],
        [KeyboardButton("❓ Помощь")]
    ]

    if uid in ADMIN_IDS:
        keyboard.append([KeyboardButton("🛠 Админ-панель")])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Функция для кнопки "Назад"
def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='back')]])

def admin_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])