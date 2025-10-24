from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.http import HttpResponse
import csv
from .models import Question, Submission

def questions_list(request):
    qs = Question.objects.all()
    subject = request.GET.get('subject')
    topic = request.GET.get('topic')
    difficulty = request.GET.get('difficulty')
    search = request.GET.get('q')

    if subject:
        qs = qs.filter(subject__iexact=subject)
    if topic:
        qs = qs.filter(topic__iexact=topic)
    if difficulty:
        qs = qs.filter(difficulty=difficulty)
    if search:
        qs = qs.filter(question_text__icontains=search)

    return render(request, 'questions/questions_list.html', {'questions': qs})

@login_required
def add_question(request):
    if request.user.user_type != 2:  # only teachers
        return redirect('questions_list')
    if request.method == 'POST':
        text = request.POST['question_text']
        subject = request.POST.get('subject', '').strip()
        topic = request.POST.get('topic', '').strip()
        difficulty = request.POST.get('difficulty', 'easy')
        Question.objects.create(
            question_text=text,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            author=request.user,
        )
        return redirect('questions_list')
    return render(request, 'questions/add_question.html')

@login_required
def edit_question(request, id):
    if request.user.user_type != 2 and request.user.user_type != 1:
        return redirect('questions_list')
    question = get_object_or_404(Question, id=id)
    if request.method == 'POST':
        question.question_text = request.POST['question_text']
        question.subject = request.POST.get('subject', '').strip()
        question.topic = request.POST.get('topic', '').strip()
        question.difficulty = request.POST.get('difficulty', question.difficulty)
        question.save()
        return redirect('questions_list')
    return render(request, 'questions/edit_question.html', {'question': question})

@login_required
def delete_question(request, id):
    if request.user.user_type != 2 and request.user.user_type != 1:
        return redirect('questions_list')
    question = get_object_or_404(Question, id=id)
    question.delete()
    return redirect('questions_list')


@login_required
def take_question(request, id):
    question = get_object_or_404(Question, id=id)
    if request.method == 'POST':
        answer = request.POST['answer_text']
        Submission.objects.create(question=question, student=request.user, answer_text=answer)
        return redirect('questions_list')
    return render(request, 'questions/take_question.html', {'question': question})


@login_required
def submissions_list(request):
    if request.user.user_type != 2:
        return redirect('questions_list')
    submissions = Submission.objects.select_related('question', 'student').order_by('-submitted_at')
    return render(request, 'questions/submissions_list.html', {'submissions': submissions})


@login_required
def grade_submission(request, id):
    if request.user.user_type != 2:
        return redirect('questions_list')
    sub = get_object_or_404(Submission, id=id)
    if request.method == 'POST':
        sub.graded = True
        sub.score = int(request.POST.get('score', 0))
        sub.feedback = request.POST.get('feedback', '')
        sub.save()
        return redirect('submissions_list')
    return render(request, 'questions/grade_submission.html', {'submission': sub})


@login_required
def leaderboard(request):
    # Top students by total score
    agg = Submission.objects.filter(graded=True).values('student__username').annotate(
        total_score=Sum('score'), count=Count('id'), avg=Avg('score')
    ).order_by('-total_score')[:20]
    return render(request, 'questions/leaderboard.html', {'rows': agg})


@login_required
def export_performance_csv(request):
    if request.user.user_type != 2:
        return redirect('questions_list')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="performance.csv"'
    writer = csv.writer(response)
    writer.writerow(['Student', 'Question ID', 'Score', 'Graded', 'Submitted At'])
    for s in Submission.objects.select_related('student', 'question').all():
        writer.writerow([s.student.username, s.question_id, s.score or 0, s.graded, s.submitted_at])
    return response


@login_required
def student_submissions(request):
    subs = Submission.objects.select_related('question').filter(student=request.user).order_by('-submitted_at')
    return render(request, 'questions/student_submissions.html', {'submissions': subs})


@login_required
def mock_test(request):
    # Simple random 5 questions mock
    import random
    all_ids = list(Question.objects.values_list('id', flat=True))
    random.shuffle(all_ids)
    selected = Question.objects.filter(id__in=all_ids[:5])
    return render(request, 'questions/mock_test.html', {'questions': selected})
