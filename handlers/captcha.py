from captcha.image import ImageCaptcha
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from io import BytesIO
import random
import string
from database.database import conn, cursor
from handlers.text import actions

# Генерация случайного текста капчи
def generateCaptchaText():
    captchaText = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return captchaText

# Создание изображения капчи
async def createCaptchaImage(captchaText):
    imageCaptcha = ImageCaptcha(width=280, height=90)
    
    # Генерация изображения с текстом
    captchaImage = imageCaptcha.generate_image(captchaText)

    # Сохранение изображения в память
    byteIo = BytesIO()
    captchaImage.save(byteIo, 'PNG')
    byteIo.seek(0)

    return byteIo

def getChangeCaptchaButton():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Изменить капчу", callback_data="change_captcha")]])

# Обработчик капчи
async def captchaHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # Проверяем, был ли уже пройден верификатор капчи
    cursor.execute("SELECT captcha_verified FROM users WHERE id=?", (uid,))
    if cursor.fetchone()[0]:
        # Если капча уже пройдена, игнорируем дальнейшие запросы
        await update.message.reply_text("✅ Капча уже пройдена!")
        return

    # Генерация текста капчи
    captchaText = generateCaptchaText()

    # Сохраняем текст капчи в user_data
    context.user_data['captchaText'] = captchaText

    # Создаем изображение капчи
    captchaImage = await createCaptchaImage(captchaText)

    # Отправляем картинку с капчей пользователю с кнопкой для изменения капчи
    await update.message.reply_photo(
        photo=captchaImage, 
        caption="Пройдите капчу: введите текст с картинки.",
        reply_markup=getChangeCaptchaButton()
    )
    actions[uid] = 'captcha'

# Обработчик текста (пользователь вводит текст)
async def handleCaptchaResponse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_input = update.message.text

    if 'captchaText' not in context.user_data:
        return

    captcha_text = context.user_data['captchaText']

    if user_input.upper() == captcha_text:
        cursor.execute("UPDATE users SET captcha_verified = 1 WHERE id=?", (uid,))
        conn.commit()

        # Получаем информацию о пригласившем
        cursor.execute("SELECT invited_by FROM users WHERE id=?", (uid,))
        invited_by = cursor.fetchone()[0]

        # Начисляем звезды если есть пригласивший
        if invited_by:
            # Начисление звёзд пригласившему
            cursor.execute("SELECT referral_price_inviter FROM settings WHERE id=1")
            price_inviter = cursor.fetchone()[0]
            cursor.execute("""
                UPDATE users 
                SET stars = stars + ? 
                WHERE id = ?
            """, (price_inviter, invited_by))

            # Начисление звёзд приглашённому
            cursor.execute("SELECT referral_price_referred FROM settings WHERE id=1")
            price_referred = cursor.fetchone()[0]
            cursor.execute("""
                UPDATE users 
                SET stars = stars + ? 
                WHERE id = ?
            """, (price_referred, uid))

            # Фиксируем реферала
            cursor.execute("""
                INSERT INTO referrals (inviter_id, referred_id) 
                VALUES (?, ?)
            """, (invited_by, uid))

            # Обнуляем invited_by ТОЛЬКО после начисления
            cursor.execute("""
                UPDATE users 
                SET invited_by = NULL 
                WHERE id = ?
            """, (uid,))

            conn.commit()

            # Отправляем уведомление пригласившему
            try:
                await context.bot.send_message(
                    invited_by,
                    f"🎉 Новый реферал! Вы получили ⭐ {price_inviter} звёзд!"
                )
            except Exception as e:
                print(f"Error sending notification to inviter: {e}")

        # Изменяем старое сообщение с капчей или отправляем новое
        if update.callback_query:
            try:
                query = update.callback_query
                await query.edit_message_text("✅")
            except Exception as e:
                print(f"Error editing captcha message: {e}")
        else:
            await update.message.reply_text("✅")
            del actions[uid] # Удаляем действие капчи

        from handlers.start import start
        await start(update, context)
    else:
        await update.message.reply_text("❌ Неправильно! Попробуйте еще раз.")

# Обработчик нажатия на инлайн кнопку "Изменить капчу"
async def changeCaptcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    uid = user.id
    await query.answer()