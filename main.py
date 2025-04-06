from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from handlers import start
from handlers.text import text_handler, handle_admin_reply
from handlers.inlineButtons import buttonInlineHandler, InlineKeyboardButton, InlineKeyboardMarkup
from handlers.keyboardButtons import buttonKeyboardHandler
from handlers.captcha import handleCaptchaResponse, changeCaptcha
from database.database import conn, cursor
from telegram import Update
from dotenv import load_dotenv
import os
import logging
from handlers.text import actions, back_button
import json
from pathlib import Path

config_path = Path(__file__).parent / 'config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

botUserName = config["BOT_USERNAME"]
ADMIN_IDS = config["ADMIN_IDS"]
TELEGRAM_CHANEL = config["TELEGRAM_CHANEL"]

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

application = ApplicationBuilder().token(os.getenv('TOKEN')).build()

async def combinedHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    # Проверяем, находится ли пользователь в процессе выполнения действия
    if uid in actions:
        action = actions[uid]
        if action == 'captcha':
            await handleCaptchaResponse(update, context)  # Обрабатываем капчу
            return
        else:
            await text_handler(update, context)
            return

    # Проверяем, является ли сообщение ответом на вопрос
    if update.message.reply_to_message:
        await handle_admin_reply(update, context)  # Обрабатываем ответ администратора
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

        # Если есть каналы, на которые пользователь не подписан, отправляем сообщение
        if not_subscribed_channels:
            channels_list = "\n".join([f"🔹 {channel}" for channel in not_subscribed_channels])
            await update.message.reply_text(
                f"Для продолжения подпишитесь на следующие каналы:\n\n{channels_list}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]])
            )
            return

    # Проверяем капчу
    cursor.execute("SELECT captcha_verified FROM users WHERE id=?", (uid,))
    captcha_verified = cursor.fetchone()[0]

    if not captcha_verified:
        await handleCaptchaResponse(update, context)
    else:
        # Обработка кнопок и текстовых сообщений
        await buttonKeyboardHandler(update, context)

        if text:
            await text_handler(update, context)

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttonInlineHandler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, combinedHandler))
application.add_handler(MessageHandler(filters.TEXT, text_handler))

print("🤖 Бот запущен!")
application.run_polling()