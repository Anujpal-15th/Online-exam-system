from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib import messages
from .models import CustomUser
from .forms import LoginForm, RegistrationForm, AdminUserCreationForm
from django.db.models import Count, Sum, Avg
from questions.models import Question, Submission, Notification
from exams.models import Test, TestAttempt, TestAnswer
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string


def _send_verification_email(user, request):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(
        reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    )
    context = {
        'user': user,
        'verify_url': verify_url,
        'site_name': 'Online Exam System',
    }
    subject = render_to_string('accounts/verify_email_subject.txt', context).strip()
    text_body = render_to_string('accounts/verify_email_email.txt', context)
    html_body = render_to_string('accounts/verify_email_email.html', context)
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    if user.email:
        msg = EmailMultiAlternatives(subject, text_body, from_email, [user.email])
        msg.attach_alternative(html_body, "text/html")
        try:
            msg.send(fail_silently=True)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send verification email to {user.email}: {e}")


def register_view(request):
    """
    User registration with automatic validation via Django Forms.
    
    Now uses RegistrationForm for:
    - Automatic field validation
    - Email format checking
    - Password strength enforcement
    - Username/email uniqueness validation
    - CSRF protection
    """
    from students.models import StudentProfile
    from core.models import TeacherProfile
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                # Form handles user creation, password hashing, and name splitting
                user = form.save()
                user_type = form.cleaned_data['user_type']
                
                # Create role-specific profile
                if user_type == '3':  # Student
                    roll_number = request.POST.get('roll_number', '').strip()
                    course = request.POST.get('course', '').strip()
                    branch = request.POST.get('branch', '').strip()
                    year = request.POST.get('year', '').strip()
                    semester = request.POST.get('semester', '').strip()
                    
                    if not all([roll_number, course, branch, year, semester]):
                        user.delete()
                        form.add_error(None, 'All student fields are required.')
                        return render(request, 'accounts/register.html', {'form': form})
                    
                    if StudentProfile.objects.filter(roll_number=roll_number).exists():
                        user.delete()
                        form.add_error(None, 'Roll number already exists.')
                        return render(request, 'accounts/register.html', {'form': form})
                    
                    StudentProfile.objects.create(
                        user=user,
                        roll_number=roll_number,
                        course=course,
                        branch=branch,
                        year=int(year),
                        semester=int(semester)
                    )
                
                elif user_type == '2':  # Teacher
                    department = request.POST.get('department', '').strip()
                    specialization = request.POST.get('specialization', '').strip()
                    qualification = request.POST.get('qualification', '').strip()
                    experience_years = request.POST.get('experience_years', '0').strip()
                    
                    if not all([department, specialization]):
                        user.delete()
                        form.add_error(None, 'Department and specialization are required for teachers.')
                        return render(request, 'accounts/register.html', {'form': form})
                    
                    try:
                        exp_years = int(experience_years) if experience_years else 0
                    except ValueError:
                        exp_years = 0
                    
                    TeacherProfile.objects.create(
                        user=user,
                        department=department,
                        specialization=specialization,
                        qualification=qualification,
                        experience_years=exp_years,
                        approval_status='approved'
                    )
                
                # Send verification email
                _send_verification_email(user, request)
                
                # Send welcome email
                try:
                    from core.email_service import EmailService
                    email_service = EmailService()
                    email_service.send_welcome_email(user)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to send welcome email to {user.email}: {e}")
                
                return render(request, 'accounts/register_done.html', {'email': user.email})
                
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Registration error: {e}")
                if 'user' in locals() and user and user.pk:
                    user.delete()
                form.add_error(None, f'Registration failed: {str(e)}')
        
        # Form has errors - will be displayed in template
        return render(request, 'accounts/register.html', {'form': form})
    
    else:
        form = RegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    User login with automatic validation via Django Forms.
    
    Now uses LoginForm for:
    - Automatic field validation
    - CSRF protection
    - Remember me functionality
    - Safer data access (no crashes if fields missing)
    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        
        if form.is_valid():
            identifier = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            
            # Try authentication with username first
            user = authenticate(request, username=identifier, password=password)
            
            # If failed, try with email
            if not user:
                try:
                    user_obj = CustomUser.objects.filter(email=identifier).first()
                    if user_obj:
                        user = authenticate(request, username=user_obj.username, password=password)
                except Exception:
                    user = None
            
            if user:
                # Check if user is blocked
                if hasattr(user, 'is_blocked') and user.is_blocked:
                    return render(request, 'accounts/blocked_user.html', status=403)
                
                # Check if account is verified
                if not user.is_active:
                    form.add_error(None, 
                        'Your account is not verified. Please check your email for the verification link, '
                        'or register again to receive a new verification email.'
                    )
                    return render(request, 'accounts/login.html', {
                        'form': form,
                        'show_resend': True,
                        'pending_user': user.username
                    })
                
                # Set session expiry based on remember_me
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                
                # Log user in
                login(request, user)
                
                # Redirect based on user type
                if user.user_type == 1:
                    return redirect('admin_dashboard')
                elif user.user_type == 2:
                    return redirect('teacher_dashboard')
                else:
                    return redirect('student_dashboard')
            else:
                form.add_error(None, 'Invalid username/email or password.')
        
        # Form has errors - will be displayed in template
        return render(request, 'accounts/login.html', {'form': form})
    
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def teacher_dashboard(request):
    total_questions = Question.objects.filter(author=request.user).count()
    teacher_submissions_q = Submission.objects.select_related('question').filter(question__author=request.user)
    teacher_attempts_q = TestAttempt.objects.select_related('test').filter(test__created_by=request.user, is_submitted=True)
    total_submissions = teacher_submissions_q.count() + teacher_attempts_q.count()
    pending_legacy = teacher_submissions_q.filter(graded=False).count()
    pending_subjective = TestAnswer.objects.select_related('attempt', 'attempt__test', 'question').filter(
        attempt__test__created_by=request.user,
        attempt__is_submitted=True,
        question__type__in=['short', 'essay'],
        score__isnull=True,
    ).count()
    pending_reviews = pending_legacy + pending_subjective
    
    combined_recent = []
    for sub in teacher_submissions_q.select_related('student', 'question').order_by('-submitted_at')[:5]:
        combined_recent.append({
            'type': 'legacy',
            'student': sub.student,
            'question': sub.question,
            'submitted_at': sub.submitted_at,
            'graded': sub.graded,
        })
    
    for attempt in teacher_attempts_q.select_related('test', 'student').order_by('-submitted_at')[:5]:
        ungraded_count = TestAnswer.objects.filter(
            attempt=attempt,
            question__type__in=['short', 'essay'],
            score__isnull=True
        ).count()
        combined_recent.append({
            'type': 'test_attempt',
            'student': attempt.student,
            'test': attempt.test,
            'submitted_at': attempt.submitted_at,
            'graded': ungraded_count == 0,
        })
    
    combined_recent.sort(key=lambda x: x['submitted_at'], reverse=True)
    latest_submissions = combined_recent[:10]
    
    # Get recent notifications
    from questions.models import Notification
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]
    
    unread_notifications_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    ctx = {
        'total_questions': total_questions,
        'pending_reviews': pending_reviews,
        'total_submissions': total_submissions,
        'latest_submissions': latest_submissions,
        'unread_notifications': unread_notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'dashboards/teacher_dashboard.html', ctx)


