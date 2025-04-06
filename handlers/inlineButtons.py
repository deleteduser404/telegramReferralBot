from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.database import conn, cursor
from handlers.start import start
from telegram.error import BadRequest
from keyboards import admin_back
from io import BytesIO
from handlers.captcha import *
import json
from pathlib import Path
from handlers.text import actions
from utils import *

config_path = Path(__file__).parent.parent / 'config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
    
ADMIN_IDS = config["ADMIN_IDS"]
OWNER = config["OWNER"]
TELEGRAM_CHANEL = config["TELEGRAM_CHANEL"]

async def buttonInlineHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    # Инициализация стека состояний, если его нет
    if 'state_stack' not in context.user_data:
        context.user_data['state_stack'] = []

    try:
        await query.answer()
    except BadRequest as e:
        if "Query is too old" in str(e):
            print(f"Ошибка: запрос устарел {e}")
            return
        raise e
    
    await query.answer()
    username = query.from_user.username or ""
    
    from keyboards import back_button
    
    if data.startswith("change_captcha"):
        # Генерация нового текста капчи
        new_captcha_text = generateCaptchaText()

        # Сохраняем новый текст капчи в user_data
        context.user_data['captchaText'] = new_captcha_text

        # Создаем новое изображение капчи
        new_captcha_image = await createCaptchaImage(new_captcha_text)

        # Сохраняем изображение как файл и передаем его
        new_captcha_image.seek(0)  # Убедитесь, что поток в начале
        new_captcha_file = BytesIO(new_captcha_image.read())
        new_captcha_file.name = 'captcha.png'

        # Создаем объект InputMediaPhoto с caption
        media = InputMediaPhoto(new_captcha_file, caption="Пройдите капчу: введите текст с картинки.")

        # Отправляем новое изображение капчи с кнопкой для изменения капчи
        await query.edit_message_media(
            media=media, 
            reply_markup=getChangeCaptchaButton()
        )

    # === Check partner subscription
    elif data.startswith("check_partner_"):
        partner_channel = data.split("check_partner_")[1]
        try:
            chat_member = await context.bot.get_chat_member(partner_channel, uid)
            if chat_member.status in ["member", "administrator", "creator"]:
                await query.edit_message_text("✅ Подписка подтверждена!")
                await start(update, context)
            else:
                await query.edit_message_text(
                    f"❗ Вы всё ещё не подписаны на {partner_channel}.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Проверить подписку", callback_data=f"check_partner_{partner_channel}")
                    ]])
                )
        except:
            await query.edit_message_text(
                f"Ошибка проверки канала {partner_channel}. Убедитесь, что бот — админ, или канал доступен."
            )
        return



    # === check_subscription main channel
    if data == 'check_subscription':
        all_subscribed = True  # Флаг для проверки подписки на все каналы
        for channel in TELEGRAM_CHANEL:
            try:
                chat_member = await context.bot.get_chat_member(channel, uid)
                if chat_member.status not in ['member', 'administrator', 'creator']:
                    all_subscribed = False
                    break
            except Exception as e:
                print(f"Ошибка проверки подписки на канал {channel}: {e}")
                all_subscribed = False
                break

        if all_subscribed:
            cursor.execute("UPDATE users SET subscription_verified = TRUE WHERE id=?", (uid,))
            conn.commit()
            await query.edit_message_text("✅ Подписка подтверждена!")
            await start(update, context)
        else:
            await query.edit_message_text(
                f"❗ Вы не подписаны на все каналы: {', '.join(TELEGRAM_CHANEL)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")
                ]])
            )
        return

    if data == 'earn':
        cursor.execute("SELECT referral_link FROM users WHERE id=?", (uid,))
        link = cursor.fetchone()[0]
        await query.edit_message_text(f"🔗 Ваша ссылка: {link}", reply_markup=back_button())

    elif data == 'buy':
        await query.edit_message_text("📢 Свяжитесь: @FRRaskTC", reply_markup=back_button())

    elif data == 'withdraw':
        cursor.execute("SELECT stars FROM users WHERE id=?", (uid,))
        stars = cursor.fetchone()[0]
        if stars < 50:
            await query.edit_message_text("❗ У вас недостаточно звёзд для вывода. Минимум: 50 ⭐.", reply_markup=back_button())
        else:
            actions[uid] = 'withdraw_request'
            await query.edit_message_text(
                f"Введите количество звёзд для вывода (от 50 до {stars} ⭐):",
                reply_markup=back_button()
            )

    # === partners
    elif data == 'partners':
        cursor.execute("SELECT info, contact FROM partners")
        rows = cursor.fetchall()
        if not rows:
            await query.edit_message_text("Нет партнёров.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить партнёра", callback_data="partner_add")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back")]
            ]))
        else:
            text = "\n".join([f"🔹 {info} — {contact}" for info, contact in rows])
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить партнёра", callback_data="partner_add")],
                    [InlineKeyboardButton("➖ Удалить партнёра", callback_data="partner_remove")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="back")]
                ])
            )


    elif data == 'mystats':
        cursor.execute("SELECT stars, withdrawn, referral_link FROM users WHERE id=?", (uid,))
        stars, withdrawn, link = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM users WHERE invited_by=?", (uid,))
        invited = cursor.fetchone()[0]
        achievements = []
        
        if invited >= 5:
            achievements.append("🔓 Рекрутёр")
            
        if stars + withdrawn >= 200:
            achievements.append("💎 Мастер")
            
        cursor.execute("SELECT captcha_verified FROM users WHERE id=?", (uid,))
        if cursor.fetchone()[0]:
            achievements.append("🧠 Гений")
        achievement_text = "\n🏅 Достижения:\n" + "\n".join(achievements) if achievements else ""
        await query.message.reply_text(
            f"👤 @{query.from_user.username or 'Пользователь'}\n"
            f"⭐ Баланс: {stars}\n"
            f"💸 Выведено: {withdrawn}\n"
            f"👥 Рефералов: {invited}\n"
            f"🔗 Ссылка: {link}\n"
            f"{achievement_text}",
            reply_markup=admin_back())

    elif data == 'ask':
        actions['ask'].add(uid)
        await query.edit_message_text("Введите ваш вопрос:", reply_markup=back_button())

    # === Confirm withdraw
    if data.startswith("confirm_withdraw_"):
        target_uid = int(data.split("_")[2])
        cursor.execute("SELECT stars FROM users WHERE id=?", (target_uid,))
        stars = cursor.fetchone()[0]
        cursor.execute("UPDATE users SET stars=0, withdrawn=withdrawn+? WHERE id=?", (stars, target_uid))
        cursor.execute("UPDATE withdraw_requests SET status='approved' WHERE user_id=?", (target_uid,))
        conn.commit()
        await context.bot.send_message(target_uid, "✅ Ваша заявка на вывод одобрена! Ожидайте, вам отпишет админ.")
        await query.edit_message_text(f"✅ Вывод подтвержден для пользователя {target_uid}.")

    # === Reject withdraw
    elif data.startswith("reject_withdraw_"):
        target_uid = int(data.split("_")[2])
        cursor.execute("UPDATE withdraw_requests SET status='rejected' WHERE user_id=?", (target_uid,))
        conn.commit()
        await context.bot.send_message(target_uid, "❌ Ваша заявка на вывод отклонена. Свяжитесь с @FRRaskTC")
        await query.edit_message_text(f"❌ Вывод отклонён для пользователя {target_uid}.")

    # === Back button
    elif data == 'back':
        from keyboards import getInlineKeyboardBut
        from messages import infoMessage

        try:
            # Получаем реферальную ссылку
            cursor.execute("SELECT referral_link FROM users WHERE id=?", (uid,))
            link = cursor.fetchone()
            if not link:
                raise ValueError("Реферальная ссылка не найдена.")

            # Подсчитываем количество рефералов
            cursor.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id=?", (uid,))
            referalsCount = cursor.fetchone()[0]

            # Получаем цену за одного реферала
            cursor.execute("SELECT referral_price_inviter FROM settings")
            referral_price_inviter = cursor.fetchone()[0]

            # Формируем и обновляем сообщение
            message_text = infoMessage(referral_price_inviter, referalsCount, link[0])
            await query.edit_message_text(
                message_text,
                parse_mode='HTML',
                reply_markup=getInlineKeyboardBut(uid)
            )
        except Exception as e:
            print(f"Ошибка при обработке кнопки 'Назад': {e}")
        finally:
            if uid in actions:
                actions.pop(uid, None)

    elif data == 'admin_back':
        from keyboards import getAdminPanelKeyboard
        try:
            await query.edit_message_text("🛠 Админ-панель:", reply_markup=getAdminPanelKeyboard(uid, OWNER))
        except Exception as e:
            print(f"Ошибка при изменении сообщения: {e}")
        finally:
            if uid in actions:
                actions.pop(uid, None)
                
    # === Add partner (only admin)
    elif data == 'partner_add':
        if uid not in ADMIN_IDS:
            await query.edit_message_text(
                "⛔ У вас нет доступа.",
                reply_markup = admin_back()
            )
            return
        actions[uid] = 'partner_add'
        await query.edit_message_text(
            "Введите описание и ссылку на партнёра через —",
            reply_markup = admin_back()
        )

    # === Remove partner (only admin)
    elif data == 'partner_remove':
        if uid not in ADMIN_IDS:
            await query.edit_message_text(
                "⛔ У вас нет доступа.",
                reply_markup = admin_back()
            )
            return
        actions[uid] = 'partner_remove'
        await query.edit_message_text(
            "Введите точную ссылку партнёра для удаления",
            reply_markup = admin_back()
        )

    # === Admin broadcast (only admin)
    elif data == 'admin_broadcast':
        if uid not in ADMIN_IDS:
            await query.edit_message_text(
                "⛔ У вас нет доступа.",
                reply_markup = admin_back()
            )
            return
        actions[uid] = 'broadcast'
        await query.edit_message_text(
            "Введите текст рассылки для всех пользователей",
            reply_markup = admin_back()
    )

    # === Admin stats (only admin)
    elif data == 'admin_stats':
        if uid not in ADMIN_IDS:
            await query.edit_message_text("⛔ У вас нет доступа.")
            return

        try:
            # Общее количество пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0] or 0

            # Количество активных пользователей (пригласили больше 5 людей)
            cursor.execute("""
                SELECT COUNT(*)
                FROM users
                WHERE id IN (
                    SELECT inviter_id
                    FROM referrals
                    GROUP BY inviter_id
                    HAVING COUNT(referred_id) > 5
                )
            """)
            active_users = cursor.fetchone()[0] or 0

            # Количество заявок на вывод
            cursor.execute("SELECT COUNT(*) FROM withdraw_requests WHERE status = 'approved'")
            approved_withdraws = cursor.fetchone()[0] or 0

            # Сумма всех выведенных звёзд
            cursor.execute("""
                SELECT COALESCE(SUM(stars), 0) 
                FROM withdraw_requests 
                WHERE status = 'approved'
            """)
            total_withdrawn_stars = cursor.fetchone()[0] or 0

            # Формируем сообщение
            stats_message = (
                f"📊 <b>Статистика</b>:\n\n"
                f"👥 <b>Всего пользователей:</b> {total_users}\n"
                f"✅ <b>Активных пользователей:</b> {active_users}\n"
                f"💸 <b>Заявок на вывод (одобрено):</b> {approved_withdraws}\n"
                f"⭐ <b>Всего выведено звёзд:</b> {total_withdrawn_stars}\n"
            )

            # Отправляем сообщение
            await query.edit_message_text(
                stats_message,
                parse_mode="HTML",
                reply_markup = admin_back()
            )

        except BadRequest as e:
            print(f"Ошибка при редактировании сообщения: {e}")
            await query.answer("Произошла ошибка. Попробуйте снова.")

    # === Admin set referral price (only admin)
    elif data == 'admin_set_price_inviter':
        if uid not in ADMIN_IDS:
            await query.edit_message_text("⛔ У вас нет доступа.")
            return
        actions[uid] = 'set_price_inviter'
        await query.edit_message_text("Введите новую цену за реферал (число).",
                reply_markup = admin_back())
        
    elif data == 'admin_set_price_referred':
        if uid not in ADMIN_IDS:
            await query.edit_message_text("⛔ У вас нет доступа.")
            return
        actions[uid] = 'set_price_referred'
        await query.edit_message_text("Введите новую цену человеку зашедшему по реферальной ссылке (число).",
                reply_markup = admin_back())
        
    # === Add admin (only owner)
    elif data == 'admin_add':
        if uid != OWNER:  # Проверяем, является ли пользователь владельцем
            await query.edit_message_text(
                "⛔ У вас нет доступа.",
                reply_markup=admin_back()
            )
            return

        # Сохраняем действие в actions
        actions[uid] = 'admin_add'

        # Запрашиваем ввод тега или ID администратора
        await query.edit_message_text(
            "Введите тег (начинается с @) или ID нового администратора:",
            reply_markup=admin_back()
        )