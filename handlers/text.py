from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from database.database import conn, cursor
import json
from pathlib import Path
from keyboards import back_button, getAdminPanelKeyboard
import random


config_path = Path(__file__).parent.parent / 'config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

ADMIN_IDS = config["ADMIN_IDS"]
OWNER = config["OWNER"]
actions = {
    'ask': set()
}
questions = {}

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_to_message = update.message.reply_to_message
    if not reply_to_message:
        return

    for question_id, question_data in questions.items():
        if reply_to_message.message_id in question_data["message_ids"]:
            user_id = question_data["user_id"]
            admin_username = update.effective_user.username or update.effective_user.id
            answer_text = update.message.text

            await context.bot.send_message(
                user_id,
                f"✅ Администратор @{admin_username} ответил на ваш вопрос:\n\n{answer_text}"
            )

            for admin_message_id in question_data["message_ids"]:
                try:
                    await context.bot.edit_message_text(
                        chat_id=reply_to_message.chat_id,
                        message_id=admin_message_id,
                        text=f"❓ Вопрос #{question_id} от @{user_id}:\n{question_data['text']}\n\n✅ Ответил: @{admin_username}\n\nОтвет: {answer_text}"
                    )
                except Exception as e:
                    print(f"Ошибка при обновлении сообщения: {e}")

            del questions[question_id]
            return

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    
    def admin_back():
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]])
    
    # Обработка вопросов от пользователей
    if uid in actions.get('ask', set()):  # Безопасный доступ к ключу 'ask'
        question_id = random.randint(100000, 999999)
        questions[question_id] = {
            "user_id": uid,
            "message_ids": [],
            "text": text
        }

        # Отправляем вопрос всем администраторам
        for admin_id in ADMIN_IDS:
            msg = await context.bot.send_message(
                admin_id,
                f"❓ Вопрос #{question_id} от @{update.effective_user.username or uid}:\n{text}\n\nОтветьте на это сообщение, чтобы отправить ответ пользователю.",
                reply_markup=back_button()
            )
            questions[question_id]["message_ids"].append(msg.message_id)

        await update.message.reply_text("✅ Вопрос отправлен. Ожидайте ответ.", reply_markup=back_button())
        actions['ask'].remove(uid)  # Удаляем пользователя из множества
        return

    # Проверяем, находится ли пользователь в процессе выполнения действия
    if uid in actions:
        action = actions[uid]

        if action == 'admin_back':
            keyboard = getAdminPanelKeyboard(uid, OWNER)
            await update.message.reply_text("🛠 Админ-панель:", reply_markup=keyboard)
    
        # === Set Price
        if action == 'set_price_inviter':
            if uid not in ADMIN_IDS:
                await update.message.reply_text("⛔ У вас нет доступа.")
                return

            elif not text.isdigit():
                await update.message.reply_text("❌ Неверный формат. Введите целое число.", reply_markup=admin_back())
                return

            # Обновляем цену в базе данных
            new_price = int(text)
            cursor.execute("UPDATE settings SET referral_price_inviter=? WHERE id=1", (new_price,))
            conn.commit()
            await update.message.reply_text(f"✅ Цена за приглашенного обновлена до {new_price}.", reply_markup=admin_back())
            print(f"Цена за реферал обновлена до {new_price}.")
            del actions[uid]  # Удаляем действие после завершения
            return

        # Если пользователь должен ввести цену для приглашенного
        elif action == 'set_price_referred':
            if uid not in ADMIN_IDS:
                await update.message.reply_text("⛔ У вас нет доступа.")
                return

            elif not text.isdigit():
                await update.message.reply_text("❌ Неверный формат. Введите целое число.", reply_markup=admin_back())
                return

            # Обновляем цену в базе данных
            new_price = int(text)
            cursor.execute("UPDATE settings SET referral_price_referred=? WHERE id=1", (new_price,))
            conn.commit()
            await update.message.reply_text(f"✅ Цена перешедшему по реферальной ссылке обновлена до {new_price}.", reply_markup=back_button())
            print(f"Цена за реферал обновлена до {new_price}.")
            
            del actions[uid]  # Удаляем действие после завершения
            return

        # === Admin broadcast
        elif action == 'broadcast':
            if uid not in ADMIN_IDS:
                await update.message.reply_text("⛔ У вас нет доступа.")
                return

            # Проверяем, что пользователь ввёл текст (а не команду или пустое сообщение)
            if not text or text.startswith('/'):
                await update.message.reply_text("❌ Неверный формат. Введите текст для рассылки.", reply_markup=admin_back())
                return

            print("Начинаем рассылку.")
            cursor.execute("SELECT id FROM users")
            users = cursor.fetchall()
            print(f"Найдено пользователей для рассылки: {len(users)}")
            for (user_id,) in users:
                try:
                    await context.bot.send_message(user_id, text)
                    print(f"Сообщение отправлено пользователю {user_id}")
                except Exception as e:
                    print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
            await update.message.reply_text("✅ Рассылка завершена.", reply_markup=admin_back())

            del actions[uid]  # Удаляем действие после завершения
            return

        # === Add Partner
        elif action == 'partner_add':
            if uid not in ADMIN_IDS:
                await update.message.reply_text("⛔ У вас нет доступа.")
                return

            # Проверяем, что текст соответствует формату "описание - @тег"
            if '-' not in text or not text.split('-')[1].strip().startswith('@'):
                await update.message.reply_text(
                    "❌ Неверный формат. Используйте: описание - @тег",
                    reply_markup=admin_back()
                )
                return

            # Разделяем текст на описание и тег
            description, tag = map(str.strip, text.split('-', 1))

            # Проверяем, что тег начинается с @
            if not tag.startswith("@"):
                await update.message.reply_text(
                    "❌ Неверный формат. Тег должен начинаться с '@'.",
                    reply_markup=admin_back()
                )
                return

            # Проверяем, существует ли канал или пользователь с таким тегом
            try:
                chat = await context.bot.get_chat(tag)
                if chat.type not in ["channel", "supergroup"]:
                    await update.message.reply_text(
                        "❌ Указанный тег не является каналом или супергруппой.",
                        reply_markup=admin_back()
                    )
                    return
            except Exception as e:
                print(f"Ошибка проверки тега {tag}: {e}")
                await update.message.reply_text(
                    "❌ Тег не найден. Убедитесь, что бот является администратором канала.",
                    reply_markup=admin_back()
                )
                return

            # Если все проверки пройдены, добавляем партнёра
            cursor.execute("INSERT INTO partners (info, contact) VALUES (?, ?)", (description, tag))
            conn.commit()
            await update.message.reply_text("✅ Партнёр добавлен.", reply_markup=admin_back())
            print(f"Партнёр добавлен: {description} - {tag}")

            # Удаляем действие после завершения
            if uid in actions:
                actions.pop(uid, None)
                
        # === Remove Partner
        elif action == 'partner_remove':
            if uid not in ADMIN_IDS:
                await update.message.reply_text("⛔ У вас нет доступа.")
                return

            elif not text.isdigit():
                await update.message.reply_text("❌ Неверный формат. Введите целое число.", reply_markup=admin_back())
                return

            contact = text.strip()

            # Проверяем, существует ли партнёр перед удалением
            cursor.execute("SELECT * FROM partners WHERE contact=?", (contact,))
            partner = cursor.fetchone()

            if partner:
                # Удаляем партнёра, если он существует
                cursor.execute("DELETE FROM partners WHERE contact=?", (contact,))
                conn.commit()
                await update.message.reply_text(f"✅ Партнёр {contact} успешно удалён.", reply_markup=admin_back())
                print(f"Партнёр удалён: {contact}")
            else:
                # Если партнёр не найден
                await update.message.reply_text(f"❌ Партнёр {contact} не найден.", reply_markup=admin_back())
                print(f"Попытка удалить несуществующего партнёра: {contact}")
                
            if uid in actions:
                actions.pop(uid, None)
        
        elif action == 'admin_add':
            if uid != config["OWNER"]:
                await update.message.reply_text("⛔ У вас нет доступа.")
                return

            new_admin = text.strip()
            if new_admin.startswith('@'):  # Если это тег
                # Убедимся, что тег начинается с @ и не пустой
                new_admin_username = new_admin[1:]
                if not new_admin_username:
                    await update.message.reply_text("❌ Неверный формат. Введите корректный тег администратора.", reply_markup=admin_back())
                    return

                # Проверяем, существует ли пользователь с таким тегом
                cursor.execute("SELECT id FROM users WHERE username=?", (new_admin_username,))
                result = cursor.fetchone()
                if result:
                    new_admin_id = result[0]
                else:
                    await update.message.reply_text("❌ Пользователь с таким тегом не найден.", reply_markup=admin_back())
                    return
            elif new_admin.isdigit():  # Если это ID
                new_admin_id = int(new_admin)
            else:
                await update.message.reply_text("❌ Неверный формат. Введите ID администратора или тег (начинается с @).", reply_markup=admin_back())
                return

            # Проверяем, не добавлен ли уже администратор
            if new_admin_id in ADMIN_IDS:
                await update.message.reply_text("❌ Этот пользователь уже является администратором.", reply_markup=admin_back())
                return

            # Добавляем нового администратора
            ADMIN_IDS.append(new_admin_id)

            # Обновляем config.json, сохраняя все данные
            config["ADMIN_IDS"] = ADMIN_IDS
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            await update.message.reply_text("✅ Новый администратор добавлен.", reply_markup=admin_back())
            print(f"Новый администратор добавлен: {new_admin_id}")
            if uid in actions:
                actions.pop(uid, None)
        
        elif action == 'withdraw_request':

            if not text.isdigit():
                await update.message.reply_text("❌ Неверный формат. Введите целое число.", reply_markup=back_button())
                return

            stars_to_withdraw = int(text)
            cursor.execute("SELECT stars FROM users WHERE id=?", (uid,))
            available_stars = cursor.fetchone()[0]

            cursor.execute("SELECT minimum_output FROM settings WHERE id=1")
            minimum_output = cursor.fetchone()[0]

            if stars_to_withdraw < minimum_output:
                await update.message.reply_text(f"❌ Минимальная сумма для вывода: {minimum_output} ⭐.", reply_markup=back_button())
            elif stars_to_withdraw > available_stars:
                await update.message.reply_text(f"❌ У вас недостаточно звёзд. Доступно: {available_stars} ⭐.", reply_markup=back_button())
            else:
                # Добавляем заявку на вывод
                cursor.execute("INSERT INTO withdraw_requests (user_id, stars, status) VALUES (?, ?, 'pending')", (uid, stars_to_withdraw))
                conn.commit()

                # Уведомляем администраторов и сохраняем идентификаторы сообщений
                admin_messages = {}
                for admin in ADMIN_IDS:
                    msg = await context.bot.send_message(
                        admin,
                        f"🤑 <b>Запрос на вывод</b>\n\n"
                        f"👤 Пользователь: @{update.effective_user.username or uid}\n"
                        f"💸 Сумма: {stars_to_withdraw} ⭐\n\n"
                        f"Принять и отклонить заявку можно только через админ панель!",
                        parse_mode="HTML"
                    )
                    admin_messages[admin] = msg.message_id

                # Сохраняем идентификаторы сообщений в контексте
                context.bot_data[f"withdraw_request_{uid}"] = admin_messages

                await update.message.reply_text("✅ Запрос отправлен. Ожидайте ответа.", reply_markup=back_button())

            if uid in actions:
                actions.pop(uid, None)
                

        elif action == 'set_minimum_output':
            if uid != config["OWNER"]:  # Проверяем, является ли пользователь владельцем
                await update.message.reply_text("⛔ У вас нет доступа.")
                return

            # Проверяем, что пользователь ввёл число
            if not text.isdigit():
                await update.message.reply_text("❌ Неверный формат. Введите целое число.", reply_markup=admin_back())
                return

            # Обновляем минимальный вывод в базе данных
            new_minimum_output = int(text)
            cursor.execute("UPDATE settings SET minimum_output=? WHERE id=1", (new_minimum_output,))
            conn.commit()

            # Отправляем подтверждение пользователю
            await update.message.reply_text(
                f"✅ Минимальная сумма для вывода обновлена до {new_minimum_output} ⭐.",
                reply_markup=admin_back()
            )
            print(f"Минимальная сумма для вывода обновлена до {new_minimum_output} ⭐.")

            # Удаляем действие из `actions`
            if uid in actions:
                actions.pop(uid, None)
        
        return