@login_required
@login_required
def admin_dashboard(request):
    if request.user.user_type != 1:
        return redirect('home')
    
    users_count = CustomUser.objects.count()
    questions_count = Question.objects.count()
    try:
        tests_count = Test.objects.count()
    except Exception:
        tests_count = Question.objects.values('subject').distinct().count()
    
    # Get legacy submissions count
    legacy_submissions_count = Submission.objects.count()
    
    # Get test attempts count
    test_attempts_count = TestAttempt.objects.filter(is_submitted=True).count()
    
    # Total submissions
    submissions_count = legacy_submissions_count + test_attempts_count
    
    # Get recent submissions (combined from both legacy and test attempts)
    recent_legacy = Submission.objects.select_related('student', 'question', 'question__author').order_by('-submitted_at')[:5]
    recent_attempts = TestAttempt.objects.select_related('test', 'test__created_by', 'student').filter(is_submitted=True).order_by('-submitted_at')[:5]
    
    # Combine and sort by date
    from itertools import chain
    combined = list(chain(recent_legacy, recent_attempts))
    combined.sort(key=lambda x: x.submitted_at, reverse=True)
    recent_submissions = combined[:10]
    
    # Get recent help requests and notifications
    from accounts.models import HelpRequest
    from questions.models import Notification
    
    pending_help_requests = HelpRequest.objects.filter(
        status__in=['pending', 'in_progress']
    ).order_by('-created_at')[:5]
    
    recent_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]
    
    unread_notifications_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    ctx = {
        'users_count': users_count,
        'questions_count': questions_count,
        'tests_count': tests_count,
        'submissions_count': submissions_count,
        'recent_submissions': recent_submissions,
        'pending_help_requests': pending_help_requests,
        'recent_notifications': recent_notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'dashboards/admin_dashboard.html', ctx)


