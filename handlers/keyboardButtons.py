from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.database import conn, cursor
from handlers.start import start
from telegram.error import BadRequest
from keyboards import getInlineKeyboardBut, getKeyboardBut
import json
from pathlib import Path
from handlers.text import actions, back_button

config_path = Path(__file__).parent.parent / 'config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

ADMIN_IDS = config["ADMIN_IDS"]
OWNER = config["OWNER"]

waiting_questions = {}
actions = {}

async def buttonKeyboardHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.message.from_user.id
    username = update.message.from_user.username or ""

    if text == "📊 Моя статистика":
        cursor.execute("SELECT stars, withdrawn, referral_link FROM users WHERE id=?", (uid,))
        stars, withdrawn, link = cursor.fetchone()
        # Подсчитываем количество пользователей, которых пригласил текущий пользователь
        cursor.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id=?", (uid,))
        referalsCount = cursor.fetchone()[0]
        
        achievements = []
        if referalsCount >= 5:
            achievements.append("🔓 <b>Рекрутёр</b> — пригласил 5+ пользователей")
        if stars + withdrawn >= 200:
            achievements.append("💎 <b>Мастер</b> — заработал 200+ звёзд")
        cursor.execute("SELECT captcha_verified FROM users WHERE id=?", (uid,))
        if cursor.fetchone()[0]:
            achievements.append("🧠 <b>Гений</b> — прошёл капчу")

        achievement_text = (
            "\n\n🏅 <b>Достижения:</b>\n" + "\n".join(achievements)
            if achievements
            else "\n\n🏅 <b>Достижения:</b>\nПока нет достижений. Начните зарабатывать звёзды!"
        )

        await update.message.reply_text(
            f"""
<b>👤 Профиль:</b> @{username or "Пользователь"}
⭐ <b>Баланс:</b> {stars} звёзд
💸 <b>Выведено:</b> {withdrawn} звёзд
👥 <b>Рефералов:</b> {referalsCount} пользователей
🔗 <b>Ваша ссылка:</b> <code>{link}</code>
    {achievement_text}
    """,
            parse_mode="HTML",
            reply_markup=getInlineKeyboardBut(uid),
        )

    elif text == "ℹ️ Информация":
        # Получаем цену за переход по реферальной ссылке
        cursor.execute("SELECT referral_price_referred FROM settings WHERE id=1")
        price_referred = cursor.fetchone()[0]

        # Получаем цену за одного реферала
        cursor.execute("SELECT referral_price_inviter FROM settings")
        referral_price_inviter = cursor.fetchone()[0]
        
        # Получаем минимальный вывод
        cursor.execute("SELECT minimum_output FROM settings WHERE id=1")
        minimum_output = cursor.fetchone()[0]
            
        await update.message.reply_text(
    f"""
<b>✨🚀 Дорогие друзья! 🎁⭐️</b>

Мы подготовили уникальный продукт для всех любителей Stars и подарков в Telegram!

<b>📢 Представляем бота, с помощью которого вы можете зарабатывать Stars за приглашение друзей по вашей уникальной реферальной ссылке.</b>

<b>💡 Как это работает?</b>
Приглашай пользователей в бота по специальной ссылке и получай по {referral_price_inviter} ⭐️ как только они пройдут капчу.

<b>⚡️ Вывод моментальный, доступен при накоплении {minimum_output} ⭐️ на балансе!</b>

<b>🔹 Как приглашать друзей?</b>
Перейди в раздел «⭐️ Заработать звёзды», скопируй свою уникальную ссылку и распространяй её:
- ✅ Среди друзей;
- ✅ В чатах;
- ✅ В TikTok и других соцсетях.

<b>🎁 Бонус! Пользователь, который перейдёт по вашей ссылке, получит {price_referred} ⭐️ на баланс!</b>

Присоединяйтесь и зарабатывайте вместе с нами! 🚀⭐️
    """,
        parse_mode='HTML'
    )

    elif text == "❓ Помощь":
        await update.message.reply_text(
        """
<b>❓ Помощь и поддержка</b>

Добро пожаловать в раздел помощи! Здесь вы найдёте ответы на основные вопросы и сможете задать свой вопрос, если не нашли нужной информации.

<b>🔹 Как заработать звёзды?</b>
- Приглашайте друзей в бота по вашей уникальной реферальной ссылке.
- За каждого друга, который пройдёт капчу, вы получите <b> {} ⭐️</b>.

<b>🔹 Как вывести звёзды?</b>
- Вывод доступен при накоплении <b>минимум {} ⭐️</b>.
- Для вывода перейдите в раздел «💸 Вывести звёзды» и следуйте инструкциям.

<b>🔹 Как использовать звёзды?</b>
- Звёзды можно обменять на бонусы или использовать для других предложений.

<b>🔹 У меня возникли вопросы</b>
Если у вас есть вопросы или проблемы, нажмите на кнопку «Задать вопрос» ниже, и мы постараемся вам помочь.

<b>📢 Контакты</b>
- По всем вопросам вы также можете написать: @FRRaskTC
        """,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask")]
        ])
    )
        
    elif text == "🛠 Админ-панель":
        from handlers.admin import admin_panel
        await admin_panel(update, context)