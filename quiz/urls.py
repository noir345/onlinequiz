from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.home, name='home'),
    path('quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('create/', views.create_quiz, name='create_quiz'),
    path('quiz/<int:quiz_id>/add-questions/', views.add_questions, name='add_questions'),
    path('quiz/<int:quiz_id>/start/', views.start_quiz_session, name='start_quiz_session'),
    path('join/', views.join_quiz, name='join_quiz'),
    path('session/<str:session_code>/', views.quiz_session, name='quiz_session'),
    path('play/<str:session_code>/', views.play_quiz, name='play_quiz'),
    path('results/<str:session_code>/', views.quiz_results, name='quiz_results'),
    path('my-quizzes/', views.my_quizzes, name='my_quizzes'),
    path('quiz/<int:quiz_id>/edit/', views.edit_quiz, name='edit_quiz'),
    path('quiz/<int:quiz_id>/delete/', views.delete_quiz, name='delete_quiz'),
    path('api/next-question/<str:session_code>/', views.next_question, name='next_question'),
]