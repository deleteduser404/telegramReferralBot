from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from handlers.inlineButtons import *
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import json
from pathlib import Path

config_path = Path(__file__).parent.parent / 'config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

OWNER = config["OWNER"]

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return

    keyboard = [
        [InlineKeyboardButton("📥 Заявки на вывод", callback_data="admin_withdraws")],
        [InlineKeyboardButton("👥 Партнёры", callback_data="partners")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")]
    ]
    if uid == OWNER:
        keyboard.append([InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")])
        keyboard.append([InlineKeyboardButton("💲 Изменить цену за заход по рефералке", callback_data="admin_set_price_referred")])
        keyboard.append([InlineKeyboardButton("💲 Изменить цену за приглашенного", callback_data="admin_set_price_inviter")])
    
    await update.message.reply_text("🛠 Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))