@login_required
def admin_users(request):
    if request.user.user_type != 1:
        return redirect('home')
    users = CustomUser.objects.all().order_by('username')
    return render(request, 'accounts/admin_users.html', { 'users': users })


@login_required
def admin_create_user(request):
    """
    Admin creates user with automatic validation via Django Forms.
    
    Now uses AdminUserCreationForm for:
    - Automatic validation
    - Consistent password requirements (8+ chars)
    - Username/email uniqueness checking
    - Cleaner, safer code
    """
    if request.user.user_type != 1:
        return redirect('home')
    
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f'User "{user.username}" has been successfully created.')
                return redirect('admin_users')
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error creating user: {e}")
                messages.error(request, f'Error creating user: {str(e)}')
        
        # Form has errors - will be displayed in template
        return render(request, 'accounts/admin_create_user.html', {'form': form})
    
    else:
        form = AdminUserCreationForm()
    
    return render(request, 'accounts/admin_create_user.html', {'form': form})


@login_required
def admin_delete_user(request, id):
    if request.user.user_type != 1:
        return redirect('home')
    if request.method == 'POST':
        try:
            u = CustomUser.objects.get(id=id)
            if u.id != request.user.id:
                username = u.username
                # Clear many-to-many relationships first
                u.groups.clear()
                u.user_permissions.clear()
                # Now delete the user
                u.delete()
                from django.contrib import messages
                messages.success(request, f'User "{username}" has been successfully deleted.')
            else:
                from django.contrib import messages
                messages.error(request, 'You cannot delete your own account.')
        except CustomUser.DoesNotExist:
            from django.contrib import messages
            messages.error(request, 'User not found.')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error deleting user: {str(e)}')
        return redirect('admin_users')
    return redirect('admin_users')


@login_required
def admin_block_user(request, id):
    """Toggle user block status"""
    if request.user.user_type != 1:
        return redirect('home')
    if request.method == 'POST':
        try:
            u = CustomUser.objects.get(id=id)
            if u.id != request.user.id:
                u.is_blocked = not u.is_blocked
                u.save(update_fields=['is_blocked'])
                from django.contrib import messages
                status = 'blocked' if u.is_blocked else 'unblocked'
                messages.success(request, f'User "{u.username}" has been {status}.')
            else:
                from django.contrib import messages
                messages.error(request, 'You cannot block your own account.')
        except CustomUser.DoesNotExist:
            from django.contrib import messages
            messages.error(request, 'User not found.')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error updating user: {str(e)}')
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
    return render(request, 'accounts/admin_activity.html', {
        'questions_count': questions_count,
        'submissions_count': submissions_count,
        'created_by_teacher': created_by_teacher,
        'submissions_by_student': submissions_by_student,
    })


