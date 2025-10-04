from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Quiz(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название викторины")
    description = models.TextField(verbose_name="Описание")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создатель")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    time_per_question = models.IntegerField(default=30, verbose_name="Время на вопрос (секунды)")
    code = models.CharField(max_length=10, unique=True, verbose_name="Код викторины")
    
    class Meta:
        verbose_name = "Викторина"
        verbose_name_plural = "Викторины"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPES = [
        ('text', 'Текстовый'),
        ('image', 'С изображением'),
        ('video', 'С видео'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', verbose_name="Викторина")
    question_text = models.TextField(verbose_name="Текст вопроса")
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='text', verbose_name="Тип вопроса")
    image = models.ImageField(upload_to='questions/', blank=True, null=True, verbose_name="Изображение")
    video_url = models.URLField(blank=True, null=True, verbose_name="URL видео")
    order = models.IntegerField(verbose_name="Порядок")
    
    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Вопрос {self.order}"


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers', verbose_name="Вопрос")
    answer_text = models.CharField(max_length=500, verbose_name="Текст ответа")
    is_correct = models.BooleanField(default=False, verbose_name="Правильный ответ")
    
    class Meta:
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"
    
    def __str__(self):
        return f"{self.question} - {self.answer_text}"


class QuizSession(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, verbose_name="Викторина")
    session_code = models.CharField(max_length=20, unique=True, verbose_name="Код сессии")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    current_question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Текущий вопрос")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Начата")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Завершена")
    
    class Meta:
        verbose_name = "Сессия викторины"
        verbose_name_plural = "Сессии викторин"
    
    def __str__(self):
        return f"{self.quiz.title} - {self.session_code}"


class Participant(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='participants', verbose_name="Сессия")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Пользователь")
    nickname = models.CharField(max_length=100, verbose_name="Никнейм")
    score = models.IntegerField(default=0, verbose_name="Счет")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="Присоединился")
    
    class Meta:
        verbose_name = "Участник"
        verbose_name_plural = "Участники"
        unique_together = ['session', 'nickname']
    
    def __str__(self):
        return f"{self.nickname} - {self.session}"


class UserAnswer(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, verbose_name="Участник")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Вопрос")
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, verbose_name="Ответ")
    answered_at = models.DateTimeField(auto_now_add=True, verbose_name="Время ответа")
    is_correct = models.BooleanField(verbose_name="Правильный ответ")
    
    class Meta:
        verbose_name = "Ответ пользователя"
        verbose_name_plural = "Ответы пользователей"
        unique_together = ['participant', 'question']
    
    def __str__(self):
        return f"{self.participant.nickname} - {self.question}"


