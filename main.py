import os
import re
import sqlite3
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Этапы обработки
NAME, CITY, PHOTO, HASHTAGS = range(4)

def init_db():
    conn = sqlite3.connect('leomatch.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT,
        username TEXT,
        photo_path TEXT,
        hashtags TEXT,
        city TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        liked_user_id INTEGER,
        is_mutual BOOLEAN DEFAULT 0,
        UNIQUE(user_id, liked_user_id)
    )
    ''')
    conn.commit()
    conn.close()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('leomatch.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name, username, photo_path, hashtags, city FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        name, username, photo_path, hashtags, sity = result

        await update.message.reply_text(f"Ваша анкета выглядит так:")
        profile_text = (
            f"<b>Город:</b> {sity}\n"
            f"<b>Имя:</b> {name}\n"
            f"<b>Ваш Id:</b> @{username}\n"
            f"<b>Хэштеги:</b> {hashtags}"
        )

        keyboard = [
            [InlineKeyboardButton("1. Смотреть анкеты.", callback_data="view_profiles")],
            [InlineKeyboardButton("2. Заполнить анкету заново.", callback_data="reset_profile")],
            [InlineKeyboardButton("3. Изменить фото.", callback_data="change_photo")],
            [InlineKeyboardButton("4. Изменить хэштеги.", callback_data="change_text")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        with open(photo_path, 'rb') as photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption=profile_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text("Привет! Введите своё имя.")
        return NAME

# Обработка имени
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    context.user_data['user_id'] = update.message.from_user.id
    context.user_data['username'] = update.message.from_user.username or "Unknown"
    await update.message.reply_text("Спасибо! Теперь введите ваш город.")
    return CITY

#обработка города
async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text.strip()
    await update.message.reply_text("Город сохранён! Теперь загрузите своё фото.")
    return PHOTO

# Обработка фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # Берём самое качественное фото
    file = await context.bot.get_file(photo.file_id)

    photo_path = f"photos/{update.message.from_user.id}.jpg"
    os.makedirs("photos", exist_ok=True)
    await file.download_to_drive(photo_path)

    context.user_data['photo_path'] = photo_path

    await update.message.reply_text(
        "Фото сохранено! Теперь введите минимум 3 хэштега (через запятую). Пример: спорт, кино, музыка"
    )
    return HASHTAGS

# Обработка хэштегов
async def handle_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hashtags = update.message.text.lower().split(', ')
    valid_hashtags = [f"#{tag}" for tag in hashtags if re.match(r'^[а-яa-z0-9]+$', tag, re.IGNORECASE)]

    if len(valid_hashtags) < 3:
        await update.message.reply_text("Пожалуйста, введите минимум 3 хэштега.")
        return HASHTAGS

    context.user_data['hashtags'] = ", ".join(valid_hashtags)

    conn = sqlite3.connect('leomatch.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, name, username, photo_path, hashtags, city) VALUES (?, ?, ?, ?, ?, ?)",
        (
            context.user_data['user_id'],
            context.user_data['name'],
            context.user_data['username'],
            context.user_data['photo_path'],
            context.user_data['hashtags'],
            context.user_data['city']
        )
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("Вы успешно зарегистрированы! Спасибо.")
    await myprofile(update, context)
    return ConversationHandler.END

# Команда /myprofile
async def myprofile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('leomatch.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name, username, photo_path, hashtags, city FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        name, username, photo_path, hashtags, sity = result

        await update.message.reply_text(f"Ваша анкета выглядит так:")
        profile_text = (
            f"<b>Имя:</b> {name}\n"
            f"<b>Город:</b> {sity}\n"
            f"<b>Ваш Id:</b> @{username}\n"
            f"<b>Хэштеги:</b> {hashtags}"
        )

        keyboard = [
            [InlineKeyboardButton("1. Смотреть анкеты.", callback_data="view_profiles")],
            [InlineKeyboardButton("2. Заполнить анкету заново.", callback_data="reset_profile")],
            [InlineKeyboardButton("3. Изменить фото.", callback_data="change_photo")],
            [InlineKeyboardButton("4. Изменить хэштеги.", callback_data="change_text")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        with open(photo_path, 'rb') as photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption=profile_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text("Профиль не найден. Начните регистрацию с команды /start.")

# Замена фото
async def handle_new_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("change_photo"):
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_path = f"photos/{update.message.from_user.id}.jpg"
        os.makedirs("photos", exist_ok=True)
        await file.download_to_drive(photo_path)

        conn = sqlite3.connect('leomatch.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET photo_path = ? WHERE user_id = ?", (photo_path, update.message.from_user.id))
        conn.commit()
        conn.close()

        context.user_data["change_photo"] = False
        await update.message.reply_text("Ваше фото обновлено!")
    else:
        await update.message.reply_text("Это фото не используется для изменения профиля.")

# Замена текста
async def handle_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("change_text"):
        hashtags = update.message.text.lower().split(', ')
        valid_hashtags = []
        for tag in hashtags:
            if re.match(r'^[а-яa-z0-9]+$', tag, re.IGNORECASE):
                valid_hashtags.append(f"#{tag}")
            else:
                await update.message.reply_text(
                    f"Хэштег '{tag}' некорректен. Используйте только буквы и цифры."
                )
                return

        hashtags_str = ", ".join(valid_hashtags)
        conn = sqlite3.connect('leomatch.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET hashtags = ? WHERE user_id = ?", (hashtags_str, update.message.from_user.id))
        conn.commit()
        conn.close()

        context.user_data["change_text"] = False
        await update.message.reply_text("Ваши хэштеги обновлены!")
    else:
        await update.message.reply_text("Этот текст не используется для изменения профиля.")

# Отмена регистрации
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "view_profiles":
        await show_profiles(update, context)
    elif query.data == "reset_profile":
        conn = sqlite3.connect('leomatch.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        await query.message.reply_text("Ваш профиль был удалён. Начните заново с команды /start.")
    elif query.data == "change_photo":
        await query.message.reply_text("Пожалуйста, отправьте новое фото для вашего профиля.")
        context.user_data["change_photo"] = True
    elif query.data == "change_text":
        await query.message.reply_text("Введите новые хэштеги через запятую.")
        context.user_data["change_text"] = True
    elif query.data.startswith("like_"):
        liked_user_id = int(query.data.split("_")[1])
        await handle_like(update, context, liked_user_id)
    elif query.data.startswith("dislike_"):
        await handle_dislike(update, context, query.data)
    elif query.data == "view_likes":
        await show_likes(update, context)
    elif query.data.startswith("show_"):
        liked_user_id = int(query.data.split("_")[1])
        await show_liked_user_profile(update, context, liked_user_id)
    elif query.data.startswith("hide_"):
        await update.callback_query.message.edit_text("Вы решили не смотреть анкеты пользователей, которым понравились.")

async def show_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    conn = sqlite3.connect('leomatch.db')
    cursor = conn.cursor()

    cursor.execute("SELECT city, hashtags FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await query.message.reply_text("Ваш профиль не найден. Зарегистрируйтесь с помощью команды /start.")
        return

    user_city, user_hashtags = user_data
    user_hashtags_set = set(user_hashtags.split(', '))

    cursor.execute("SELECT user_id, name, username, photo_path, hashtags FROM users WHERE user_id != ? AND city = ?", (user_id, user_city))
    profiles = cursor.fetchall()
    conn.close()

    recommended_profiles = []
    for profile_user_id, name, username, photo_path, hashtags in profiles:
        profile_hashtags_set = set(hashtags.split(', '))
        if len(user_hashtags_set.intersection(profile_hashtags_set)) >= 2:
            recommended_profiles.append((profile_user_id, name, username, photo_path, hashtags))

    if recommended_profiles:
        random.shuffle(recommended_profiles)
        context.user_data['profile_queue'] = recommended_profiles
        await display_profile(update, context)
    else:
        await query.message.reply_text("Подходящих анкет в вашем городе не найдено.")


async def display_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    profile_queue = context.user_data.get('profile_queue', [])

    if profile_queue:
        profile_user_id, name, username, photo_path, hashtags = profile_queue.pop(0)
        profile_text = (
            f"<b>Имя:</b> {name}\n"
            f"<b>Хэштеги:</b> {hashtags}"
        )
        keyboard = [
            [InlineKeyboardButton("👍", callback_data=f"like_{profile_user_id}"),
             InlineKeyboardButton("👎", callback_data=f"dislike_{profile_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        with open(photo_path, 'rb') as photo_file:
            await query.message.reply_photo(
                photo=photo_file,
                caption=profile_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    else:
        await query.message.reply_text("Рекомендованные анкеты закончились, возвращайтесь завтра.")

async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE, liked_user_id: int):
    user_id = update.callback_query.from_user.id

    conn = sqlite3.connect('leomatch.db')
    cursor = conn.cursor()

    cursor.execute("INSERT OR IGNORE INTO likes (user_id, liked_user_id) VALUES (?, ?)", (user_id, liked_user_id))
    conn.commit()

    cursor.execute("SELECT user_id FROM likes WHERE user_id = ? AND liked_user_id = ?", (liked_user_id, user_id))
    if cursor.fetchone():
        cursor.execute("UPDATE likes SET is_mutual = 1 WHERE (user_id = ? AND liked_user_id = ?) OR (user_id = ? AND liked_user_id = ?)",
                       (user_id, liked_user_id, liked_user_id, user_id))
        conn.commit()
        cursor.execute("SELECT username FROM users WHERE user_id = ?", (liked_user_id,))
        liked_username = cursor.fetchone()[0]
        await update.callback_query.message.reply_text(f"У вас взаимная симпатия с @{liked_username}!")
        await context.bot.send_message(liked_user_id, f"У вас взаимная симпатия с @{update.callback_query.from_user.username}!")
    else:
        keyboard = [
            [InlineKeyboardButton("Показать", callback_data=f"show_{user_id}"),
             InlineKeyboardButton("Не показывать", callback_data=f"hide_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            liked_user_id,
            f"Вы кому-то понравились! Хотите увидеть его анкету?",
            reply_markup=reply_markup
        )
    conn.close()

    await update.callback_query.edit_message_reply_markup(reply_markup=None)
    await display_profile(update, context)

async def handle_dislike(update: Update, context: ContextTypes.DEFAULT_TYPE, query_data: str):
    await update.callback_query.edit_message_reply_markup(reply_markup=None)
    await display_profile(update, context)

async def show_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    conn = sqlite3.connect('leomatch.db')
    cursor = conn.cursor()

    cursor.execute("SELECT u.user_id, u.name, u.username, u.photo_path, u.hashtags FROM likes l JOIN users u ON l.user_id = u.user_id WHERE l.liked_user_id = ? AND l.is_mutual = 0", (user_id,))
    profiles = cursor.fetchall()
    conn.close()

    if profiles:
        for profile_user_id, name, username, photo_path, hashtags in profiles:
            profile_text = (
                f"<b>Имя:</b> {name}\n"
                f"<b>Хэштеги:</b> {hashtags}"
            )
            keyboard = [
                [InlineKeyboardButton("👍", callback_data=f"like_{profile_user_id}"),
                 InlineKeyboardButton("👎", callback_data=f"dislike_{profile_user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            with open(photo_path, 'rb') as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=profile_text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
    else:
        await update.message.reply_text("Пока нет анкет, которым вы понравились.")

async def show_liked_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, liked_user_id: int):
    conn = sqlite3.connect('leomatch.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name, username, photo_path, hashtags, city FROM users WHERE user_id = ?", (liked_user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        name, username, photo_path, hashtags, sity = profile
        profile_text = (
            f"<b>Имя:</b> {name}\n"
            f"<b>Хэштеги:</b> {hashtags}"
        )
        keyboard = [
            [InlineKeyboardButton("👍", callback_data=f"like_{liked_user_id}"),
             InlineKeyboardButton("👎", callback_data=f"dislike_{liked_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        with open(photo_path, 'rb') as photo_file:
            await update.callback_query.message.reply_photo(
                photo=photo_file,
                caption=profile_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    else:
        await update.callback_query.message.reply_text("Анкета не найдена.")

# Основной метод
def main():
    init_db()

    application = Application.builder().token("8087708008:AAEQBHTwwv7GDvXkJngs7MkdBPlKI1VIBEw").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city)],
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            HASHTAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hashtags)],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('myprofile', myprofile))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_new_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_text))

    application.run_polling()

if __name__ == '__main__':
    main()