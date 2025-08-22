"""
Обработчики callback'ов для Telegram бота
"""

from typing import Dict, Callable, Awaitable
from telegram import Update
from telegram.ext import ContextTypes


class CallbackHandler:
    """Класс для обработки callback'ов с использованием словаря обработчиков"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        
        # Словарь точных обработчиков (для конкретных callback'ов)
        self.exact_handlers: Dict[str, Callable] = {
            "event_with_photo": self.bot.start_event_with_photo,
            "event_without_photo": self.bot.start_event_without_photo,
            "cancel_event_creation": self.bot.cancel_event_creation,
            "cancel_proposal_creation": self.bot.cancel_proposal_creation,
            "proposal_with_photo": self.bot.start_proposal_with_photo,
            "proposal_without_photo": self.bot.start_proposal_without_photo,
            "skip_description": self.bot.skip_proposal_description,
            "back_to_events": self.bot.show_events_inline,
            "back_to_proposals": self.bot.show_proposals_inline,
            "back_to_admin": self.bot.back_to_admin_menu,
        }
        
        # Словарь префиксных обработчиков (для callback'ов начинающихся с определенного префикса)
        self.prefix_handlers: Dict[str, Callable] = {
            "odds_": self._handle_odds_selection,
            "custom_odds_": self._handle_custom_odds,
            "proposal_": self._handle_proposal_action,
            "event_": self._handle_event_details,
            "bet_": self._handle_make_bet,
        }
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Основной метод обработки callback'ов"""
        
        # Сначала проверяем точные совпадения
        if callback_data in self.exact_handlers:
            await self.exact_handlers[callback_data](update, context)
            return
        
        # Затем проверяем префиксы
        for prefix, handler in self.prefix_handlers.items():
            if callback_data.startswith(prefix):
                await handler(update, context, callback_data)
                return
        
        # Если ничего не найдено, логируем
        print(f"⚠️ Неизвестный callback: {callback_data}")
    
    async def _handle_odds_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка выбора коэффициентов"""
        await self.bot.handle_odds_selection(update, context, callback_data)
    
    async def _handle_custom_odds(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка пользовательских коэффициентов"""
        proposal_id = int(callback_data.split("_")[2])
        await self.bot.start_custom_odds_input(update, context, proposal_id)
    
    async def _handle_proposal_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка действий с предложениями"""
        await self.bot.handle_proposal_action(update, context, callback_data)
    
    async def _handle_event_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка показа деталей события"""
        await self.bot.show_event_details(update, context, callback_data)
    
    async def _handle_make_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка создания ставки"""
        await self.bot.make_bet(update, context, callback_data)


class TextHandler:
    """Класс для обработки текстовых сообщений с использованием словаря"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        
        # Словарь обработчиков текстовых команд (кнопок меню)
        self.menu_handlers: Dict[str, Callable] = {
            "🎲 События": self.bot.show_events,
            "💰 Баланс": self.bot.balance,
            "🎯 Мои ставки": self.bot.my_bets,
            "💡 Предложить событие": self.bot.start_proposal_creation,
            "ℹ️ Помощь": self.bot.help_command,
            "👑 Админ панель": self.bot.admin_menu_handler,
            "🆕 Создать событие": self.bot.start_event_creation,
            "🔒 Закрыть событие": self.bot.close_event_menu,
            "📋 Предложения": self.bot.show_proposals_menu,
            "💵 Добавить баланс": self.bot.add_balance_menu,
            "📊 Статистика": self.bot.show_stats,
            "◀️ Главное меню": self.bot.back_to_main_menu,
        }
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Основной метод обработки текстовых сообщений"""
        
        # Проверяем, есть ли активные состояния
        if context.user_data.get('betting_step') == 'waiting_amount':
            await self.bot.process_bet_amount(update, context, text)
            return
        
        if context.user_data.get('custom_odds_step'):
            await self.bot.process_custom_odds_input(update, context, text)
            return
        
        if context.user_data.get('creating_event') and update.effective_user.id == self.bot.config.ADMIN_ID:
            await self.bot.process_event_creation_step(update, context, text)
            return
        
        if context.user_data.get('creating_proposal'):
            await self.bot.process_proposal_creation_step(update, context, text)
            return
        
        # Обработка команд меню
        if text in self.menu_handlers:
            await self.menu_handlers[text](update, context)
        else:
            # Неизвестная команда
            await update.message.reply_text(
                "🤔 Я не понимаю эту команду.\n"
                "Используйте кнопки меню или /help для получения помощи."
            )
