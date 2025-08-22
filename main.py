import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from data_manager import DataManager
import config
from messages import ADMIN_MESSAGES, USER_MESSAGES, ERROR_MESSAGES, SUCCESS_MESSAGES, NOTIFICATION_MESSAGES, CREATION_MESSAGES
from handlers import CallbackHandler, TextHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TotalizerBot:
    def __init__(self):
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        self.data_manager = DataManager(config.DATA_DIR)
        self.config = config
        
        # Инициализируем обработчики
        self.callback_handler = CallbackHandler(self)
        self.text_handler = TextHandler(self)
        
        self.setup_handlers()
    
    def get_main_menu(self, is_admin: bool = False):
        """Создание главного меню"""
        keyboard = [
            [KeyboardButton("🎲 События"), KeyboardButton("💰 Баланс")],
            [KeyboardButton("🎯 Мои ставки"), KeyboardButton("💡 Предложить событие")],
            [KeyboardButton("ℹ️ Помощь")]
        ]
        
        if is_admin:
            keyboard.append([KeyboardButton("👑 Админ панель")])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    def get_admin_menu(self):
        """Создание админского меню"""
        keyboard = [
            [KeyboardButton("🆕 Создать событие"), KeyboardButton("🔒 Закрыть событие")],
            [KeyboardButton("📋 Предложения"), KeyboardButton("💵 Добавить баланс")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("◀️ Главное меню")]
        ]
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    # ========== УТИЛИТНЫЕ МЕТОДЫ ==========
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка является ли пользователь администратором"""
        return user_id == config.ADMIN_ID
    
    async def check_admin_access(self, update: Update, error_message: str = "❌ У вас нет прав администратора") -> bool:
        """Проверка прав администратора с автоматическим ответом при отказе"""
        user = update.effective_user
        if not self.is_admin(user.id):
            if hasattr(update, 'message') and update.message:
                await update.message.reply_text(error_message)
            elif hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(error_message)
            return False
        return True
    
    def create_cancel_button(self, callback_data: str, text: str = "❌ Отменить") -> InlineKeyboardButton:
        """Создание стандартной кнопки отмены"""
        return InlineKeyboardButton(text, callback_data=callback_data)
    
    def create_back_button(self, callback_data: str, text: str = "🔙 Назад") -> InlineKeyboardButton:
        """Создание стандартной кнопки возврата"""
        return InlineKeyboardButton(text, callback_data=callback_data)
        
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Команды пользователей и админов
        command_handlers = {
            # Основные команды
            "start": self.start,
            "help": self.help_command,
            "balance": self.balance,
            "events": self.show_events,
            "mybets": self.my_bets,
            # Админские команды
            "admin": self.admin_panel,
            "create_event": self.create_event,
            "close_event": self.close_event,
            "add_balance": self.add_balance,
        }
        
        # Регистрируем все команды
        for command, handler_func in command_handlers.items():
            self.application.add_handler(CommandHandler(command, handler_func))
        
        # Специальные обработчики
        special_handlers = [
            (CallbackQueryHandler, self.button_callback),
            (MessageHandler, self.handle_text, filters.TEXT & ~filters.COMMAND),
            (MessageHandler, self.handle_photo, filters.PHOTO),
        ]
        
        # Регистрируем специальные обработчики
        for handler_args in special_handlers:
            if len(handler_args) == 2:
                handler_class, handler_func = handler_args
                self.application.add_handler(handler_class(handler_func))
            else:
                handler_class, handler_func, handler_filter = handler_args
                self.application.add_handler(handler_class(handler_filter, handler_func))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        
        try:
            # Проверяем, есть ли пользователь
            db_user = self.data_manager.get_user(user.id)
            
            if not db_user:
                # Создаем нового пользователя
                db_user = self.data_manager.create_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name
                )
            
            # Используем сообщение из файла messages.py
            welcome_text = USER_MESSAGES['start']
            
            if user.id == config.ADMIN_ID:
                welcome_text += "\n👑 Вам доступна админ панель!"
            
            # Показываем меню с кнопками
            is_admin = user.id == config.ADMIN_ID
            reply_markup = self.get_main_menu(is_admin)
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка в start: {e}")
            await update.message.reply_text("❌ Произошла ошибка при запуске")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        user = update.effective_user
        
        help_text = USER_MESSAGES['help']
        
        # Показываем меню
        is_admin = user.id == config.ADMIN_ID
        reply_markup = self.get_main_menu(is_admin)
        
        await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /balance"""
        user = update.effective_user
        
        try:
            db_user = self.data_manager.get_user(user.id)
            if db_user:
                # Добавляем информацию об активных ставках
                active_bets = self.data_manager.get_active_bets_count(user.id)
                
                active_bets_info = f"\n🎯 Активных ставок: {active_bets}" if active_bets > 0 else ""
                
                balance_text = CREATION_MESSAGES['user_balance'].format(
                    balance=db_user['balance'],
                    active_bets_info=active_bets_info
                )
                
                # Показываем меню
                is_admin = user.id == config.ADMIN_ID
                reply_markup = self.get_main_menu(is_admin)
                
                await update.message.reply_text(balance_text, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
        except Exception as e:
            logger.error(f"Ошибка в balance: {e}")
            await update.message.reply_text("❌ Ошибка при получении баланса")

    async def show_events(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /events - показать активные события"""
        try:
            events = self.data_manager.get_active_events()
            
            if not events:
                await update.message.reply_text("📭 Нет активных событий для ставок")
                return
            
            keyboard = []
            for event in events:
                button_text = f"🎯 {event['title']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"event_{event['id']}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🎲 **Активные события для ставок:**\n\nВыберите событие:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка в show_events: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке событий")

    async def my_bets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /mybets - показать ставки пользователя"""
        user = update.effective_user
        
        try:
            db_user = self.data_manager.get_user(user.id)
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            bets = self.data_manager.get_user_bets(user.id, 10)
            
            if not bets:
                await update.message.reply_text("📭 У вас нет ставок")
                return
            
            # Собираем список ставок
            bets_list = []
            for bet in bets:
                event = self.data_manager.get_event(bet['event_id'])
                if not event:
                    continue
                
                option_text = event['option1'] if bet['option'] == 1 else event['option2']
                
                if event['is_active']:
                    status = "⏳ Активна"
                elif bet['is_won'] is True:
                    win_amount = bet['amount'] * bet['odds']
                    status = f"✅ Выиграна (+{win_amount:.2f} монет)"
                elif bet['is_won'] is False:
                    status = "❌ Проиграна"
                else:
                    status = "⏸ Ждет результата"
                
                bet_item = CREATION_MESSAGES['bet_item'].format(
                    event_title=event['title'],
                    option=option_text,
                    amount=bet['amount'],
                    odds=bet['odds'],
                    status=status
                ).strip()
                
                bets_list.append(bet_item)
            
            bets_text = CREATION_MESSAGES['user_bets_list'].format(
                bets_list='\n\n'.join(bets_list)
            )
            
            # Показываем меню
            is_admin = user.id == config.ADMIN_ID
            reply_markup = self.get_main_menu(is_admin)
            
            await update.message.reply_text(bets_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка в my_bets: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке ставок")

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Админская панель"""
        if not await self.check_admin_access(update, "❌ У вас нет доступа к админ-панели"):
            return
        
        admin_text = ADMIN_MESSAGES['help']
        
        await update.message.reply_text(admin_text, parse_mode='Markdown')

    async def create_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание нового события"""
        if not await self.check_admin_access(update, "❌ У вас нет прав для создания событий"):
            return
        
        if not context.args:
            await update.message.reply_text(CREATION_MESSAGES['create_event_help'], parse_mode='Markdown')
            return
        
        try:
            # Соединяем все аргументы обратно в строку
            event_data = ' '.join(context.args)
            parts = event_data.split(';')
            
            if len(parts) < 5 or len(parts) > 6:
                await update.message.reply_text("❌ Неверный формат. Используйте: Название;Вариант1;Вариант2;Коэф1;Коэф2;URL_картинки (картинка необязательна)")
                return
            
            title = parts[0].strip()
            option1 = parts[1].strip()
            option2 = parts[2].strip()
            odds1 = float(parts[3].strip())
            odds2 = float(parts[4].strip())
            
            # Картинка необязательна
            image_url = None
            if len(parts) == 6:
                image_url = parts[5].strip()
                # Простая проверка URL
                if image_url and not (image_url.startswith('http://') or image_url.startswith('https://')):
                    await update.message.reply_text("❌ URL картинки должен начинаться с http:// или https://")
                    return
            
            event = self.data_manager.create_event(
                title=title,
                option1=option1,
                option2=option2,
                odds1=odds1,
                odds2=odds2,
                image_url=image_url
            )
            
            success_text = SUCCESS_MESSAGES['event_created_simple'].format(
                title=event['title'],
                option1=event['option1'],
                option2=event['option2'],
                odds1=event['odds1'],
                odds2=event['odds2'],
                event_id=event['id']
            )
            
            if event.get('image_file_id') or event.get('image_url'):
                success_text += f"\n🖼️ Картинка прикреплена"
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text("❌ Ошибка в коэффициентах. Используйте числа (например: 1.5)")
        except Exception as e:
            logger.error(f"Ошибка при создании события: {e}")
            await update.message.reply_text("❌ Ошибка при создании события")

    async def close_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Закрытие события и подведение итогов"""
        if not await self.check_admin_access(update, "❌ У вас нет прав для закрытия событий"):
            return
        
        if len(context.args) != 2:
            await update.message.reply_text("❌ Формат: /close_event [ID события] [результат: 1 или 2]")
            return
        
        try:
            event_id = int(context.args[0])
            result = int(context.args[1])
            
            if result not in [1, 2]:
                await update.message.reply_text("❌ Результат должен быть 1 или 2")
                return
            
            event = self.data_manager.get_event(event_id)
            if not event:
                await update.message.reply_text("❌ Событие не найдено")
                return
            
            if not event['is_active']:
                await update.message.reply_text("❌ Событие уже закрыто")
                return
            
            # Закрываем событие
            self.data_manager.close_event(event_id, result)
            
            # Подводим итоги ставок
            stats = self.data_manager.process_event_results(event_id, result)
            
            # Уведомляем всех игроков о результатах их ставок
            await self.notify_players_about_results(event, result)
            
            winning_option = event['option1'] if result == 1 else event['option2']
            
            result_text = SUCCESS_MESSAGES['event_closed_simple'].format(
                title=event['title'],
                winning_option=winning_option,
                total_bets=stats['total_bets'],
                winners=stats['winners'],
                total_payouts=stats['total_payouts']
            )
            
            await update.message.reply_text(result_text, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text("❌ ID события и результат должны быть числами")
        except Exception as e:
            logger.error(f"Ошибка при закрытии события: {e}")
            await update.message.reply_text("❌ Ошибка при закрытии события")

    async def add_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление баланса пользователю"""
        if not await self.check_admin_access(update, "❌ У вас нет прав для изменения баланса"):
            return
        
        if len(context.args) != 2:
            await update.message.reply_text("❌ Формат: /add_balance [Telegram ID] [сумма]")
            return
        
        try:
            telegram_id = int(context.args[0])
            amount = float(context.args[1])
            
            target_user = self.data_manager.get_user(telegram_id)
            if not target_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            old_balance = target_user['balance']
            success = self.data_manager.add_balance(telegram_id, amount)
            
            if success:
                new_user = self.data_manager.get_user(telegram_id)
                result_text = SUCCESS_MESSAGES['balance_changed'].format(
                    first_name=target_user['first_name'] or 'Неизвестно',
                    telegram_id=target_user['telegram_id'],
                    old_balance=old_balance,
                    amount=amount,
                    new_balance=new_user['balance']
                )
                await update.message.reply_text(result_text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Ошибка при изменении баланса")
            
        except ValueError:
            await update.message.reply_text("❌ ID и сумма должны быть числами")
        except Exception as e:
            logger.error(f"Ошибка при изменении баланса: {e}")
            await update.message.reply_text("❌ Ошибка при изменении баланса")

    async def safe_edit_message(self, update: Update, text: str, parse_mode: str = 'HTML', reply_markup=None):
        """Безопасное редактирование сообщения (с фото или без)"""
        try:
            # Проверяем, есть ли фото в сообщении
            if update.callback_query.message.photo:
                # Если есть фото, удаляем сообщение и отправляем новое
                await update.callback_query.delete_message()
                await update.callback_query.message.reply_text(
                    text, 
                    parse_mode=parse_mode, 
                    reply_markup=reply_markup
                )
            else:
                # Если нет фото, редактируем существующее сообщение
                await update.callback_query.edit_message_text(
                    text, 
                    parse_mode=parse_mode, 
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Ошибка в safe_edit_message: {e}")
            try:
                # Резервный вариант - отправляем новое сообщение
                await update.callback_query.message.reply_text(
                    text, 
                    parse_mode=parse_mode, 
                    reply_markup=reply_markup
                )
            except:
                # Последний резерв - просто ответ на callback
                await update.callback_query.answer(text)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()
        
        # Делегируем обработку новому CallbackHandler
        await self.callback_handler.handle_callback(update, context, query.data)

    async def show_events_inline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать события в inline режиме"""
        try:
            events = self.data_manager.get_active_events()
            
            if not events:
                await self.safe_edit_message(update, "📭 Нет активных событий для ставок")
                return
            
            keyboard = []
            for event in events:
                button_text = f"🎯 {event['title']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"event_{event['id']}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.safe_edit_message(
                update,
                "🎲 <b>Активные события для ставок:</b>\n\nВыберите событие:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка в show_events_inline: {e}")
            await self.safe_edit_message(update, "❌ Ошибка при загрузке событий")

    async def show_event_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Показать детали события"""
        try:
            event_id = int(callback_data.split("_")[1])
            event = self.data_manager.get_event(event_id)
            
            if not event or not event['is_active']:
                await self.safe_edit_message(update, "❌ Событие не найдено или неактивно")
                return
            
            # Считаем общую сумму ставок
            event_bets = self.data_manager.get_event_bets(event_id)
            total_bets = len(event_bets)
            
            event_text = CREATION_MESSAGES['event_details'].format(
                title=event['title'],
                description=event['description'] or 'Описание отсутствует',
                option1=event['option1'],
                option2=event['option2'],
                odds1=event['odds1'],
                odds2=event['odds2'],
                total_bets=total_bets
            )
            
            keyboard = [
                [InlineKeyboardButton(f"1️⃣ {event['option1']} ({event['odds1']})", callback_data=f"bet_{event_id}_1")],
                [InlineKeyboardButton(f"2️⃣ {event['option2']} ({event['odds2']})", callback_data=f"bet_{event_id}_2")],
                [InlineKeyboardButton("◀️ Назад к событиям", callback_data="back_to_events")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Если есть картинка, отправляем её отдельно
            if event.get('image_file_id') or event.get('image_url'):
                try:
                    # Приоритет у file_id, потом URL
                    photo = event.get('image_file_id') or event.get('image_url')
                    
                    await update.callback_query.message.reply_photo(
                        photo=photo,
                        caption=event_text,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    # Удаляем предыдущее сообщение
                    await update.callback_query.delete_message()
                except Exception as e:
                    logger.error(f"Ошибка при отправке картинки: {e}")
                    # Если картинка не загрузилась, показываем без неё
                    await self.safe_edit_message(
                        update,
                        event_text + "\n\n⚠️ Картинка недоступна",
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
            else:
                await self.safe_edit_message(
                    update,
                    event_text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            
        except Exception as e:
            logger.error(f"Ошибка в show_event_details: {e}")
            await self.safe_edit_message(update, "❌ Ошибка при загрузке события")

    async def make_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Начать процесс создания ставки"""
        try:
            parts = callback_data.split("_")
            event_id = int(parts[1])
            option = int(parts[2])
            
            # Сохраняем данные в context для последующего использования
            context.user_data['betting_event_id'] = event_id
            context.user_data['betting_option'] = option
            context.user_data['betting_step'] = 'waiting_amount'
            
            event = self.data_manager.get_event(event_id)
            option_text = event['option1'] if option == 1 else event['option2']
            odds = event['odds1'] if option == 1 else event['odds2']
            
            bet_text = CREATION_MESSAGES['bet_amount_input'].format(
                event_title=event['title'],
                option_text=option_text,
                odds=odds
            )
            
            await self.safe_edit_message(update, bet_text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка в make_bet: {e}")
            await self.safe_edit_message(update, "❌ Ошибка при создании ставки")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        text = update.message.text
        
        # Делегируем обработку новому TextHandler
        await self.text_handler.handle_text(update, context, text)

    async def process_bet_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, amount_text: str):
        """Обработка суммы ставки"""
        user = update.effective_user
        
        try:
            amount = float(amount_text)
            
            if amount < 10:
                await update.message.reply_text("❌ Минимальная сумма ставки: 10 монет")
                return
            
            event_id = context.user_data.get('betting_event_id')
            option = context.user_data.get('betting_option')
            
            # Проверяем пользователя и его баланс
            db_user = self.data_manager.get_user(user.id)
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            if db_user['balance'] < amount:
                await update.message.reply_text(f"❌ Недостаточно средств. Ваш баланс: {db_user['balance']:.2f} монет")
                return
            
            # Проверяем событие
            event = self.data_manager.get_event(event_id)
            if not event or not event['is_active']:
                await update.message.reply_text("❌ Событие больше не активно")
                return
            
            # Создаем ставку
            odds = event['odds1'] if option == 1 else event['odds2']
            option_text = event['option1'] if option == 1 else event['option2']
            
            bet = self.data_manager.create_bet(
                telegram_id=user.id,
                event_id=event_id,
                amount=amount,
                option=option,
                odds=odds
            )
            
            # Очищаем временные данные
            context.user_data.clear()
            
            # Получаем обновленный баланс
            updated_user = self.data_manager.get_user(user.id)
            potential_win = amount * odds
            
            success_text = SUCCESS_MESSAGES['bet_accepted'].format(
                event_title=event['title'],
                option_text=option_text,
                amount=amount,
                odds=odds,
                potential_win=potential_win,
                new_balance=updated_user['balance']
            )
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            
        except ValueError as e:
            if "Недостаточно средств" in str(e) or "Событие не активно" in str(e):
                await update.message.reply_text(f"❌ {e}")
            else:
                await update.message.reply_text("❌ Введите корректную сумму (число)")
            context.user_data.clear()
        except Exception as e:
            logger.error(f"Ошибка при обработке ставки: {e}")
            await update.message.reply_text("❌ Ошибка при создании ставки")
            context.user_data.clear()

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий"""
        user = update.effective_user
        
        # Проверяем, находится ли пользователь в процессе создания события и ждет фото
        if (context.user_data.get('creating_event') and 
            user.id == config.ADMIN_ID and 
            context.user_data.get('event_step') == 'waiting_photo'):
            await self.process_event_photo(update, context)
        # Проверяем, создает ли пользователь предложение с фото
        elif (context.user_data.get('creating_proposal') and 
              context.user_data.get('proposal_step') == 'waiting_photo'):
            await self.process_proposal_photo(update, context)
        else:
            await update.message.reply_text(
                "🖼️ Красивая картинка! Но я пока не знаю, что с ней делать.\n"
                "Если хотите предложить событие с картинкой, используйте кнопку '💡 Предложить событие'.\n"
                "Если вы админ и хотите создать событие с картинкой, используйте кнопку '🆕 Создать событие'."
            )

    async def process_event_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фото для создания события"""
        photo = update.message.photo[-1]  # Берем фото наилучшего качества
        file_id = photo.file_id
        
        # Сохраняем file_id картинки
        context.user_data['event_image_file_id'] = file_id
        
        await update.message.reply_text(
            "✅ Картинка получена!\n\n"
            "Теперь введите название события:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отменить", callback_data="cancel_event_creation")
            ]])
        )
        
        context.user_data['event_step'] = 'waiting_title'

    async def process_proposal_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фото для создания предложения"""
        photo = update.message.photo[-1]  # Берем фото наилучшего качества
        file_id = photo.file_id
        
        # Сохраняем file_id картинки
        context.user_data['proposal_image_file_id'] = file_id
        
        await update.message.reply_text(
            "✅ Картинка получена!\n\n"
            "Теперь введите название события:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отменить", callback_data="cancel_proposal_creation")
            ]])
        )
        
        # Переходим к следующему шагу
        context.user_data['proposal_step'] = 'waiting_title'

    # ========== ОБРАБОТЧИКИ КНОПОК МЕНЮ ==========

    async def admin_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Переключение в админское меню"""
        if not await self.check_admin_access(update, "❌ У вас нет доступа к админ-панели"):
            return
        
        admin_text = ADMIN_MESSAGES['panel']
        
        reply_markup = self.get_admin_menu()
        await update.message.reply_text(admin_text, parse_mode='Markdown', reply_markup=reply_markup        )

    async def start_event_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать диалоговое создание события"""
        if not await self.check_admin_access(update, "❌ У вас нет прав для создания событий"):
            return
        
        # Очищаем предыдущие данные
        context.user_data.clear()
        context.user_data['creating_event'] = True
        context.user_data['event_step'] = 'choose_method'
        
        keyboard = [
            [InlineKeyboardButton("🖼️ С картинкой", callback_data="event_with_photo")],
            [InlineKeyboardButton("📝 Без картинки", callback_data="event_without_photo")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_event_creation")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🆕 **Создание нового события**\n\n"
            "Выберите способ создания:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def process_event_creation_step(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка шагов создания события"""
        step = context.user_data.get('event_step')
        
        if step == 'waiting_title':
            context.user_data['event_title'] = text
            context.user_data['event_step'] = 'waiting_option1'
            await update.message.reply_text(
                f"✅ Название: {text}\n\n📝 Введите первый вариант исхода:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="cancel_event_creation")
                ]])
            )
            
        elif step == 'waiting_option1':
            context.user_data['event_option1'] = text
            context.user_data['event_step'] = 'waiting_option2'
            await update.message.reply_text(
                f"✅ Первый вариант: {text}\n\n📝 Введите второй вариант исхода:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="cancel_event_creation")
                ]])
            )
            
        elif step == 'waiting_option2':
            context.user_data['event_option2'] = text
            context.user_data['event_step'] = 'waiting_odds1'
            await update.message.reply_text(
                f"✅ Второй вариант: {text}\n\n💰 Введите коэффициент для '{context.user_data['event_option1']}' (например: 1.8):",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="cancel_event_creation")
                ]])
            )
            
        elif step == 'waiting_odds1':
            try:
                odds1 = float(text)
                context.user_data['event_odds1'] = odds1
                context.user_data['event_step'] = 'waiting_odds2'
                await update.message.reply_text(
                    f"✅ Коэффициент для '{context.user_data['event_option1']}': {odds1}\n\n"
                    f"💰 Введите коэффициент для '{context.user_data['event_option2']}' (например: 2.1):",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Отменить", callback_data="cancel_event_creation")
                    ]])
                )
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число (например: 1.8)")
                
        elif step == 'waiting_odds2':
            try:
                odds2 = float(text)
                context.user_data['event_odds2'] = odds2
                await self.finalize_event_creation(update, context)
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число (например: 2.1)")

    async def finalize_event_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершение создания события"""
        try:
            event = self.data_manager.create_event(
                title=context.user_data['event_title'],
                option1=context.user_data['event_option1'],
                option2=context.user_data['event_option2'],
                odds1=context.user_data['event_odds1'],
                odds2=context.user_data['event_odds2'],
                image_file_id=context.user_data.get('event_image_file_id')
            )
            
            success_text = SUCCESS_MESSAGES['event_created_simple'].format(
                title=event['title'],
                option1=event['option1'],
                option2=event['option2'],
                odds1=event['odds1'],
                odds2=event['odds2'],
                event_id=event['id']
            )
            
            if event.get('image_file_id') or event.get('image_url'):
                success_text += "\n🖼️ Картинка прикреплена"
            
            # Показываем админское меню
            reply_markup = self.get_admin_menu()
            
            await update.message.reply_text(
                success_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Очищаем данные
            context.user_data.clear()
            
        except Exception as e:
            logger.error(f"Ошибка при создании события: {e}")
            await update.message.reply_text("❌ Ошибка при создании события")
            context.user_data.clear()

    async def start_event_with_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание события с фото"""
        context.user_data['creating_event'] = True
        context.user_data['event_step'] = 'waiting_photo'
        
        await update.callback_query.edit_message_text(
            "🖼️ **Создание события с картинкой**\n\n"
            "📷 Отправьте картинку для события:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отменить", callback_data="cancel_event_creation")
            ]])
        )

    async def start_event_without_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание события без фото"""
        context.user_data['creating_event'] = True
        context.user_data['event_step'] = 'waiting_title'
        
        await update.callback_query.edit_message_text(
            "📝 **Создание события без картинки**\n\n"
            "📝 Введите название события:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отменить", callback_data="cancel_event_creation")
            ]])
        )

    async def cancel_event_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена создания события"""
        context.user_data.clear()
        
        reply_markup = self.get_admin_menu()
        
        await update.callback_query.edit_message_text(
            "❌ Создание события отменено.\n\n"
            "👑 Вы в админ-панели:",
            reply_markup=reply_markup
        )

    async def back_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат в главное меню"""
        user = update.effective_user
        is_admin = user.id == config.ADMIN_ID
        
        reply_markup = self.get_main_menu(is_admin)
        await update.message.reply_text(
            "🏠 **Главное меню**\n\nВыберите действие из меню ниже:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def create_event_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню создания события"""
        if not await self.check_admin_access(update, "❌ У вас нет прав для создания событий"):
            return
        
        await update.message.reply_text(ADMIN_MESSAGES['event_creation_format'], parse_mode='Markdown')

    async def close_event_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню закрытия события"""
        if not await self.check_admin_access(update, "❌ У вас нет прав для закрытия событий"):
            return
        
        # Показываем активные события
        events = self.data_manager.get_active_events()
        
        if not events:
            await update.message.reply_text("📭 Нет активных событий для закрытия")
            return
        
        # Собираем список активных событий
        events_list = []
        for event in events:
            event_item = CREATION_MESSAGES['event_list_item'].format(
                event_id=event['id'],
                title=event['title'],
                option1=event['option1'],
                option2=event['option2']
            ).strip()
            events_list.append(event_item)
        
        help_text = CREATION_MESSAGES['close_event_help'].format(
            events_list='\n\n'.join(events_list)
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def add_balance_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню добавления баланса"""
        if not await self.check_admin_access(update, "❌ У вас нет прав для изменения баланса"):
            return
        
        await update.message.reply_text(ADMIN_MESSAGES['add_balance_format'], parse_mode='Markdown')

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику бота"""
        if not await self.check_admin_access(update, "❌ У вас нет прав для просмотра статистики"):
            return
        
        try:
            # Загружаем данные
            users = self.data_manager._load_json(self.data_manager.users_file)
            events = self.data_manager._load_json(self.data_manager.events_file)
            bets = self.data_manager._load_json(self.data_manager.bets_file)
            
            # Считаем статистику
            total_users = len(users)
            total_events = len(events)
            active_events = len([e for e in events.values() if e.get('is_active')])
            total_bets = len(bets)
            
            # Считаем общий баланс и общую сумму ставок
            total_balance = sum(user.get('balance', 0) for user in users.values())
            total_bet_amount = sum(bet.get('amount', 0) for bet in bets.values())
            
            # Считаем выигрышные ставки
            won_bets = len([b for b in bets.values() if b.get('is_won') is True])
            
            # Вычисляем процент выигрышей
            win_percentage = (won_bets/total_bets*100) if total_bets > 0 else 0
            
            stats_text = ADMIN_MESSAGES['detailed_stats'].format(
                total_users=total_users,
                total_balance=total_balance,
                total_events=total_events,
                active_events=active_events,
                total_bets=total_bets,
                won_bets=won_bets,
                win_percentage=win_percentage
            )
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка в show_stats: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке статистики")

    # ========== ПРЕДЛОЖЕНИЯ СОБЫТИЙ ==========

    async def start_proposal_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание предложения события"""
        user = update.effective_user
        
        # Очищаем предыдущие данные
        context.user_data.clear()
        
        keyboard = [
            [InlineKeyboardButton("🖼️ С картинкой", callback_data="proposal_with_photo")],
            [InlineKeyboardButton("📝 Без картинки", callback_data="proposal_without_photo")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_proposal_creation")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "💡 **Предложить событие**\n\n"
            "Выберите способ создания:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def start_proposal_with_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание предложения с фото"""
        context.user_data['creating_proposal'] = True
        context.user_data['proposal_step'] = 'waiting_photo'
        
        await update.callback_query.edit_message_text(
            "💡 **Предложение события с картинкой**\n\n"
            "📷 Отправьте картинку для события:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отменить", callback_data="cancel_proposal_creation")
            ]])
        )

    async def start_proposal_without_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание предложения без фото"""
        context.user_data['creating_proposal'] = True
        context.user_data['proposal_step'] = 'waiting_title'
        
        await update.callback_query.edit_message_text(
            "💡 **Предложение события без картинки**\n\n"
            "📝 Введите название события:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отменить", callback_data="cancel_proposal_creation")
            ]])
        )

    async def process_proposal_creation_step(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка шагов создания предложения"""
        step = context.user_data.get('proposal_step')
        
        if step == 'waiting_title':
            context.user_data['proposal_title'] = text
            context.user_data['proposal_step'] = 'waiting_option1'
            await update.message.reply_text(
                f"✅ Название: {text}\n\n📝 Введите первый вариант исхода:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="cancel_proposal_creation")
                ]])
            )
            
        elif step == 'waiting_option1':
            context.user_data['proposal_option1'] = text
            context.user_data['proposal_step'] = 'waiting_option2'
            await update.message.reply_text(
                f"✅ Первый вариант: {text}\n\n📝 Введите второй вариант исхода:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="cancel_proposal_creation")
                ]])
            )
            
        elif step == 'waiting_option2':
            context.user_data['proposal_option2'] = text
            context.user_data['proposal_step'] = 'waiting_description'
            await update.message.reply_text(
                f"✅ Второй вариант: {text}\n\n📝 Введите описание события (или напишите 'пропустить'):",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_description"),
                    InlineKeyboardButton("❌ Отменить", callback_data="cancel_proposal_creation")
                ]])
            )
            
        elif step == 'waiting_description':
            description = None if text.lower() == 'пропустить' else text
            await self.finalize_proposal_creation(update, context, description)

    async def finalize_proposal_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str = None):
        """Завершение создания предложения"""
        user = update.effective_user
        
        try:
            proposal = self.data_manager.create_proposal(
                telegram_id=user.id,
                title=context.user_data['proposal_title'],
                option1=context.user_data['proposal_option1'],
                option2=context.user_data['proposal_option2'],
                description=description,
                image_file_id=context.user_data.get('proposal_image_file_id')
            )
            
            # Формируем текст с учетом картинки
            image_info = "🖼️ С картинкой" if proposal.get('image_file_id') else "📝 Без картинки"
            
            success_text = CREATION_MESSAGES['proposal_sent_user'].format(
                title=proposal['title'],
                option1=proposal['option1'],
                option2=proposal['option2'],
                description=proposal['description'] or 'Не указано',
                image_info=image_info,
                proposal_id=proposal['id']
            )
            
            # Показываем главное меню
            is_admin = user.id == config.ADMIN_ID
            reply_markup = self.get_main_menu(is_admin)
            
            await update.message.reply_text(
                success_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Уведомляем администратора о новом предложении
            await self.notify_admin_about_proposal(proposal)
            
            # Очищаем данные
            context.user_data.clear()
            
        except Exception as e:
            logger.error(f"Ошибка при создании предложения: {e}")
            await update.message.reply_text("❌ Ошибка при создании предложения")
            context.user_data.clear()

    async def notify_admin_about_proposal(self, proposal: dict):
        """Уведомить администратора о новом предложении"""
        try:
            # Добавляем информацию о картинке
            image_info = "🖼️ С картинкой" if proposal.get('image_file_id') else "📝 Без картинки"
            
            notification_text = NOTIFICATION_MESSAGES['admin_new_proposal'].format(
                author=proposal['first_name'],
                username=proposal['username'] or 'нет username',
                title=proposal['title'],
                description=proposal['description'] or 'Не указано',
                option1=proposal['option1'],
                option2=proposal['option2'],
                image_info=image_info,
                proposal_id=proposal['id']
            )
            
            await self.application.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=notification_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка при уведомлении админа: {e}")

    async def show_proposals_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню предложений для админа"""
        if not await self.check_admin_access(update, "❌ У вас нет доступа к предложениям"):
            return
        
        try:
            pending_proposals = self.data_manager.get_pending_proposals()
            
            if not pending_proposals:
                await update.message.reply_text(
                    "📭 Нет ожидающих рассмотрения предложений",
                    reply_markup=self.get_admin_menu()
                )
                return
            
            proposals_text = "📋 **Ожидающие рассмотрения предложения:**\n\n"
            keyboard = []
            
            for proposal in pending_proposals[:10]:  # Показываем первые 10
                # Добавляем информацию о картинке
                image_info = "🖼️" if proposal.get('image_file_id') else "📝"
                proposals_text += f"**ID {proposal['id']}:** {proposal['title']} {image_info}\n"
                proposals_text += f"👤 От: {proposal['first_name']}\n"
                proposals_text += f"1️⃣ {proposal['option1']} | 2️⃣ {proposal['option2']}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(f"📋 Предложение {proposal['id']}", callback_data=f"proposal_view_{proposal['id']}")
                ])
            
            if len(pending_proposals) > 10:
                proposals_text += f"... и еще {len(pending_proposals) - 10} предложений"
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                proposals_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка в show_proposals_menu: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке предложений")

    async def show_proposals_inline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать предложения в inline режиме"""
        if not await self.check_admin_access(update, "❌ У вас нет доступа к предложениям"):
            return
        
        try:
            pending_proposals = self.data_manager.get_pending_proposals()
            
            if not pending_proposals:
                await update.callback_query.edit_message_text(
                    "📭 Нет ожидающих рассмотрения предложений",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
                    ]])
                )
                return
            
            proposals_text = "📋 **Ожидающие рассмотрения предложения:**\n\n"
            keyboard = []
            
            for proposal in pending_proposals[:10]:  # Показываем первые 10
                # Добавляем информацию о картинке
                image_info = "🖼️" if proposal.get('image_file_id') else "📝"
                proposals_text += f"**ID {proposal['id']}:** {proposal['title']} {image_info}\n"
                proposals_text += f"👤 От: {proposal['first_name']}\n"
                proposals_text += f"1️⃣ {proposal['option1']} | 2️⃣ {proposal['option2']}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(f"📋 Предложение {proposal['id']}", callback_data=f"proposal_view_{proposal['id']}")
                ])
            
            if len(pending_proposals) > 10:
                proposals_text += f"... и еще {len(pending_proposals) - 10} предложений"
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                proposals_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка в show_proposals_inline: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при загрузке предложений")

    async def handle_proposal_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка действий с предложениями"""
        if not await self.check_admin_access(update, "❌ Нет доступа"):
            return
        
        try:
            parts = callback_data.split("_")
            action = parts[1]
            proposal_id = int(parts[2])
            
            if action == "view":
                await self.show_proposal_details(update, context, proposal_id)
            elif action == "approve":
                await self.approve_proposal_dialog(update, context, proposal_id)
            elif action == "reject":
                await self.reject_proposal_dialog(update, context, proposal_id)
                
        except Exception as e:
            logger.error(f"Ошибка в handle_proposal_action: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при обработке предложения")

    async def show_proposal_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, proposal_id: int):
        """Показать детали предложения"""
        try:
            proposal = self.data_manager.get_proposal(proposal_id)
            
            if not proposal:
                await update.callback_query.edit_message_text("❌ Предложение не найдено")
                return
            
            # Добавляем информацию о картинке
            image_info = "🖼️ С картинкой" if proposal.get('image_file_id') else "📝 Без картинки"
            
            details_text = CREATION_MESSAGES['proposal_details'].format(
                proposal_id=proposal['id'],
                author=proposal['first_name'],
                username=proposal['username'] or 'нет username',
                title=proposal['title'],
                description=proposal['description'] or 'Не указано',
                option1=proposal['option1'],
                option2=proposal['option2'],
                image_info=image_info
            ) + f"""