@login_required
def admin_questions(request):
    """Admin view to see all questions from all teachers"""
    if request.user.user_type != 1:
        return redirect('home')
    
    # Get all questions with author information
    questions = Question.objects.select_related('author').prefetch_related('folders').order_by('-created_at')
    
    # Filter by search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        questions = questions.filter(
            Q(question_text__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(author__username__icontains=search_query)
        )
    
    # Filter by folder if provided
    folder_id = request.GET.get('folder')
    current_folder = None
    if folder_id:
        try:
            from questions.models import QuestionFolder
            current_folder = QuestionFolder.objects.get(id=folder_id)
            questions = questions.filter(folders__id=folder_id)
        except QuestionFolder.DoesNotExist:
            pass
    
    # Get all folders for filter dropdown
    from questions.models import QuestionFolder
    all_folders = QuestionFolder.objects.filter(parent=None, is_archived=False).prefetch_related('subfolders')
    
    return render(request, 'accounts/admin_questions.html', {
        'questions': questions,
        'search_query': search_query,
        'current_folder': current_folder,
        'folders': all_folders,
    })


@login_required
def admin_tests(request):
    """Admin view to see all tests from all teachers"""
    if request.user.user_type != 1:
        return redirect('home')
    
    # Get all tests with creator information
    tests = Test.objects.select_related('created_by').prefetch_related('questions').order_by('-created_at')
    
    # Filter by search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        tests = tests.filter(
            Q(title__icontains=search_query) |
            Q(created_by__username__icontains=search_query)
        )
    
    return render(request, 'accounts/admin_tests.html', {
        'tests': tests,
        'search_query': search_query,
    })


@login_required
@login_required
def admin_submissions(request):
    """Admin view to see all submissions from all students"""
    if request.user.user_type != 1:
        return redirect('home')
    
    # Get all submissions (legacy system)
    legacy_submissions = Submission.objects.select_related('question', 'student', 'question__author')\
        .order_by('-submitted_at')
    
    # Get all test attempts (new system)
    test_attempts = TestAttempt.objects.select_related('test', 'student', 'test__created_by')\
        .filter(is_submitted=True)\
        .prefetch_related('answers__question')\
        .order_by('-submitted_at')
    
    # Filter by search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        legacy_submissions = legacy_submissions.filter(
            Q(student__username__icontains=search_query) |
            Q(question__question_text__icontains=search_query) |
            Q(question__author__username__icontains=search_query)
        )
        test_attempts = test_attempts.filter(
            Q(student__username__icontains=search_query) |
            Q(test__title__icontains=search_query) |
            Q(test__created_by__username__icontains=search_query)
        )
    
    # Combine both into a unified list
    combined_submissions = []
    
    # Add legacy submissions
    for sub in legacy_submissions:
        combined_submissions.append({
            'type': 'legacy',
            'id': sub.id,
            'student': sub.student,
            'teacher': sub.question.author,
            'question': sub.question,
            'graded': sub.graded,
            'score': sub.score,
            'submitted_at': sub.submitted_at,
        })
    
    # Add test attempts
    for attempt in test_attempts:
        total_answers = attempt.answers.count()
        graded_answers = attempt.answers.filter(score__isnull=False).count()
        ungraded_subjective = attempt.answers.filter(
            question__type__in=['short', 'essay'],
            score__isnull=True
        ).count()
        
        combined_submissions.append({
            'type': 'test_attempt',
            'id': attempt.id,
            'student': attempt.student,
            'teacher': attempt.test.created_by,
            'test_name': attempt.test.title,
            'test': attempt.test,
            'attempt_number': attempt.attempt_number,
            'total_score': attempt.total_score,
            'submitted_at': attempt.submitted_at,
            'total_questions': total_answers,
            'graded_count': graded_answers,
            'graded': ungraded_subjective == 0,
        })
    
    # Sort by submission date (newest first)
    combined_submissions.sort(key=lambda x: x['submitted_at'], reverse=True)
    
    return render(request, 'accounts/admin_submissions.html', {
        'submissions': combined_submissions,
        'search_query': search_query,
        'legacy_count': legacy_submissions.count(),
        'test_attempt_count': test_attempts.count(),
    })


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
    return render(request, 'accounts/teacher_reports.html', {
        'by_student': by_student,
        'by_question': by_question,
    })


