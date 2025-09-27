from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from config import ADMIN_IDS
from database import Database
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminPanel:
    def __init__(self, db: Database):
        self.db = db

    def admin_menu(self, update: Update, context: CallbackContext):
        if update.effective_user.id not in ADMIN_IDS:
            update.message.reply_text("⛔ У вас нет прав доступа к админ-панели")
            return

        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🎞 Фильмы", callback_data="admin_movies")],
            [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📌 Каналы", callback_data="admin_channels")],
            [InlineKeyboardButton("🔄 Обновить базу", callback_data="admin_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text("👨‍💻 Админ-панель:", reply_markup=reply_markup)

    def handle_admin_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        
        if query.data == "admin_stats":
            self.show_stats(query)
        elif query.data == "admin_movies":
            self.show_movies_menu(query)
        elif query.data == "admin_channels":
            self.show_channels_menu(query)
        elif query.data == "admin_refresh":
            self.refresh_database(query, context)
        elif query.data == "admin_broadcast":
            query.edit_message_text("📢 Введите сообщение для рассылки (текст или медиа + текст):")
            context.user_data['awaiting_broadcast'] = True
        elif query.data == "admin_back":
            self.handle_admin_back(query)

    def show_stats(self, query):
        movies_count = self.db.get_movies_count()
        users_count = self.db.get_users_count()
        popular_codes = self.db.get_popular_codes(5)
        
        stats_text = f"""📊 Статистика бота:

🎬 Фильмов в базе: {movies_count}
👥 Пользователей: {users_count}

🔥 Последние добавленные коды:
"""
        for code in popular_codes:
            stats_text += f"• {code[0]}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(stats_text, reply_markup=reply_markup)

    def show_movies_menu(self, query):
        keyboard = [
            [InlineKeyboardButton("📋 Список фильмов", callback_data="movies_list")],
            [InlineKeyboardButton("➕ Добавить вручную", callback_data="movies_add")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("🎞 Управление фильмами:", reply_markup=reply_markup)

    def show_channels_menu(self, query):
        channels = self.db.get_all_channels()
        keyboard = []
        
        for channel_id, username, title in channels:
            keyboard.append([InlineKeyboardButton(f"❌ {title or username}", callback_data=f"channel_del_{channel_id}")])
        
        keyboard.append([InlineKeyboardButton("➕ Добавить канал", callback_data="channel_add")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("📌 Управление каналами:", reply_markup=reply_markup)

    def refresh_database(self, query, context):
        query.edit_message_text("🔄 Сканирую архив-канал...")
        # Здесь будет логика сканирования канала
        # Пока заглушка
        query.edit_message_text("✅ База фильмов обновлена!")

    def handle_admin_back(self, query):
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🎞 Фильмы", callback_data="admin_movies")],
            [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📌 Каналы", callback_data="admin_channels")],
            [InlineKeyboardButton("🔄 Обновить базу", callback_data="admin_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("👨‍💻 Админ-панель:", reply_markup=reply_markup)

def setup_admin_handlers(dp, admin_panel):
    dp.add_handler(CallbackQueryHandler(admin_panel.handle_admin_callback, pattern="^admin_"))
    dp.add_handler(CallbackQueryHandler(admin_panel.handle_admin_callback, pattern="^admin_back$"))