📅 <b>Создано:</b> {proposal['created_at'][:16].replace('T', ' ')}
⏳ <b>Статус:</b> {proposal['status']}

Выберите действие:
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ Одобрить", callback_data=f"proposal_approve_{proposal_id}")],
                [InlineKeyboardButton("❌ Отклонить", callback_data=f"proposal_reject_{proposal_id}")],
                [InlineKeyboardButton("🔙 К списку", callback_data="back_to_proposals")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Если есть картинка, показываем её
            if proposal.get('image_file_id'):
                try:
                    await update.callback_query.message.reply_photo(
                        photo=proposal['image_file_id'],
                        caption=details_text,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    # Удаляем предыдущее сообщение
                    await update.callback_query.delete_message()
                except Exception as e:
                    logger.error(f"Ошибка при отправке картинки предложения: {e}")
                    # Если картинка не загрузилась, показываем без неё
                    await update.callback_query.edit_message_text(
                        details_text + "\n\n⚠️ Картинка недоступна",
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
            else:
                await update.callback_query.edit_message_text(
                    details_text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            
        except Exception as e:
            logger.error(f"Ошибка в show_proposal_details: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при загрузке предложения")

    async def approve_proposal_dialog(self, update: Update, context: ContextTypes.DEFAULT_TYPE, proposal_id: int):
        """Диалог ввода коэффициентов для одобрения предложения"""
        try:
            proposal = self.data_manager.get_proposal(proposal_id)
            
            if not proposal:
                await self.safe_edit_message(update, "❌ Предложение не найдено")
                return
            
            # Сразу начинаем ввод коэффициентов
            await self.start_custom_odds_input(update, context, proposal_id)
            
        except Exception as e:
            logger.error(f"Ошибка при запуске ввода коэффициентов: {e}")
            await self.safe_edit_message(update, "❌ Ошибка при запуске ввода коэффициентов")

    async def approve_proposal_with_odds(self, update: Update, context: ContextTypes.DEFAULT_TYPE, proposal_id: int, odds1: float, odds2: float):
        """Одобрить предложение с указанными коэффициентами"""
        try:
            proposal = self.data_manager.get_proposal(proposal_id)
            
            if not proposal:
                await self.safe_edit_message(update, "❌ Предложение не найдено")
                return
            
            # Одобряем с указанными коэффициентами
            result = self.data_manager.approve_proposal(proposal_id, odds1, odds2)
            
            success_text = CREATION_MESSAGES['proposal_approved_admin'].format(
                proposal_id=proposal_id,
                author=proposal['first_name'],
                event_title=result['event']['title'],
                event_id=result['event']['id'],
                odds1=odds1,
                odds2=odds2
            )
            
            # Уведомляем пользователя
            await self.notify_user_about_approval(proposal, result['event'])
            
            await self.safe_edit_message(
                update,
                success_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 К предложениям", callback_data="back_to_proposals")
                ]])
            )
            
            # Очищаем контекст
            context.user_data.pop('approving_proposal_id', None)
            
        except Exception as e:
            logger.error(f"Ошибка при одобрении предложения: {e}")
            await self.safe_edit_message(update, "❌ Ошибка при одобрении предложения")

    async def start_custom_odds_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, proposal_id: int):
        """Начать ввод пользовательских коэффициентов"""
        try:
            proposal = self.data_manager.get_proposal(proposal_id)
            
            if not proposal:
                await self.safe_edit_message(update, "❌ Предложение не найдено")
                return
            
            # Сохраняем состояние в контексте
            context.user_data['custom_odds_proposal_id'] = proposal_id
            context.user_data['custom_odds_step'] = 'waiting_odds1'
            
            custom_text = CREATION_MESSAGES['custom_odds_input_step1'].format(
                proposal_id=proposal_id,
                title=proposal['title'],
                option1=proposal['option1'],
                option2=proposal['option2']
            )
            
            keyboard = [
                [InlineKeyboardButton("❌ Отменить", callback_data=f"proposal_view_{proposal_id}")]
            ]
            
            await self.safe_edit_message(
                update,
                custom_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Ошибка при запуске ввода коэффициентов: {e}")
            await self.safe_edit_message(update, "❌ Ошибка при запуске ввода коэффициентов")

    async def handle_odds_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка выбора предустановленных коэффициентов"""
        try:
            # Парсим callback_data: "odds_1.5_2.5_123"
            parts = callback_data.split("_")
            odds1 = float(parts[1])
            odds2 = float(parts[2]) 
            proposal_id = int(parts[3])
            
            await self.approve_proposal_with_odds(update, context, proposal_id, odds1, odds2)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке выбора коэффициентов: {e}")
            await self.safe_edit_message(update, "❌ Ошибка при обработке коэффициентов")

    async def process_custom_odds_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка ввода пользовательских коэффициентов"""
        try:
            step = context.user_data.get('custom_odds_step')
            proposal_id = context.user_data.get('custom_odds_proposal_id')
            
            if not proposal_id:
                await update.message.reply_text("❌ Ошибка: предложение не найдено")
                context.user_data.clear()
                return
            
            proposal = self.data_manager.get_proposal(proposal_id)
            if not proposal:
                await update.message.reply_text("❌ Предложение не найдено")
                context.user_data.clear()
                return
            
            try:
                coefficient = float(text.replace(',', '.'))
                if coefficient <= 0 or coefficient > 10:
                    await update.message.reply_text("❌ Коэффициент должен быть числом от 0.1 до 10.0")
                    return
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число (например: 1.8)")
                return
            
            if step == 'waiting_odds1':
                # Сохраняем первый коэффициент
                context.user_data['custom_odds1'] = coefficient
                context.user_data['custom_odds_step'] = 'waiting_odds2'
                
                odds_text = CREATION_MESSAGES['custom_odds_input_step2'].format(
                    proposal_id=proposal_id,
                    title=proposal['title'],
                    option1=proposal['option1'],
                    option2=proposal['option2'],
                    odds1=coefficient
                )
                
                keyboard = [
                    [InlineKeyboardButton("❌ Отменить", callback_data=f"proposal_view_{proposal_id}")]
                ]
                
                await update.message.reply_text(
                    odds_text,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            elif step == 'waiting_odds2':
                # Получаем оба коэффициента и одобряем
                odds1 = context.user_data.get('custom_odds1')
                odds2 = coefficient
                
                if not odds1:
                    await update.message.reply_text("❌ Ошибка: первый коэффициент не найден")
                    context.user_data.clear()
                    return
                
                # Одобряем предложение с пользовательскими коэффициентами
                result = self.data_manager.approve_proposal(proposal_id, odds1, odds2)
                
                success_text = f"""
✅ <b>Предложение одобрено!</b>

📋 <b>Предложение #{proposal_id}</b> от {proposal['first_name']}
🎯 Создано событие <b>"{result['event']['title']}"</b> (ID: {result['event']['id']})
💰 <b>Коэффициенты:</b> {odds1} / {odds2}

Пользователь будет уведомлен об одобрении.
                """
                
                is_admin = update.effective_user.id == config.ADMIN_ID
                reply_markup = self.get_admin_menu() if is_admin else self.get_main_menu()
                
                await update.message.reply_text(
                    success_text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                
                # Уведомляем пользователя
                await self.notify_user_about_approval(proposal, result['event'])
                
                # Очищаем контекст
                context.user_data.clear()
                
        except Exception as e:
            logger.error(f"Ошибка при обработке пользовательских коэффициентов: {e}")
            await update.message.reply_text("❌ Ошибка при обработке коэффициентов")
            context.user_data.clear()

    async def reject_proposal_dialog(self, update: Update, context: ContextTypes.DEFAULT_TYPE, proposal_id: int):
        """Диалог отклонения предложения"""
        try:
            proposal = self.data_manager.get_proposal(proposal_id)
            
            if not proposal:
                await update.callback_query.edit_message_text("❌ Предложение не найдено")
                return
            
            # Отклоняем предложение
            success = self.data_manager.reject_proposal(proposal_id, "Отклонено администратором")
            
            if success:
                success_text = CREATION_MESSAGES['proposal_rejected_admin'].format(
                    proposal_id=proposal_id,
                    author=proposal['first_name'],
                    title=proposal['title']
                )
                
                # Уведомляем пользователя
                await self.notify_user_about_rejection(proposal)
                
                await update.callback_query.edit_message_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 К предложениям", callback_data="back_to_proposals")
                    ]])
                )
            else:
                await update.callback_query.edit_message_text("❌ Ошибка при отклонении предложения")
            
        except Exception as e:
            logger.error(f"Ошибка при отклонении предложения: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при отклонении предложения")

    async def notify_user_about_approval(self, proposal: dict, event: dict):
        """Уведомить пользователя об одобрении предложения"""
        try:
            notification_text = NOTIFICATION_MESSAGES['user_proposal_approved'].format(
                title=proposal['title'],
                proposal_id=proposal['id'],
                event_id=event['id'],
                odds1=event['odds1'],
                odds2=event['odds2']
            )
            
            await self.application.bot.send_message(
                chat_id=proposal['telegram_id'],
                text=notification_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя об одобрении: {e}")

    async def notify_user_about_rejection(self, proposal: dict):
        """Уведомить пользователя об отклонении предложения"""
        try:
            notification_text = NOTIFICATION_MESSAGES['user_proposal_rejected'].format(
                title=proposal['title']
            )
            
            await self.application.bot.send_message(
                chat_id=proposal['telegram_id'],
                text=notification_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя об отклонении: {e}")

    async def notify_players_about_results(self, event: dict, winning_option: int):
        """Уведомить всех игроков о результатах их ставок"""
        try:
            # Получаем все ставки на это событие
            event_bets = self.data_manager.get_event_bets(event['id'])
            
            if not event_bets:
                return
            
            winning_text = event['option1'] if winning_option == 1 else event['option2']
            
            # Группируем ставки по пользователям
            user_bets = {}
            for bet in event_bets:
                user_id = bet['telegram_id']
                if user_id not in user_bets:
                    user_bets[user_id] = []
                user_bets[user_id].append(bet)
            
            # Отправляем уведомления каждому игроку
            for user_id, bets in user_bets.items():
                try:
                    # Подсчитываем результаты для этого пользователя
                    total_bet_amount = 0
                    total_winnings = 0
                    won_bets = 0
                    lost_bets = 0
                    
                    bet_details = []
                    
                    for bet in bets:
                        total_bet_amount += bet['amount']
                        bet_option_text = event['option1'] if bet['option'] == 1 else event['option2']
                        
                        if bet['option'] == winning_option:
                            # Выигрышная ставка
                            payout = bet['amount'] * bet['odds']
                            total_winnings += payout
                            won_bets += 1
                            bet_details.append(f"✅ {bet_option_text}: {bet['amount']:.0f} → {payout:.0f} монет (коэф. {bet['odds']})")
                        else:
                            # Проигрышная ставка
                            lost_bets += 1
                            bet_details.append(f"❌ {bet_option_text}: {bet['amount']:.0f} монет (коэф. {bet['odds']})")
                    
                    # Формируем сообщение
                    if total_winnings > 0:
                        # Есть выигрыши
                        profit = total_winnings - total_bet_amount
                        if profit > 0:
                            result_emoji = "🎉"
                            result_text = f"Вы выиграли {profit:.0f} монет!"
                        else:
                            result_emoji = "😐"
                            result_text = f"Вы остались при своих (выиграли {total_winnings:.0f}, поставили {total_bet_amount:.0f})"
                    else:
                        result_emoji = "😔"
                        result_text = f"Вы проиграли {total_bet_amount:.0f} монет"
                    
                    # Выбираем подходящий шаблон в зависимости от результата
                    if profit > 0:
                        template = NOTIFICATION_MESSAGES['bet_result_win']
                    elif profit == 0:
                        template = NOTIFICATION_MESSAGES['bet_result_even']
                    else:
                        template = NOTIFICATION_MESSAGES['bet_result_loss']
                    
                    notification_text = template.format(
                        event_title=event['title'],
                        winning_option=winning_text,
                        bet_details=chr(10).join(bet_details),
                        result_text=result_text
                    )
                    
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=notification_text,
                        parse_mode='HTML'
                    )
                    
                except Exception as e:
                    logger.error(f"Ошибка при уведомлении игрока {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка при уведомлении игроков о результатах: {e}")

    async def cancel_proposal_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена создания предложения"""
        context.user_data.clear()
        
        is_admin = update.effective_user.id == config.ADMIN_ID
        reply_markup = self.get_main_menu(is_admin)
        
        await update.callback_query.edit_message_text(
            "❌ Создание предложения отменено.",
            reply_markup=reply_markup
        )

    async def skip_proposal_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пропустить описание предложения"""
        await self.finalize_proposal_creation_from_callback(update, context, None)

    async def finalize_proposal_creation_from_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str = None):
        """Завершение создания предложения из callback query"""
        user = update.effective_user
        
        try:
            proposal = self.data_manager.create_proposal(
                telegram_id=user.id,
                title=context.user_data['proposal_title'],
                option1=context.user_data['proposal_option1'],
                option2=context.user_data['proposal_option2'],
                description=description,
                image_file_id=context.user_data.get('proposal_image_file_id')
            )
            
            # Формируем текст с учетом картинки
            image_info = "🖼️ С картинкой" if proposal.get('image_file_id') else "📝 Без картинки"
            
            success_text = CREATION_MESSAGES['proposal_sent_user'].format(
                title=proposal['title'],
                option1=proposal['option1'],
                option2=proposal['option2'],
                description=proposal['description'] or 'Не указано',
                image_info=image_info,
                proposal_id=proposal['id']
            )
            
            # Показываем главное меню
            is_admin = user.id == config.ADMIN_ID
            reply_markup = self.get_main_menu(is_admin)
            
            # Отправляем новое сообщение вместо редактирования
            await update.callback_query.message.reply_text(
                success_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Удаляем предыдущее сообщение
            await update.callback_query.delete_message()
            
            # Уведомляем администратора о новом предложении
            await self.notify_admin_about_proposal(proposal)
            
            # Очищаем данные
            context.user_data.clear()
            
        except Exception as e:
            logger.error(f"Ошибка при создании предложения из callback: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при создании предложения")
            context.user_data.clear()

    async def back_to_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат в админское меню"""
        admin_text = ADMIN_MESSAGES['panel']
        
        reply_markup = self.get_admin_menu()
        
        await update.callback_query.edit_message_text(
            admin_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    def run(self):
        """Запуск бота"""
        print("🚀 Запуск Telegram бота-тотализатора...")
        print("✅ Файловое хранилище инициализировано")
        
        # Запускаем бота
        print("🤖 Бот запущен и готов к работе!")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        bot = TotalizerBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")