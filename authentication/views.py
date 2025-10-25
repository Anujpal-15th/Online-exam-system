from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django.db.models import Count, Sum, Avg
from questions.models import Question, Submission
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings

def _send_verification_email(user, request):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(
        reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    )
    subject = 'Verify your email - Online Exam System'
    message = (
        f"Hi {user.username},\n\n"
        f"Thanks for registering at Online Exam System. Please verify your email by clicking the link below:\n"
        f"{verify_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    if user.email:
        send_mail(subject, message, from_email, [user.email], fail_silently=True)


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user_type = request.POST.get('user_type')
        
        # Validation
        if not username:
            return render(request, 'authentication/register.html', {'error': 'Username is required.'})
        if not email:
            return render(request, 'authentication/register.html', {'error': 'Email is required for verification.'})
        if not password:
            return render(request, 'authentication/register.html', {'error': 'Password is required.'})
        if not user_type:
            return render(request, 'authentication/register.html', {'error': 'Please select a role.'})
            
        # Check for existing username
        if CustomUser.objects.filter(username=username).exists():
            return render(request, 'authentication/register.html', {'error': 'Username already exists.'})
            
        # Check for existing email
        if CustomUser.objects.filter(email=email).exists():
            return render(request, 'authentication/register.html', {'error': 'Email already registered.'})
        
        try:
            # Create inactive user until email verified
            user = CustomUser.objects.create_user(
                username=username, 
                email=email,
                password=password, 
                user_type=user_type,
                is_active=False
            )

            # Send verification email
            _send_verification_email(user, request)
            return render(request, 'authentication/register_done.html', {'email': email})
            
        except Exception as e:
            return render(request, 'authentication/register.html', {'error': f'Registration failed: {str(e)}'})
            
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
            # Block login until email verified
            if not user.is_active:
                return render(request, 'authentication/login.html', { 'error': 'Please verify your email first. Check your inbox or resend verification.', 'show_resend': True, 'pending_user': user.username })
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
def dashboard_home(request):
    # logic to redirect based on user type
    if request.user.is_authenticated:
        if request.user.user_type == 1:  # admin
            return redirect('admin_dashboard')
        elif request.user.user_type == 2:  # teacher
            return redirect('teacher_dashboard')
        else:  # student
            return redirect('student_dashboard')
    else:
        return redirect('login')


def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        return render(request, 'authentication/verify_email_success.html')
    else:
        return render(request, 'authentication/verify_email_failed.html')


def resend_verification(request):
    if request.method == 'POST':
        identifier = request.POST.get('username_or_email', '').strip()
        user = None
        if identifier:
            try:
                user = CustomUser.objects.filter(username=identifier).first()
                if not user:
                    user = CustomUser.objects.filter(email=identifier).first()
            except Exception:
                user = None
        if user and not user.is_active:
            try:
                _send_verification_email(user, request)
            except Exception:
                pass
        return render(request, 'authentication/resend_verification_sent.html')
    # Fallback form
    return render(request, 'authentication/resend_verification_form.html')