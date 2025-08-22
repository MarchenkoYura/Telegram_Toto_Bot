import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class DataManager:
    """Класс для управления данными в JSON файлах"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.events_file = os.path.join(data_dir, "events.json")
        self.bets_file = os.path.join(data_dir, "bets.json")
        self.proposals_file = os.path.join(data_dir, "proposals.json")
        
        # Создаем папку data если её нет
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Инициализируем файлы если их нет
        self._init_files()
    
    def _init_files(self):
        """Инициализация файлов данных"""
        if not os.path.exists(self.users_file):
            self._save_json(self.users_file, {})
        
        if not os.path.exists(self.events_file):
            self._save_json(self.events_file, {})
        
        if not os.path.exists(self.bets_file):
            self._save_json(self.bets_file, {})
            
        if not os.path.exists(self.proposals_file):
            self._save_json(self.proposals_file, {})
    
    def _load_json(self, file_path: str) -> dict:
        """Загрузка данных из JSON файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_json(self, file_path: str, data: dict):
        """Сохранение данных в JSON файл"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_next_id(self, data: dict) -> int:
        """Получение следующего ID"""
        if not data:
            return 1
        return max([int(k) for k in data.keys()]) + 1
    
    # ========== ПОЛЬЗОВАТЕЛИ ==========
    
    def get_user(self, telegram_id: int) -> Optional[dict]:
        """Получить пользователя по Telegram ID"""
        users = self._load_json(self.users_file)
        for user_data in users.values():
            if user_data.get('telegram_id') == telegram_id:
                return user_data
        return None
    
    def create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> dict:
        """Создать нового пользователя"""
        users = self._load_json(self.users_file)
        user_id = self._get_next_id(users)
        
        user_data = {
            'id': user_id,
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'balance': 1000.0,
            'created_at': datetime.now().isoformat()
        }
        
        users[str(user_id)] = user_data
        self._save_json(self.users_file, users)
        return user_data
    
    def update_user_balance(self, telegram_id: int, new_balance: float) -> bool:
        """Обновить баланс пользователя"""
        users = self._load_json(self.users_file)
        
        for user_id, user_data in users.items():
            if user_data.get('telegram_id') == telegram_id:
                user_data['balance'] = new_balance
                self._save_json(self.users_file, users)
                return True
        return False
    
    def add_balance(self, telegram_id: int, amount: float) -> bool:
        """Добавить к балансу пользователя"""
        user = self.get_user(telegram_id)
        if user:
            new_balance = user['balance'] + amount
            return self.update_user_balance(telegram_id, new_balance)
        return False
    
    # ========== СОБЫТИЯ ==========
    
    def create_event(self, title: str, option1: str, option2: str, odds1: float = 2.0, odds2: float = 2.0, description: str = None, image_url: str = None, image_file_id: str = None) -> dict:
        """Создать новое событие"""
        events = self._load_json(self.events_file)
        event_id = self._get_next_id(events)
        
        event_data = {
            'id': event_id,
            'title': title,
            'description': description,
            'option1': option1,
            'option2': option2,
            'odds1': odds1,
            'odds2': odds2,
            'image_url': image_url,
            'image_file_id': image_file_id,
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'closed_at': None,
            'result': None
        }
        
        events[str(event_id)] = event_data
        self._save_json(self.events_file, events)
        return event_data
    
    def get_event(self, event_id: int) -> Optional[dict]:
        """Получить событие по ID"""
        events = self._load_json(self.events_file)
        return events.get(str(event_id))
    
    def get_active_events(self) -> List[dict]:
        """Получить все активные события"""
        events = self._load_json(self.events_file)
        return [event for event in events.values() if event.get('is_active', False)]
    
    def close_event(self, event_id: int, result: int) -> bool:
        """Закрыть событие с результатом (1 или 2)"""
        events = self._load_json(self.events_file)
        
        if str(event_id) in events:
            event = events[str(event_id)]
            event['is_active'] = False
            event['result'] = result
            event['closed_at'] = datetime.now().isoformat()
            
            self._save_json(self.events_file, events)
            return True
        return False
    
    # ========== СТАВКИ ==========
    
    def create_bet(self, telegram_id: int, event_id: int, amount: float, option: int, odds: float) -> dict:
        """Создать новую ставку"""
        user = self.get_user(telegram_id)
        if not user:
            raise ValueError("Пользователь не найден")
        
        if user['balance'] < amount:
            raise ValueError("Недостаточно средств")
        
        event = self.get_event(event_id)
        if not event or not event.get('is_active'):
            raise ValueError("Событие не активно")
        
        bets = self._load_json(self.bets_file)
        bet_id = self._get_next_id(bets)
        
        bet_data = {
            'id': bet_id,
            'user_id': user['id'],
            'telegram_id': telegram_id,
            'event_id': event_id,
            'amount': amount,
            'option': option,
            'odds': odds,
            'created_at': datetime.now().isoformat(),
            'is_won': None
        }
        
        bets[str(bet_id)] = bet_data
        self._save_json(self.bets_file, bets)
        
        # Списываем средства с баланса
        self.update_user_balance(telegram_id, user['balance'] - amount)
        
        return bet_data
    
    def get_user_bets(self, telegram_id: int, limit: int = 10) -> List[dict]:
        """Получить ставки пользователя"""
        bets = self._load_json(self.bets_file)
        user_bets = [bet for bet in bets.values() if bet.get('telegram_id') == telegram_id]
        
        # Сортируем по дате создания (новые сначала)
        user_bets.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return user_bets[:limit]
    
    def get_event_bets(self, event_id: int) -> List[dict]:
        """Получить все ставки на событие"""
        bets = self._load_json(self.bets_file)
        return [bet for bet in bets.values() if bet.get('event_id') == event_id]
    
    def process_event_results(self, event_id: int, winning_option: int) -> dict:
        """Обработать результаты события и выплатить выигрыши"""
        event_bets = self.get_event_bets(event_id)
        stats = {
            'total_bets': len(event_bets),
            'winners': 0,
            'total_payouts': 0
        }
        
        bets = self._load_json(self.bets_file)
        
        for bet in event_bets:
            bet_id = str(bet['id'])
            if bet['option'] == winning_option:
                # Выигрышная ставка
                bets[bet_id]['is_won'] = True
                payout = bet['amount'] * bet['odds']
                self.add_balance(bet['telegram_id'], payout)
                stats['winners'] += 1
                stats['total_payouts'] += payout
            else:
                # Проигрышная ставка
                bets[bet_id]['is_won'] = False
        
        self._save_json(self.bets_file, bets)
        return stats
    
    def get_active_bets_count(self, telegram_id: int) -> int:
        """Получить количество активных ставок пользователя"""
        bets = self._load_json(self.bets_file)
        events = self._load_json(self.events_file)
        
        count = 0
        for bet in bets.values():
            if (bet.get('telegram_id') == telegram_id and 
                bet.get('event_id') and
                str(bet['event_id']) in events and
                events[str(bet['event_id'])].get('is_active')):
                count += 1
        
        return count
    
    # ========== ПРЕДЛОЖЕНИЯ СОБЫТИЙ ==========
    
    def create_proposal(self, telegram_id: int, title: str, option1: str, option2: str, description: str = None, image_file_id: str = None) -> dict:
        """Создать предложение события от пользователя"""
        proposals = self._load_json(self.proposals_file)
        proposal_id = self._get_next_id(proposals)
        
        user = self.get_user(telegram_id)
        
        proposal_data = {
            'id': proposal_id,
            'user_id': user['id'] if user else None,
            'telegram_id': telegram_id,
            'username': user['username'] if user else None,
            'first_name': user['first_name'] if user else None,
            'title': title,
            'description': description,
            'option1': option1,
            'option2': option2,
            'image_file_id': image_file_id,  # ID картинки от пользователя
            'status': 'pending',  # pending, approved, rejected
            'created_at': datetime.now().isoformat(),
            'reviewed_at': None,
            'event_id': None  # ID созданного события, если одобрено
        }
        
        proposals[str(proposal_id)] = proposal_data
        self._save_json(self.proposals_file, proposals)
        return proposal_data
    
    def get_proposal(self, proposal_id: int) -> Optional[dict]:
        """Получить предложение по ID"""
        proposals = self._load_json(self.proposals_file)
        return proposals.get(str(proposal_id))
    
    def get_pending_proposals(self) -> List[dict]:
        """Получить все ожидающие рассмотрения предложения"""
        proposals = self._load_json(self.proposals_file)
        pending = [p for p in proposals.values() if p.get('status') == 'pending']
        
        # Сортируем по дате создания (новые первыми)
        pending.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return pending
    
    def get_user_proposals(self, telegram_id: int, limit: int = 10) -> List[dict]:
        """Получить предложения пользователя"""
        proposals = self._load_json(self.proposals_file)
        user_proposals = [p for p in proposals.values() if p.get('telegram_id') == telegram_id]
        
        # Сортируем по дате создания (новые первыми)
        user_proposals.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return user_proposals[:limit]
    
    def approve_proposal(self, proposal_id: int, odds1: float = 2.0, odds2: float = 2.0) -> dict:
        """Одобрить предложение и создать событие"""
        proposals = self._load_json(self.proposals_file)
        
        if str(proposal_id) not in proposals:
            raise ValueError("Предложение не найдено")
        
        proposal = proposals[str(proposal_id)]
        
        if proposal['status'] != 'pending':
            raise ValueError("Предложение уже рассмотрено")
        
        # Создаем событие
        event = self.create_event(
            title=proposal['title'],
            option1=proposal['option1'],
            option2=proposal['option2'],
            odds1=odds1,
            odds2=odds2,
            description=proposal['description'],
            image_file_id=proposal.get('image_file_id')
        )
        
        # Обновляем статус предложения
        proposal['status'] = 'approved'
        proposal['reviewed_at'] = datetime.now().isoformat()
        proposal['event_id'] = event['id']
        
        proposals[str(proposal_id)] = proposal
        self._save_json(self.proposals_file, proposals)
        
        return {
            'proposal': proposal,
            'event': event
        }
    
    def reject_proposal(self, proposal_id: int, reason: str = None) -> bool:
        """Отклонить предложение"""
        proposals = self._load_json(self.proposals_file)
        
        if str(proposal_id) not in proposals:
            return False
        
        proposal = proposals[str(proposal_id)]
        
        if proposal['status'] != 'pending':
            return False
        
        proposal['status'] = 'rejected'
        proposal['reviewed_at'] = datetime.now().isoformat()
        if reason:
            proposal['rejection_reason'] = reason
        
        proposals[str(proposal_id)] = proposal
        self._save_json(self.proposals_file, proposals)
        
        return True
