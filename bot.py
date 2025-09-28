import logging
import sqlite3
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler
from telegram.ext import filters
from config import BOT_TOKEN, ADMIN_IDS, ARCHIVE_CHANNEL_ID, REQUIRED_CHANNELS, CODES_CHANNEL
from config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# База данных
class Database:
    def __init__(self, db_path="movies.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                caption TEXT,
                added_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                channel_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                title TEXT
            )
        ''')
        
        # Добавляем начальные каналы из config
        for channel_id, username in REQUIRED_CHANNELS.items():
            # Убедимся, что username начинается с @ и нет дублирования
            clean_username = username.strip()
            if not clean_username.startswith('@'):
                clean_username = '@' + clean_username
            cursor.execute(
                'INSERT OR IGNORE INTO channels (channel_id, username, title) VALUES (?, ?, ?)',
                (channel_id, clean_username, None)
            )
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    
    def add_movie(self, code, file_id, caption=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT OR REPLACE INTO movies (code, file_id, caption) VALUES (?, ?, ?)', 
                         (code, file_id, caption))
            conn.commit()
            print(f"✅ Фильм #{code} добавлен в базу")
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления фильма: {e}")
            return False
        finally:
            conn.close()
    
    def get_movie(self, code):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT code, file_id, caption FROM movies WHERE code = ?', (code,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def delete_movie(self, code):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM movies WHERE code = ?', (code,))
        conn.commit()
        conn.close()
        print(f"✅ Фильм #{code} удален")
        return True
    
    def add_user(self, user_id, username=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
        conn.commit()
        conn.close()
    
    def update_user_activity(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def get_all_movies(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT code, caption FROM movies ORDER BY code')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def movie_exists(self, code):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM movies WHERE code = ?', (code,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def get_all_users(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username FROM users')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_users_count(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    def add_channel(self, channel_id, username, title=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Чистим username от лишних @
        clean_username = username.strip()
        if clean_username.startswith('@@'):
            clean_username = '@' + clean_username[2:]
        elif not clean_username.startswith('@'):
            clean_username = '@' + clean_username
            
        cursor.execute('INSERT OR REPLACE INTO channels (channel_id, username, title) VALUES (?, ?, ?)', 
                      (channel_id, clean_username, title))
        conn.commit()
        conn.close()
        return True
    
    def get_all_channels(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT channel_id, username, title FROM channels')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def delete_channel(self, channel_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
        conn.commit()
        conn.close()
        return True

db = Database()

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет подписку на все каналы из базы и возвращает список неподписанных"""
    channels = db.get_all_channels()
    not_subscribed = []
    
    for channel_id, username, title in channels:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append((channel_id, username, title))
                logger.info(f"❌ Пользователь {user_id} не подписан на канал {username}")
            else:
                logger.info(f"✅ Пользователь {user_id} подписан на канал {username}")
        except Exception as e:
            logger.error(f"Ошибка проверки подписки на канал {channel_id} ({username}): {e}")
            not_subscribed.append((channel_id, username, title))
    
    return not_subscribed

async def show_subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE, not_subscribed_channels):
    """Показывает кнопки для подписки на недостающие каналы"""
    if not not_subscribed_channels:
        return True
    
    keyboard = []
    for channel_id, username, title in not_subscribed_channels:
        channel_name = title or username
        # Убедимся, что username правильный для URL
        clean_username = username.lstrip('@')
        keyboard.append([InlineKeyboardButton(f"A'zo bolish {channel_name}", url=f"https://t.me/{clean_username}")])
    
    keyboard.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📢 Botdan foydalanish uchun kanallarimizga obuna bo'lishingiz kerak:\n\n" + \
           "\n".join([f"• {title or username}" for channel_id, username, title in not_subscribed_channels])
    
    try:
        if update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return False
    except Exception as e:
        logger.error(f"Obunani ko'rsatish xatosi: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username)
    db.update_user_activity(user.id)
    
    # Для админов пропускаем проверку подписки
    if user.id in ADMIN_IDS:
        movies_count = len(db.get_all_movies())
        users_count = db.get_users_count()
        
        await update.message.reply_text(
            f"👨‍💻 Добро пожаловать, администратор {user.first_name}!\n\n"
            f"📊 Статистика:\n"
            f"🎬 Фильмов: {movies_count}\n"
            f"👥 Пользователей: {users_count}\n\n"
            "Используйте /admin для панели управления\n"
            "Отправьте видео с подписью #код чтобы добавить фильм"
        )
        return
    
    # Для обычных пользователей проверяем подписку на ВСЕ каналы
    not_subscribed = await check_subscription(user.id, context)
    
    if not not_subscribed:
        await update.message.reply_text(
            f"🎬 Xush kelibsiz, {user.first_name}!\n\n"
            "Kodni kiriting videoni yuklab olish uchun.\n\n"
            f"📺 Video kodlarini kanalimizda ko'rishingiz mumkin: {CODES_CHANNEL}"
        )
    else:
        await show_subscription_required(update, context, not_subscribed)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.update_user_activity(user.id)
    
    # Админы могут всё без проверки подписки
    if user.id in ADMIN_IDS:
        text = update.message.text.strip()
        
        if text.isdigit() or re.match(r'^[a-zA-Z0-9]+$', text):
            movie = db.get_movie(text)
            if movie:
                code, file_id, caption = movie
                try:
                    await context.bot.send_video(
                        chat_id=user.id,
                        video=file_id,
                        caption=caption or f"Kod bo'yicha film {code}",
                        protect_content=True
                    )
                except Exception as e:
                    await update.message.reply_text(f"❌ Xato: {e}")
            else:
                await update.message.reply_text("❌ Film topilmadi")
        return
    
    # Обычные пользователи - проверяем подписку на ВСЕ каналы ПЕРЕД обработкой
    not_subscribed = await check_subscription(user.id, context)
    if not_subscribed:
        await show_subscription_required(update, context, not_subscribed)
        return
    
    text = update.message.text.strip()
    
    # Еще раз проверяем подписку (на случай если пользователь отправил код быстро)
    not_subscribed = await check_subscription(user.id, context)
    if not_subscribed:
        await show_subscription_required(update, context, not_subscribed)
        return
    
    if text.isdigit() or re.match(r'^[a-zA-Z0-9]+$', text):
        movie = db.get_movie(text)
        if movie:
            code, file_id, caption = movie
            try:
                # Отправляем фильм
                await context.bot.send_video(
                    chat_id=user.id,
                    video=file_id,
                    caption=caption or f"Kod bo'yicha film {code}",
                    protect_content=True
                )
                
                # Отправляем ссылку на канал с кодами
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"📺 Kodlarini kanalimizda ko'rishingiz mumkin: {CODES_CHANNEL}",
                    disable_web_page_preview=True
                )
                
                logger.info(f"✅ Пользователь {user.id} получил фильм {code}")
            except Exception as e:
                await update.message.reply_text("❌ Ошибка при отправке видео")
        else:
            await update.message.reply_text(
                f"❌ Ushbu kod bilan video topilmadi\n\n"
                f"📺 Kodlarini kanalimizda ko'rishingiz mumkin: {CODES_CHANNEL}"
            )
    else:
        try:
            await update.message.delete()
        except:
            pass

async def handle_admin_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка видео от админов"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        try:
            await update.message.delete()
        except:
            pass
        return
    
    message = update.message
    caption = message.caption or ""
    
    code_match = re.search(r'#(\w+)', caption)
    if not code_match:
        await message.reply_text("❌ Добавьте в подпись код в formatе #123")
        return
    
    code = code_match.group(1)
    
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document and message.document.mime_type and 'video' in message.document.mime_type:
        file_id = message.document.file_id
    
    if not file_id:
        await message.reply_text("❌ Сообщение не содержит видео")
        return
    
    try:
        if message.video:
            await context.bot.send_video(
                chat_id=ARCHIVE_CHANNEL_ID,
                video=file_id,
                caption=caption
            )
        else:
            await context.bot.send_document(
                chat_id=ARCHIVE_CHANNEL_ID,
                document=file_id,
                caption=caption
            )
        
        if db.add_movie(code, file_id, caption):
            await message.reply_text(f"✅ Фильм #{code} добавлен и опубликован!")
        else:
            await message.reply_text("❌ Ошибка добавления в базу")
            
    except Exception as e:
        await message.reply_text(f"❌ Ошибка публикации: {e}")

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки проверки подписки"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db.update_user_activity(user.id)
    
    # Проверяем подписку на ВСЕ каналы
    not_subscribed = await check_subscription(user.id, context)
    
    if not not_subscribed:
        await query.message.edit_text(
            f"✅ Ajoyib! Endi siz botdan foydalanishingiz mumkin.\n\n"
            "Kodni kiriting videoni yuklab olish uchun.\n\n"
            f"📺 Video kodlarini kanalimizda ko'rishingiz mumkin:: {CODES_CHANNEL}"
        )
    else:
        # Удаляем старое сообщение и показываем новое с актуальным списком каналов
        try:
            await query.message.delete()
        except:
            pass
        await show_subscription_required(update, context, not_subscribed)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Панель администратора"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав доступа")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🎬 Список фильмов", callback_data="admin_movies")],
        [InlineKeyboardButton("📌 Каналы для подписки", callback_data="admin_channels")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("👨‍💻 Панель администратора:", reply_markup=reply_markup)

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback от админ-панели"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_stats":
        await show_admin_stats(query)
    elif query.data == "admin_movies":
        await show_movies_management(query)
    elif query.data == "admin_channels":
        await show_channels_management(query)
    elif query.data == "admin_broadcast":
        await query.message.reply_text("📢 Для рассылки ответьте на сообщение командой /broadcast")
    elif query.data == "admin_back":
        await admin_panel_callback(query)
    elif query.data == "add_channel":
        await query.message.reply_text(
            "📝 Чтобы добавить канал, используйте команду:\n"
            "/addchannel <id> <@username> [название]\n\n"
            "Пример: /addchannel -100123456789 @my_channel \"Мой канал\""
        )
    elif query.data == "delete_channel":
        await show_delete_channel_menu(query)
    elif query.data.startswith("delete_channel_"):
        await handle_delete_channel(query)

async def show_admin_stats(query):
    """Показать статистику"""
    movies_count = len(db.get_all_movies())
    users_count = db.get_users_count()
    channels = db.get_all_channels()
    
    stats_text = f"""📊 Статистика бота:

🎬 Фильмов: {movies_count}
👥 Пользователей: {users_count}
📺 Каналов для подписки: {len(channels)}

Каналы:
"""
    for channel_id, username, title in channels:
        stats_text += f"• {title or username}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def show_movies_management(query):
    """Управление фильмами"""
    movies = db.get_all_movies()
    
    if movies:
        movies_text = "🎬 Список фильмов:\n\n"
        for code, caption in movies:
            movies_text += f"• #{code} - {caption[:30]}...\n" if caption else f"• #{code}\n"
        
        movies_text += f"\n🗑️ Удалить фильм: /delete <код>"
    else:
        movies_text = "📭 Фильмов пока нет"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(movies_text, reply_markup=reply_markup)

async def show_channels_management(query):
    """Управление каналами для подписки"""
    channels = db.get_all_channels()
    
    channels_text = "📌 Текущие каналы для подписки:\n\n"
    if channels:
        for channel_id, username, title in channels:
            channels_text += f"• {title or username}\n"
    else:
        channels_text += "📭 Каналов пока нет\n"
    
    channels_text += "\n👇 Выберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🗑️ Удалить канал", callback_data="delete_channel")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(channels_text, reply_markup=reply_markup)

async def show_delete_channel_menu(query):
    """Меню удаления каналов"""
    channels = db.get_all_channels()
    
    if not channels:
        await query.message.reply_text("📭 Нет каналов для удаления")
        return
    
    keyboard = []
    for channel_id, username, title in channels:
        channel_name = title or username
        keyboard.append([InlineKeyboardButton(f"🗑️ {channel_name}", callback_data=f"delete_channel_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_channels")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📌 Выберите канал для удаления:", reply_markup=reply_markup)

async def handle_delete_channel(query):
    """Обработчик удаления канала"""
    try:
        channel_id = int(query.data.split('_')[2])
        if db.delete_channel(channel_id):
            await query.message.reply_text("✅ Канал удален!")
            await show_channels_management(query)
        else:
            await query.message.reply_text("❌ Ошибка удаления канала")
    except (ValueError, IndexError):
        await query.message.reply_text("❌ Ошибка обработки запроса")

async def admin_panel_callback(query):
    """Вернуться в админ-панель"""
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🎬 Список фильмов", callback_data="admin_movies")],
        [InlineKeyboardButton("📌 Каналы для подписки", callback_data="admin_channels")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("👨‍💻 Панель администратора:", reply_markup=reply_markup)

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассылка сообщения всем пользователям"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    
    if update.message.reply_to_message:
        users = db.get_all_users()
        success = 0
        failed = 0
        
        for user_id, username in users:
            try:
                await update.message.reply_to_message.copy(user_id)
                success += 1
            except:
                failed += 1
        
        await update.message.reply_text(f"✅ Рассылка завершена\nУспешно: {success}\nНе удалось: {failed}")
    else:
        await update.message.reply_text("❌ Ответьте на сообщение для рассылки")

async def delete_movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить фильм по коду"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    
    if context.args:
        code = context.args[0]
        if db.delete_movie(code):
            await update.message.reply_text(f"✅ Фильм #{code} удален")
        else:
            await update.message.reply_text(f"❌ Фильм #{code} не найден")
    else:
        await update.message.reply_text("❌ Укажите код фильма: /delete <код>")

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить канал для подписки"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    
    if context.args and len(context.args) >= 2:
        try:
            channel_id = int(context.args[0])
            username = context.args[1]
            title = " ".join(context.args[2:]) if len(context.args) > 2 else None
            
            if db.add_channel(channel_id, username, title):
                await update.message.reply_text(f"✅ Канал @{username} добавлен!")
            else:
                await update.message.reply_text("❌ Ошибка добавления канала")
        except ValueError:
            await update.message.reply_text("❌ ID канала должен быть числом")
    else:
        await update.message.reply_text(
            "❌ Использование: /addchannel <id> <@username> [название]\n\n"
            "Пример: /addchannel -100123456789 @my_channel \"Мой канал\""
        )

async def delete_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить канал для подписки"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    
    if context.args:
        try:
            channel_id = int(context.args[0])
            if db.delete_channel(channel_id):
                await update.message.reply_text(f"✅ Канал удален!")
            else:
                await update.message.reply_text("❌ Канал не найден")
        except ValueError:
            await update.message.reply_text("❌ ID канала должен быть числом")
    else:
        await update.message.reply_text("❌ Укажите ID канала: /deletechannel <id>")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("delete", delete_movie_command))
    application.add_handler(CommandHandler("addchannel", add_channel_command))
    application.add_handler(CommandHandler("deletechannel", delete_channel_command))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(
        (filters.VIDEO | filters.Document.ALL) & filters.CAPTION,
        handle_admin_video
    ))
    
    # Обработчики callback-кнопок
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^add_channel$"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^delete_channel$"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^delete_channel_"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_back$"))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    print("🤖 Бот запущен!")
    print("📺 Коды фильмов в канале:", CODES_CHANNEL)
    
    application.run_polling()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Ошибка в боте:", exc_info=context.error)

if __name__ == "__main__":
    main()