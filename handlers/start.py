from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from keyboards import getInlineKeyboardBut, getKeyboardBut
from database.database import conn, cursor
from handlers.captcha import captchaHandler
import logging
import json
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

config_path = Path(__file__).parent.parent / 'config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

botUserName = config["BOT_USERNAME"]
ADMIN_IDS = config["ADMIN_IDS"]
TELEGRAM_CHANEL = config["TELEGRAM_CHANEL"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    username = user.username or ""
    message_obj = update.message or (update.callback_query and update.callback_query.message)
    args = context.args if hasattr(context, 'args') else []

    # Проверяем, был ли пользователь приглашён
    invited_by = int(args[0]) if args and args[0].isdigit() and int(args[0]) != uid else None
    cursor.execute("SELECT id FROM users WHERE id=?", (uid,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (id, username, stars, withdrawn, invited_by, referral_link) VALUES (?, ?, 0, 0, ?, '')", (uid, username, invited_by))
        link = f"https://t.me/{botUserName}?start={uid}"
        cursor.execute("UPDATE users SET referral_link=? WHERE id=?", (link, uid))
        conn.commit()

    # Проверка, была ли уже пройдена капча
    cursor.execute("SELECT subscription_verified, captcha_verified, invited_by FROM users WHERE id=?", (uid,))
    row = cursor.fetchone()
    subscription_verified = row[0]
    captcha_verified = row[1]
    invited_by = row[2]

    if not captcha_verified:
        await captchaHandler(update, context)
        return

    not_subscribed_channels = []  # Список каналов, на которые пользователь не подписан

    for channel in TELEGRAM_CHANEL:
        if channel.startswith("@"):
            try:
                chat_member = await context.bot.get_chat_member(channel, uid)
                if chat_member.status not in ["member", "administrator", "creator"]:
                    not_subscribed_channels.append(channel)
            except Exception as e:
                print(f"Ошибка проверки подписки на канал {channel}: {e}")

    # Если есть каналы, на которые пользователь не подписан, отправляем одно сообщение
    if not_subscribed_channels:
        channels_list = "\n".join([f"🔹 {channel}" for channel in not_subscribed_channels])
        await message_obj.reply_text(
            f"Для продолжения подпишитесь на следующие каналы:\n\n{channels_list}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]])
        )
        return

    # === New: Check partner channels ===
    cursor.execute("SELECT contact FROM partners")
    partner_contacts = [r[0] for r in cursor.fetchall()]

    for contact in partner_contacts:
        if contact.startswith("@"):
            try:
                chat_member = await context.bot.get_chat_member(contact, uid)
                if chat_member.status not in ["member", "administrator", "creator"]:
                    await message_obj.reply_text(
                        f"Для продолжения подпишитесь на канал {contact}.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("✅ Проверить подписку", callback_data=f"check_partner_{contact}")
                        ]])
                    )
                    return
            except:
                pass 

    # Получаем данные пользователя: звезды, снятые звезды и реферальная ссылка
    cursor.execute("SELECT stars, withdrawn, referral_link FROM users WHERE id=?", (uid,))
    stars, withdrawn, link = cursor.fetchone()

    # Подсчитываем количество пользователей, которых пригласил текущий пользователь
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id=?", (uid,))
    referalsCount = cursor.fetchone()[0]

    # Получаем цену за одного реферала
    cursor.execute("SELECT referral_price_inviter FROM settings")
    referral_price_inviter = cursor.fetchone()[0]
    
    # Получаем цену за переход по реферальной ссылке
    cursor.execute("SELECT referral_price_referred FROM settings WHERE id=1")
    price_referred = cursor.fetchone()[0]


    from urllib.parse import quote_plus

    # Текст сообщения для шаринга (без ссылки)
    share_text = f"""🎉 **Получите бесплатные звёзды!** 🎉

Мы уже отправили **более тысячи звёзд** и дарим вам **{price_referred} ⭐️** за переход в наш бот! 😎

Не упустите шанс! 🚀

👉 Просто нажмите на кнопку ниже, чтобы начать! 👇👇👇"""

    # Кодируем компоненты URL
    encoded_text = quote_plus(share_text)
    encoded_link = quote_plus(link)

    # Формируем URL для кнопки
    share_url = f"https://t.me/share/url?text={encoded_text}&url={encoded_link}"

    # Создаем инлайн кнопку
    inviteButton = InlineKeyboardButton("Пригласить друзей", url=share_url)

    from keyboards import getInlineKeyboardBut
    from messages import infoMessage

    await message_obj.reply_text(
        "❤️",
        reply_markup=getKeyboardBut(uid)
    )
    await message_obj.reply_text(
        infoMessage(referral_price_inviter, referalsCount, link),
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[inviteButton]])
    )