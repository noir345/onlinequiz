import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import QuizSession, Participant, UserAnswer


class QuizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_code = self.scope['url_route']['kwargs']['session_code']
        self.room_group_name = f'quiz_{self.session_code}'
        
        # Проверяем существование сессии
        session = await self.get_session()
        if not session:
            await self.close()
            return
        
        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем информацию о сессии
        await self.send(text_data=json.dumps({
            'type': 'session_info',
            'session_code': self.session_code,
            'quiz_title': session.quiz.title,
            'current_question': await self.get_current_question_info()
        }))
    
    async def disconnect(self, close_code):
        # Покидаем группу
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'join_quiz':
            await self.handle_join_quiz(data)
        elif message_type == 'submit_answer':
            await self.handle_submit_answer(data)
        elif message_type == 'next_question':
            await self.handle_next_question()
        elif message_type == 'end_quiz':
            await self.handle_end_quiz()
    
    async def handle_join_quiz(self, data):
        """Обработка присоединения к викторине"""
        nickname = data.get('nickname')
        user_id = data.get('user_id')
        
        participant = await self.create_participant(nickname, user_id)
        
        if participant:
            # Отправляем обновленную информацию об участниках
            participants = await self.get_participants()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'participants_update',
                    'participants': participants
                }
            )
    
    async def handle_submit_answer(self, data):
        """Обработка ответа пользователя"""
        participant_id = data.get('participant_id')
        answer_id = data.get('answer_id')
        
        result = await self.process_answer(participant_id, answer_id)
        
        if result:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'answer_result',
                    'participant_id': participant_id,
                    'is_correct': result['is_correct'],
                    'score': result['score']
                }
            )
    
    async def handle_next_question(self):
        """Переход к следующему вопросу"""
        next_question = await self.get_next_question()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'next_question',
                'question': next_question
            }
        )
    
    async def handle_end_quiz(self):
        """Завершение викторины"""
        results = await self.get_quiz_results()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'quiz_ended',
                'results': results
            }
        )
    
    async def participants_update(self, event):
        """Отправка обновления списка участников"""
        await self.send(text_data=json.dumps({
            'type': 'participants_update',
            'participants': event['participants']
        }))
    
    async def answer_result(self, event):
        """Отправка результата ответа"""
        await self.send(text_data=json.dumps({
            'type': 'answer_result',
            'participant_id': event['participant_id'],
            'is_correct': event['is_correct'],
            'score': event['score']
        }))
    
    async def next_question(self, event):
        """Отправка следующего вопроса"""
        await self.send(text_data=json.dumps({
            'type': 'next_question',
            'question': event['question']
        }))
    
    async def quiz_ended(self, event):
        """Отправка результатов викторины"""
        await self.send(text_data=json.dumps({
            'type': 'quiz_ended',
            'results': event['results']
        }))
    
    @database_sync_to_async
    def get_session(self):
        try:
            return QuizSession.objects.get(session_code=self.session_code, is_active=True)
        except QuizSession.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_current_question_info(self):
        session = QuizSession.objects.get(session_code=self.session_code)
        if session.current_question:
            question = session.current_question
            answers = list(question.answers.values('id', 'answer_text'))
            return {
                'id': question.id,
                'text': question.question_text,
                'type': question.question_type,
                'image': question.image.url if question.image else None,
                'video_url': question.video_url,
                'answers': answers,
                'time_limit': session.quiz.time_per_question
            }
        return None
    
    @database_sync_to_async
    def create_participant(self, nickname, user_id):
        try:
            session = QuizSession.objects.get(session_code=self.session_code)
            user = None
            if user_id:
                from django.contrib.auth.models import User
                user = User.objects.get(id=user_id)
            
            participant = Participant.objects.create(
                session=session,
                user=user,
                nickname=nickname
            )
            return participant
        except Exception:
            return None
    
    @database_sync_to_async
    def get_participants(self):
        session = QuizSession.objects.get(session_code=self.session_code)
        return list(session.participants.values('id', 'nickname', 'score'))
    
    @database_sync_to_async
    def process_answer(self, participant_id, answer_id):
        try:
            participant = Participant.objects.get(id=participant_id)
            answer = Answer.objects.get(id=answer_id)
            
            # Проверяем, не отвечал ли уже
            if UserAnswer.objects.filter(participant=participant, question=answer.question).exists():
                return None
            
            # Создаем запись об ответе
            UserAnswer.objects.create(
                participant=participant,
                question=answer.question,
                answer=answer,
                is_correct=answer.is_correct
            )
            
            # Обновляем счет
            if answer.is_correct:
                participant.score += 1
                participant.save()
            
            return {
                'is_correct': answer.is_correct,
                'score': participant.score
            }
        except Exception:
            return None
    
    @database_sync_to_async
    def get_next_question(self):
        session = QuizSession.objects.get(session_code=self.session_code)
        questions = list(session.quiz.questions.all().order_by('order'))
        
        if not questions:
            return None
        
        current_order = session.current_question.order if session.current_question else 0
        next_question = None
        
        for question in questions:
            if question.order > current_order:
                next_question = question
                break
        
        if next_question:
            session.current_question = next_question
            session.save()
            
            answers = list(next_question.answers.values('id', 'answer_text'))
            return {
                'id': next_question.id,
                'text': next_question.question_text,
                'type': next_question.question_type,
                'image': next_question.image.url if next_question.image else None,
                'video_url': next_question.video_url,
                'answers': answers,
                'time_limit': session.quiz.time_per_question
            }
        
        return None
    
    @database_sync_to_async
    def get_quiz_results(self):
        session = QuizSession.objects.get(session_code=self.session_code)
        participants = list(session.participants.all().order_by('-score').values(
            'id', 'nickname', 'score'
        ))
        
        session.is_active = False
        session.save()
        
        return participants
