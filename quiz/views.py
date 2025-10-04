import random
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Quiz, Question, Answer, QuizSession, Participant, UserAnswer
from .forms import QuizForm, QuestionForm, AnswerFormSet, JoinQuizForm


def home(request):
    popular_quizzes = Quiz.objects.filter(is_active=True).order_by('-created_at')[:6]
    recent_quizzes = Quiz.objects.filter(is_active=True).order_by('-created_at')[:6]
    
    context = {
        'popular_quizzes': popular_quizzes,
        'recent_quizzes': recent_quizzes,
    }
    return render(request, 'quiz/home.html', context)


def quiz_list(request):
    quizzes = Quiz.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'quiz/quiz_list.html', {'quizzes': quizzes})


def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    return render(request, 'quiz/quiz_detail.html', {'quiz': quiz})


@login_required
def create_quiz(request):
    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.creator = request.user
            quiz.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            quiz.save()
            messages.success(request, f'Викторина создана! Код: {quiz.code}')
            return redirect('quiz:add_questions', quiz_id=quiz.id)
    else:
        form = QuizForm()
    return render(request, 'quiz/create_quiz.html', {'form': form})


@login_required
def add_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, creator=request.user)
    
    if request.method == 'POST':
        question_form = QuestionForm(request.POST, request.FILES)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.quiz = quiz
            question.save()
            
            formset = AnswerFormSet(request.POST, instance=question)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Вопрос добавлен!')
                return redirect('quiz:add_questions', quiz_id=quiz.id)
    else:
        question_form = QuestionForm()
        formset = AnswerFormSet()
    
    questions = quiz.questions.all()
    return render(request, 'quiz/add_questions.html', {
        'quiz': quiz,
        'question_form': question_form,
        'formset': formset,
        'questions': questions
    })


@login_required
def start_quiz_session(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, creator=request.user)
    
    if not quiz.questions.exists():
        messages.error(request, 'Добавьте вопросы в викторину!')
        return redirect('quiz:add_questions', quiz_id=quiz.id)
    
    session_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    session = QuizSession.objects.create(
        quiz=quiz,
        session_code=session_code,
        current_question=quiz.questions.order_by('order').first()
    )
    
    return redirect('quiz:quiz_session', session_code=session_code)


def join_quiz(request):
    if request.method == 'POST':
        form = JoinQuizForm(request.POST)
        if form.is_valid():
            session_code = form.cleaned_data['session_code']
            nickname = form.cleaned_data['nickname']
            
            try:
                # Отладочная информация
                print(f"Поиск сессии с кодом: {session_code}")
                all_sessions = QuizSession.objects.all()
                print(f"Всего сессий в базе: {all_sessions.count()}")
                for s in all_sessions:
                    print(f"Сессия: {s.session_code}, активна: {s.is_active}")
                
                session = QuizSession.objects.get(session_code=session_code, is_active=True)
                
                if session.participants.filter(nickname=nickname).exists():
                    messages.error(request, 'Нікнейм вже зайнятий!')
                    return render(request, 'quiz/join_quiz.html', {'form': form})
                
                participant = Participant.objects.create(
                    session=session,
                    user=request.user if request.user.is_authenticated else None,
                    nickname=nickname
                )
                
                request.session['participant_id'] = participant.id
                request.session['session_code'] = session_code
                
                return redirect('quiz:play_quiz', session_code=session_code)
                
            except QuizSession.DoesNotExist:
                messages.error(request, 'Сесію не знайдено або вона завершена!')
    else:
        form = JoinQuizForm()
    
    return render(request, 'quiz/join_quiz.html', {'form': form})


def quiz_session(request, session_code):
    session = get_object_or_404(QuizSession, session_code=session_code)
    participants = session.participants.all()
    
    return render(request, 'quiz/quiz_session.html', {
        'session': session,
        'participants': participants
    })


def play_quiz(request, session_code):
    session = get_object_or_404(QuizSession, session_code=session_code, is_active=True)
    
    participant_id = request.session.get('participant_id')
    if not participant_id:
        return redirect('quiz:join_quiz')
    
    try:
        participant = Participant.objects.get(id=participant_id, session=session)
    except Participant.DoesNotExist:
        return redirect('quiz:join_quiz')
    
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        answer_id = request.POST.get('answer_id')
        
        if question_id and answer_id:
            question = get_object_or_404(Question, id=question_id)
            answer = get_object_or_404(Answer, id=answer_id)
            
            if not UserAnswer.objects.filter(participant=participant, question=question).exists():
                user_answer = UserAnswer.objects.create(
                    participant=participant,
                    question=question,
                    answer=answer,
                    is_correct=answer.is_correct
                )
                
                if answer.is_correct:
                    participant.score += 1
                    participant.save()
                
                # Переходим к следующему вопросу
                next_question = session.quiz.questions.filter(order__gt=question.order).order_by('order').first()
                if next_question:
                    session.current_question = next_question
                    session.save()
                else:
                    # Викторина завершена
                    session.is_active = False
                    session.save()
                    return redirect('quiz:quiz_results', session_code=session_code)
    
    current_question = session.current_question
    if not current_question:
        return redirect('quiz:quiz_results', session_code=session_code)
    
    answers = current_question.answers.all()
    
    return render(request, 'quiz/play_quiz.html', {
        'session': session,
        'participant': participant,
        'current_question': current_question,
        'answers': answers
    })


def quiz_results(request, session_code):
    session = get_object_or_404(QuizSession, session_code=session_code)
    participants = session.participants.all().order_by('-score')
    
    participant_id = request.session.get('participant_id')
    current_participant = None
    if participant_id:
        try:
            current_participant = Participant.objects.get(id=participant_id, session=session)
        except Participant.DoesNotExist:
            pass
    
    return render(request, 'quiz/quiz_results.html', {
        'session': session,
        'participants': participants,
        'current_participant': current_participant
    })


@login_required
def my_quizzes(request):
    quizzes = Quiz.objects.filter(creator=request.user).order_by('-created_at')
    return render(request, 'quiz/my_quizzes.html', {'quizzes': quizzes})


@login_required
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, creator=request.user)
    
    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, 'Викторина обновлена!')
            return redirect('quiz:my_quizzes')
    else:
        form = QuizForm(instance=quiz)
    
    return render(request, 'quiz/edit_quiz.html', {'form': form, 'quiz': quiz})


@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, creator=request.user)
    
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, 'Викторина удалена!')
        return redirect('quiz:my_quizzes')
    
    return render(request, 'quiz/delete_quiz.html', {'quiz': quiz})


@csrf_exempt
def next_question(request, session_code):
    if request.method == 'POST':
        session = get_object_or_404(QuizSession, session_code=session_code)
        current_question = session.current_question
        
        if current_question:
            next_question = session.quiz.questions.filter(order__gt=current_question.order).first()
            session.current_question = next_question
            session.save()
            
            if not next_question:
                session.is_active = False
                session.ended_at = timezone.now()
                session.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})