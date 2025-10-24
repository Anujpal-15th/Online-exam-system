from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django.db.models import Count, Sum, Avg
from questions.models import Question, Submission

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST.get('email', '').strip()
        password = request.POST['password']
        user_type = request.POST['user_type']
        user = CustomUser.objects.create_user(username=username, password=password, user_type=user_type)
        if email:
            user.email = email
            user.save(update_fields=['email'])
        return redirect('login')
    return render(request, 'authentication/register.html')

def login_view(request):
    if request.method == 'POST':
        identifier = request.POST['username']
        password = request.POST['password']
        role = request.POST.get('role')
        # Try username first, then email fallback
        user = authenticate(request, username=identifier, password=password)
        if not user:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                u = User.objects.filter(email=identifier).first()
                if u:
                    user = authenticate(request, username=u.username, password=password)
            except Exception:
                user = None
        if user:
            # Validate selected role if provided
            if role == 'admin' and user.user_type != 1:
                return render(request, 'authentication/login.html', { 'error': 'Not an admin account.' })
            if role == 'teacher' and user.user_type != 2:
                return render(request, 'authentication/login.html', { 'error': 'Not a teacher account.' })
            if role == 'student' and user.user_type != 3:
                return render(request, 'authentication/login.html', { 'error': 'Not a student account.' })

            login(request, user)
            if user.user_type == 1:
                return redirect('admin_dashboard')
            elif user.user_type == 2:
                return redirect('teacher_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            return render(request, 'authentication/login.html', { 'error': 'Invalid credentials.' })
    return render(request, 'authentication/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def student_dashboard(request):
    # Show all available questions to students directly on their dashboard
    questions = Question.objects.all().order_by('-created_at')
    return render(request, 'dashboards/student_dashboard.html', { 'questions': questions })


@login_required
def teacher_dashboard(request):
    # Show latest submissions snapshot to teachers
    latest_submissions = Submission.objects.select_related('student', 'question').order_by('-submitted_at')[:10]
    return render(request, 'dashboards/teacher_dashboard.html', { 'latest_submissions': latest_submissions })


@login_required
def admin_dashboard(request):
    return render(request, 'dashboards/admin_dashboard.html')


# Admin utilities
@login_required
def admin_users(request):
    if request.user.user_type != 1:
        return redirect('home')
    users = CustomUser.objects.all().order_by('username')
    return render(request, 'authentication/admin_users.html', { 'users': users })


@login_required
def admin_create_user(request):
    if request.user.user_type != 1:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST.get('email', '').strip()
        user_type = int(request.POST.get('user_type', 3))
        u = CustomUser.objects.create_user(username=username, password=password, user_type=user_type)
        if email:
            u.email = email
            u.save(update_fields=['email'])
        return redirect('admin_users')
    return render(request, 'authentication/admin_create_user.html')


@login_required
def admin_delete_user(request, id):
    if request.user.user_type != 1:
        return redirect('home')
    if request.method == 'POST':
        try:
            u = CustomUser.objects.get(id=id)
            if u.id != request.user.id:
                u.delete()
        except CustomUser.DoesNotExist:
            pass
        return redirect('admin_users')
    return redirect('admin_users')


@login_required
def admin_activity(request):
    if request.user.user_type != 1:
        return redirect('home')
    questions_count = Question.objects.count()
    submissions_count = Submission.objects.count()
    created_by_teacher = Question.objects.values('author__username').annotate(cnt=Count('id')).order_by('-cnt')
    submissions_by_student = Submission.objects.values('student__username').annotate(
        cnt=Count('id'), total=Sum('score'), avg=Avg('score')
    ).order_by('-cnt')
    return render(request, 'authentication/admin_activity.html', {
        'questions_count': questions_count,
        'submissions_count': submissions_count,
        'created_by_teacher': created_by_teacher,
        'submissions_by_student': submissions_by_student,
    })


# Teacher performance report
@login_required
def teacher_reports(request):
    if request.user.user_type != 2:
        return redirect('home')
    by_student = Submission.objects.values('student__username').annotate(
        attempts=Count('id'), total=Sum('score'), avg=Avg('score')
    ).order_by('-total')
    by_question = Submission.objects.values('question_id').annotate(
        attempts=Count('id'), avg=Avg('score')
    ).order_by('-attempts')
    return render(request, 'authentication/teacher_reports.html', {
        'by_student': by_student,
        'by_question': by_question,
    })