@login_required
def profile_view(request):
    """Display user profile with role-specific information"""
    context = {
        'user': request.user,
    }
    
    # Add role-specific profile data
    if request.user.user_type == 3:  # Student
        try:
            from students.models import StudentProfile
            context['profile'] = StudentProfile.objects.get(user=request.user)
        except StudentProfile.DoesNotExist:
            context['profile'] = None
    elif request.user.user_type == 2:  # Teacher
        try:
            from core.models import TeacherProfile
            context['profile'] = TeacherProfile.objects.get(user=request.user)
        except TeacherProfile.DoesNotExist:
            context['profile'] = None
    
    return render(request, 'accounts/profile.html', context)


def dashboard_home(request):
    if request.user.is_authenticated:
        if request.user.user_type == 1:
            return redirect('admin_dashboard')
        elif request.user.user_type == 2:
            return redirect('teacher_dashboard')
        else:
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
        return render(request, 'accounts/verify_email_success.html')
    else:
        return render(request, 'accounts/verify_email_failed.html')


@login_required
def admin_help(request):
    """Admin help portal - view and manage student support requests"""
    if request.user.user_type != 1:
        return redirect('dashboard_home')
    
    from accounts.models import HelpRequest
    from django.db.models import Q
    
    # Get all help requests
    help_requests = HelpRequest.objects.select_related('student', 'responded_by').order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    if status_filter:
        help_requests = help_requests.filter(status=status_filter)
    
    # Filter by priority if provided
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        help_requests = help_requests.filter(priority=priority_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        help_requests = help_requests.filter(
            Q(subject__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(student__username__icontains=search_query) |
            Q(student__email__icontains=search_query)
        )
    
    # Get counts for stats
    total_requests = HelpRequest.objects.count()
    pending_requests = HelpRequest.objects.filter(status='pending').count()
    in_progress_requests = HelpRequest.objects.filter(status='in_progress').count()
    resolved_requests = HelpRequest.objects.filter(status__in=['resolved', 'closed']).count()
    
    return render(request, 'accounts/admin_help.html', {
        'help_requests': help_requests,
        'search_query': search_query,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'in_progress_requests': in_progress_requests,
        'resolved_requests': resolved_requests,
    })


@login_required
def admin_delete_question(request, id):
    """Delete a question (admin only)"""
    if request.user.user_type != 1:
        return redirect('dashboard_home')
    
    if request.method == 'POST':
        try:
            from questions.models import Question
            question = Question.objects.get(id=id)
            question.delete()
            from django.contrib import messages
            messages.success(request, f'Question has been successfully deleted.')
        except Question.DoesNotExist:
            from django.contrib import messages
            messages.error(request, 'Question not found.')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error deleting question: {str(e)}')
    
    return redirect('admin_questions')


@login_required
def admin_delete_test(request, id):
    """Delete a test (admin only)"""
    if request.user.user_type != 1:
        return redirect('dashboard_home')
    
    if request.method == 'POST':
        try:
            from exams.models import Test
            test = Test.objects.get(id=id)
            test.delete()
            from django.contrib import messages
            messages.success(request, f'Test "{test.title}" has been successfully deleted.')
        except Test.DoesNotExist:
            from django.contrib import messages
            messages.error(request, 'Test not found.')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error deleting test: {str(e)}')
    
    return redirect('admin_tests')


@login_required
def admin_delete_help(request, id):
    """Delete a help request (admin only)"""
    if request.user.user_type != 1:
        return redirect('dashboard_home')
    
    if request.method == 'POST':
        try:
            from accounts.models import HelpRequest
            from django.contrib import messages
            
            help_request = HelpRequest.objects.get(id=id)
            subject = help_request.subject
            student_name = help_request.student.username
            help_request.delete()
            messages.success(request, f'Help request from {student_name} - "{subject}" has been successfully deleted.')
        except HelpRequest.DoesNotExist:
            from django.contrib import messages
            messages.error(request, 'Help request not found.')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error deleting help request: {str(e)}')
    
    return redirect('admin_help')


@login_required
def admin_respond_help(request, id):
    """Respond to a student help request (admin only)"""
    if request.user.user_type != 1:
        return redirect('dashboard_home')
    
    if request.method == 'POST':
        try:
            from accounts.models import HelpRequest
            from django.contrib import messages
            from django.utils import timezone
            
            help_request = HelpRequest.objects.get(id=id)
            response = request.POST.get('response', '').strip()
            new_status = request.POST.get('status', help_request.status)
            
            if response:
                help_request.admin_response = response
                help_request.responded_by = request.user
                help_request.status = new_status
                
                if new_status in ['resolved', 'closed']:
                    help_request.resolved_at = timezone.now()
                
                help_request.save()
                
                # Send email notification to student
                try:
                    from core.email_service import EmailService
                    email_service = EmailService()
                    email_service.send_help_request_notification(help_request, to_admin=False)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to send help response notification email: {e}")
                
                messages.success(request, 'Response sent successfully.')
            else:
                messages.error(request, 'Please provide a response.')
        except HelpRequest.DoesNotExist:
            from django.contrib import messages
            messages.error(request, 'Help request not found.')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error sending response: {str(e)}')
    
    return redirect('admin_help')


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
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to resend verification email: {e}")
        return render(request, 'accounts/resend_verification_sent.html')
    return render(request, 'accounts/resend_verification_form.html')


@login_required
def teacher_notifications(request):
    """Display all notifications for teacher."""
    if request.user.user_type != 2:
        return redirect('teacher_dashboard')
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read
    if request.method == 'POST':
        action = request.POST.get('action', 'mark_read')
        if action == 'clear_all':
            Notification.objects.filter(user=request.user).delete()
            messages.success(request, 'All notifications cleared successfully.')
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            messages.success(request, 'All notifications marked as read.')
        return redirect('teacher_notifications')
    
    unread_notifications_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    context = {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'accounts/teacher_notifications.html', context)


@login_required
def admin_notifications(request):
    """Display all notifications for admin."""
    if request.user.user_type != 1 and not request.user.is_staff:
        return redirect('admin_dashboard')
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read
    if request.method == 'POST':
        action = request.POST.get('action', 'mark_read')
        if action == 'clear_all':
            Notification.objects.filter(user=request.user).delete()
            messages.success(request, 'All notifications cleared successfully.')
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            messages.success(request, 'All notifications marked as read.')
        return redirect('admin_notifications')
    
    unread_notifications_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    context = {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'accounts/admin_notifications.html', context)


@login_required
def mark_teacher_notification_read(request, notification_id):
    """Mark a teacher notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    # Redirect to notification link if exists
    if notification.link:
        return redirect(notification.link)
    
    # Check for next parameter
    next_url = request.GET.get('next', '')
    if next_url:
        return redirect(next_url)
    
    return redirect('teacher_notifications')


@login_required
def mark_admin_notification_read(request, notification_id):
    """Mark an admin notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    # Redirect to notification link if exists
    if notification.link:
        return redirect(notification.link)
    
    # Check for next parameter
    next_url = request.GET.get('next', '')
    if next_url:
        return redirect(next_url)
    
    return redirect('admin_notifications')
