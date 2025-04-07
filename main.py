from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from handlers import start
from handlers.text import text_handler, handle_admin_reply, actions
from handlers.inlineButtons import buttonInlineHandler, InlineKeyboardButton, InlineKeyboardMarkup
from handlers.keyboardButtons import buttonKeyboardHandler
from handlers.captcha import handleCaptchaResponse, changeCaptcha
from database.database import conn, cursor
from telegram import Update
from dotenv import load_dotenv
import os
import logging
import json
from pathlib import Path

# === Загрузка конфигурации ===
configPath = Path(__file__).parent / 'config.json'
with open(configPath, 'r', encoding='utf-8') as f:
    config = json.load(f)

botUsername = config["BOT_USERNAME"]
adminIds = config["ADMIN_IDS"]
telegramChannel = config["TELEGRAM_CHANEL"]

# === Настройка окружения и логирования ===
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Инициализация приложения ===
application = ApplicationBuilder().token(os.getenv('TOKEN')).build()

# === Вспомогательные функции ===
async def checkSubscription(uid, context, channels):
    """Проверяет подписку пользователя на список каналов."""
    notSubscribed = []
    for channel in channels:
        if channel.startswith("@"):
            try:
                chatMember = await context.bot.get_chat_member(channel, uid)
                if chatMember.status not in ["member", "administrator", "creator"]:
                    notSubscribed.append(channel)
            except Exception as e:
                logger.error(f"Ошибка проверки подписки на канал {channel}: {e}")
                notSubscribed.append(channel)  # Добавляем канал, если произошла ошибка
    return notSubscribed

async def sendSubscriptionMessage(update, channels):
    """Отправляет сообщение с просьбой подписаться на каналы."""
    channelsList = "\n".join([f"🔹 {channel}" for channel in channels])
    await update.message.reply_text(
        f"Для продолжения подпишитесь на следующие каналы:\n\n{channelsList}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]])
    )

# === Основной обработчик ===
async def combinedHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    # Проверяем, находится ли пользователь в процессе выполнения действия
    if uid in actions:
        action = actions[uid]
        if action == 'captcha':
            await handleCaptchaResponse(update, context)
        else:
            await text_handler(update, context)
        return

    # Проверяем, является ли сообщение ответом на вопрос
    if update.message.reply_to_message:
        await handle_admin_reply(update, context)
        return

    # Проверяем подписку на основные каналы
    notSubscribedChannels = await checkSubscription(uid, context, telegramChannel)

    # Проверяем подписку на каналы партнёров
    cursor.execute("SELECT contact FROM partners")
    partnerContacts = [r[0] for r in cursor.fetchall()]
    notSubscribedChannels += await checkSubscription(uid, context, partnerContacts)

    # Если есть каналы, на которые пользователь не подписан, отправляем сообщение
    if notSubscribedChannels:
        await sendSubscriptionMessage(update, notSubscribedChannels)
        return

    # Проверяем капчу
    cursor.execute("SELECT captcha_verified FROM users WHERE id=?", (uid,))
    captchaVerified = cursor.fetchone()[0]

    if not captchaVerified:
        await handleCaptchaResponse(update, context)
    else:
        # Обработка кнопок и текстовых сообщений
        await buttonKeyboardHandler(update, context)
        if text:
            await text_handler(update, context)

# === Регистрация обработчиков ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttonInlineHandler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, combinedHandler))
application.add_handler(MessageHandler(filters.TEXT, text_handler))

# === Запуск бота ===
if __name__ == "__main__":
    logger.info("🤖 Бот запущен!")
    application.run_polling()