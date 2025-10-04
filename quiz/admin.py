from django.contrib import admin
from .models import Quiz, Question, Answer, QuizSession, Participant, UserAnswer


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'created_at', 'is_active', 'code']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['code', 'created_at']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'quiz', 'question_type', 'order']
    list_filter = ['question_type', 'quiz']
    search_fields = ['question_text']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['answer_text', 'question', 'is_correct']
    list_filter = ['is_correct', 'question__quiz']


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'session_code', 'is_active', 'started_at']
    list_filter = ['is_active', 'started_at']


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['nickname', 'session', 'score', 'joined_at']
    list_filter = ['session', 'joined_at']


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['participant', 'question', 'answer', 'is_correct', 'answered_at']
    list_filter = ['is_correct', 'answered_at']
