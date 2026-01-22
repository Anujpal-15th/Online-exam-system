from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum, Q, Max, F
from django.http import HttpResponse, JsonResponse
import csv
from .models import (Question, Submission, QuestionOption, Resource, Notification, QuestionFolder, MaterialFolder, Tag)
from exams.models import (Test, TestQuestion, TestAttempt, TestAnswer, Certificate, MarkedQuestion)
from django.utils import timezone
from datetime import timedelta, datetime
from django.db import transaction
from django.contrib import messages
import json
from io import TextIOWrapper, BytesIO
import uuid
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from core.email_service import EmailService


def _get_student_context(request):
    """Helper function to get common context for all student views."""
    context = {}
    if request.user.is_authenticated and request.user.user_type == 3:
        context['unread_notifications'] = Notification.objects.filter(
            user=request.user,
            is_read=False
        )
    return context


def _create_notification(user, title, message, notification_type='general', link=''):
    """Helper function to create notifications for users."""
    try:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to create notification: {e}")


def questions_list(request):
    qs = Question.objects.select_related('author').prefetch_related('tags').all()
    subject = request.GET.get('subject')
    topic = request.GET.get('topic')
    difficulty = request.GET.get('difficulty')
    search = request.GET.get('q')
    folder_id = request.GET.get('folder')
    tag_slug = request.GET.get('tag')

    # Scope for teachers: see only own questions
    try:
        if request.user.is_authenticated and getattr(request.user, 'user_type', None) == 2:
            qs = qs.filter(author=request.user)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error filtering questions by author: {e}")

    if subject:
        qs = qs.filter(subject__iexact=subject)
    if topic:
        qs = qs.filter(topic__iexact=topic)
    if difficulty:
        qs = qs.filter(difficulty=difficulty)
    if search:
        qs = qs.filter(question_text__icontains=search)
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)
    if folder_id:
        if folder_id == 'all':
            # Show all questions including those in folders
            pass
        else:
            # Show questions in specific folder
            qs = qs.filter(folders__id=folder_id)
    else:
        # Default: show only questions NOT in any folder
        qs = qs.filter(folders__isnull=True)
    
    # Get current folder for breadcrumb
    current_folder = None
    if folder_id and folder_id != 'all':
        try:
            current_folder = QuestionFolder.objects.get(id=folder_id, created_by=request.user)
        except QuestionFolder.DoesNotExist:
            pass
    
    # Get all folders for sidebar
    folders = QuestionFolder.objects.filter(
        created_by=request.user,
        parent=None,
        is_archived=False
    ).prefetch_related('subfolders', 'questions') if request.user.is_authenticated and request.user.user_type in (1, 2) else []
    
    # Get available tags for filter
    available_tags = Tag.objects.filter(
        Q(created_by=request.user) | Q(is_global=True)
    ).annotate(
        question_count=Count('questions', filter=Q(questions__author=request.user))
    ).filter(question_count__gt=0).order_by('name') if request.user.is_authenticated and request.user.user_type in (1, 2) else []
    
    # Get current tag
    current_tag = None
    if tag_slug and request.user.is_authenticated and request.user.user_type in (1, 2):
        try:
            current_tag = Tag.objects.get(slug=tag_slug)
        except Tag.DoesNotExist:
            pass

    return render(request, 'questions/questions_list.html', {
        'questions': qs,
        'current_folder': current_folder,
        'folders': folders,
        'available_tags': available_tags,
        'current_tag': current_tag,
    })

@login_required
def add_question(request):
    if request.user.user_type not in (1, 2):  # admins and teachers
        return redirect('questions_list')
    if request.method == 'POST':
        # File upload flow
        if request.FILES.get('question_file'):
            upload = request.FILES['question_file']
            name = (upload.name or '').lower()
            created_count = 0
            try:
                if name.endswith('.json') or name.endswith('.txt'):
                    # Expect JSON array/object
                    text = upload.read().decode('utf-8', errors='ignore')
                    data = json.loads(text)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        created_count += _create_question_from_dict(item, request.user)
                elif name.endswith('.csv'):
                    f = TextIOWrapper(upload.file, encoding='utf-8', errors='ignore')
                    reader = csv.DictReader(f)
                    for row in reader:
                        created_count += _create_question_from_dict(row, request.user)
                else:
                    messages.error(request, 'Unsupported file format. Please upload JSON, TXT (JSON) or CSV.')
                    return redirect('add_question')
                messages.success(request, f'Uploaded and created {created_count} question(s).')
                return redirect('questions_list')
            except Exception as e:
                messages.error(request, f'Failed to process file: {e}')
                return redirect('add_question')

        text = request.POST.get('question_text','').strip()
        subject = request.POST.get('subject', '').strip()
        topic = request.POST.get('topic', '').strip()
        difficulty = request.POST.get('difficulty', 'easy')
        marks = request.POST.get('marks', '1')
        try:
            marks = int(marks)
        except ValueError:
            marks = 1
        qtype_form = request.POST.get('question_type')
        # map template type -> model type
        type_map = {
            'multiple_choice': 'mcq_single',
            'true_false': 'true_false',
            'short_answer': 'short',
            'essay': 'essay',
            'fill_blanks': 'fill_in',
            'matching': 'matching',
            'numerical': 'numerical',
        }
        qtype = type_map.get(qtype_form, 'short')
        
        q = Question.objects.create(
            question_text=text,
            type=qtype,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            marks=marks,
            author=request.user,
        )
        
        # Add question to selected folders
        folder_ids = request.POST.getlist('folders')
        if folder_ids:
            folders = QuestionFolder.objects.filter(id__in=folder_ids, created_by=request.user)
            q.folders.set(folders)
        
        # build answer key / options
        if qtype == 'mcq_single':
            opts = []
            for i in ['1','2','3','4']:
                val = request.POST.get(f'option{i}', '').strip()
                if val:
                    opts.append(val)
            correct_idx = request.POST.get('correct_answer', '1')
            try:
                cidx = int(correct_idx)
            except Exception:
                cidx = 1
            order = 1
            for idx, txt in enumerate(opts, start=1):
                QuestionOption.objects.create(question=q, text=txt, is_correct=(idx == cidx), order=order)
                order += 1
        elif qtype == 'true_false':
            tf = request.POST.get('tf_answer', 'true') == 'true'
            q.answer_key = {'correct': tf}
            q.save(update_fields=['answer_key'])
        elif qtype == 'fill_in':
            raw = request.POST.get('blank_answer', '')
            answers = [a.strip() for a in raw.split(';') if a.strip()]
            q.answer_key = {'answers': answers}
            q.save(update_fields=['answer_key'])
        elif qtype == 'matching':
            lefts = request.POST.getlist('match_left[]')
            rights = request.POST.getlist('match_right[]')
            pairs = {}
            for l, r in zip(lefts, rights):
                l = (l or '').strip()
                r = (r or '').strip()
                if l and r:
                    pairs[l] = r
            q.answer_key = {'pairs': pairs}
            q.save(update_fields=['answer_key'])
        elif qtype == 'numerical':
            try:
                value = float(request.POST.get('numerical_answer'))
            except Exception:
                value = None
            try:
                margin = float(request.POST.get('error_margin') or 0)
            except Exception:
                margin = 0
            if value is not None:
                q.answer_key = {'value': value, 'margin': margin}
                q.save(update_fields=['answer_key'])
        elif qtype in ('short','essay'):
            rubric = request.POST.get('essay_rubric', '') or request.POST.get('short_answer', '')
            if rubric:
                q.rubric_text = rubric
                q.save(update_fields=['rubric_text'])
        # Show success message and redirect to same page
        messages.success(request, 'Question added successfully!')
        return redirect('add_question')
    
    # Pass base_template based on user type
    base_template = 'dashboards/admin_base.html' if request.user.user_type == 1 else 'dashboards/teacher_base.html'
    return render(request, 'questions/add_question.html', {'base_template': base_template})


def _create_question_from_dict(item, user):
    """Create a Question from a dict-like item. Returns 1 on success, 0 otherwise."""
    try:
        # normalize mapping
        getv = lambda *keys: next((item.get(k) for k in keys if isinstance(item, dict) and item.get(k) is not None), None)
        text = (getv('question_text', 'text') or '').strip()
        if not text:
            return 0
        type_map = {
            'multiple_choice': 'mcq_single', 'mcq_single': 'mcq_single', 'mcq_multi': 'mcq_multi',
            'true_false': 'true_false', 'short': 'short', 'short_answer': 'short', 'essay': 'essay',
            'fill_in': 'fill_in', 'fill_blanks': 'fill_in', 'matching': 'matching', 'numerical': 'numerical',
        }
        raw_type = (str(getv('type', 'question_type') or 'short')).lower()
        qtype = type_map.get(raw_type, 'short')
        subject = (getv('subject') or '').strip()
        topic = (getv('topic') or '').strip()
        difficulty = (getv('difficulty') or 'easy') or 'easy'
        q = Question.objects.create(
            question_text=text,
            type=qtype,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            author=user,
        )
        # objective types
        if qtype in ('mcq_single','mcq_multi'):
            opts = getv('options')
            if isinstance(opts, str):
                opts = [o.strip() for o in opts.split('|') if o.strip()]
            if not isinstance(opts, list):
                opts = []
            correct = getv('correct')
            correct_set = set()
            if qtype == 'mcq_single':
                if isinstance(correct, str) and correct.isdigit():
                    correct_set.add(int(correct))
                elif isinstance(correct, (int, float)):
                    correct_set.add(int(correct))
            else:
                if isinstance(correct, str):
                    for part in correct.split(','):
                        part = part.strip()
                        if part.isdigit():
                            correct_set.add(int(part))
                elif isinstance(correct, list):
                    for v in correct:
                        try:
                            correct_set.add(int(v))
                        except (ValueError, TypeError):
                            continue  # Skip invalid option values
            order = 1
            for idx, txt in enumerate(opts, start=1):
                is_corr = (idx in correct_set) or (isinstance(correct, str) and correct.lower() == txt.lower())
                QuestionOption.objects.create(question=q, text=txt, is_correct=is_corr, order=order)
                order += 1
        elif qtype == 'true_false':
            val = getv('true_false', 'correct')
            if isinstance(val, str):
                val = val.strip().lower() in ('true','1','yes','y')
            q.answer_key = {'correct': bool(val)}
            q.save(update_fields=['answer_key'])
        elif qtype == 'fill_in':
            answers = getv('fill_answers', 'answers', 'correct') or ''
            if isinstance(answers, str):
                answers = [a.strip() for a in answers.replace('|',';').split(';') if a.strip()]
            elif not isinstance(answers, list):
                answers = []
            q.answer_key = {'answers': answers}
            q.save(update_fields=['answer_key'])
        elif qtype == 'matching':
            pairs = getv('matching_pairs') or {}
            if isinstance(pairs, str):
                mapping = {}
                for seg in pairs.split('|'):
                    if ':' in seg:
                        l, r = seg.split(':', 1)
                        l = l.strip(); r = r.strip()
                        if l and r:
                            mapping[l] = r
                pairs = mapping
            if not isinstance(pairs, dict):
                pairs = {}
            q.answer_key = {'pairs': pairs}
            q.save(update_fields=['answer_key'])
        elif qtype == 'numerical':
            try:
                value = float(getv('numerical_value', 'value'))
            except Exception:
                value = None
            try:
                margin = float(getv('numerical_margin', 'margin') or 0)
            except Exception:
                margin = 0
            if value is not None:
                q.answer_key = {'value': value, 'margin': margin}
                q.save(update_fields=['answer_key'])
        else:
            rubric = (getv('rubric') or '')
            if rubric:
                q.rubric_text = rubric
                q.save(update_fields=['rubric_text'])
        return 1
    except Exception:
        return 0

@login_required
def edit_question(request, id):
    if request.user.user_type != 2 and request.user.user_type != 1:
        return redirect('questions_list')
    question = get_object_or_404(Question, id=id)
    # Teachers can only edit their own questions
    if request.user.user_type == 2 and question.author_id != request.user.id:
        return redirect('questions_list')
    if request.method == 'POST':
        question.question_text = request.POST['question_text']
        question.subject = request.POST.get('subject', '').strip()
        question.topic = request.POST.get('topic', '').strip()
        question.difficulty = request.POST.get('difficulty', question.difficulty)
        question.save()
        
        # Update folders
        folder_ids = request.POST.getlist('folders')
        if folder_ids:
            folders = QuestionFolder.objects.filter(id__in=folder_ids, created_by=request.user)
            question.folders.set(folders)
        else:
            question.folders.clear()
        
        # Redirect based on user type
        if request.user.user_type == 1:
            return redirect('admin_questions')
        return redirect('questions_list')
    
    # Get question folders as JSON for JavaScript
    import json
    question_folders = list(question.folders.values('id', 'name'))
    question_folders_json = json.dumps(question_folders)
    
    # Pass base_template based on user type
    base_template = 'dashboards/admin_base.html' if request.user.user_type == 1 else 'dashboards/teacher_base.html'
    return render(request, 'questions/edit_question.html', {
        'question': question,
        'base_template': base_template,
        'question_folders': question_folders_json
    })

@login_required
def delete_question(request, id):
    if request.user.user_type != 2 and request.user.user_type != 1:
        return redirect('questions_list')
    question = get_object_or_404(Question, id=id)
    # Teachers can only delete their own questions
    if request.user.user_type == 2 and question.author_id != request.user.id:
        return redirect('questions_list')
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
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    
    # Get all submissions for teacher's questions (legacy system)
    legacy_submissions = Submission.objects.select_related('question', 'student')\
        .filter(question__author=request.user).order_by('-submitted_at')
    
    # Get all test attempts for teacher's tests (new system)
    test_attempts = TestAttempt.objects.select_related('test', 'student')\
        .filter(test__created_by=request.user, is_submitted=True)\
        .prefetch_related('answers__question')\
        .order_by('-submitted_at')
    
    # Combine both into a unified list with metadata
    combined_submissions = []
    
    # Add legacy submissions
    for sub in legacy_submissions:
        combined_submissions.append({
            'type': 'legacy',
            'id': sub.id,
            'student': sub.student,
            'question': sub.question,
            'answer_text': sub.answer_text,
            'graded': sub.graded,
            'score': sub.score,
            'submitted_at': sub.submitted_at,
            'test_name': None,
            'total_questions': 1,
            'graded_count': 1 if sub.graded else 0,
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
            'test_name': attempt.test.title,
            'test': attempt.test,
            'attempt_number': attempt.attempt_number,
            'total_score': attempt.total_score,
            'submitted_at': attempt.submitted_at,
            'total_questions': total_answers,
            'graded_count': graded_answers,
            'ungraded_subjective': ungraded_subjective,
            'graded': ungraded_subjective == 0,  # Fully graded if no ungraded subjective questions
        })
    
    # Sort by submission date (newest first)
    combined_submissions.sort(key=lambda x: x['submitted_at'], reverse=True)
    
    context = {
        'submissions': combined_submissions,
        'legacy_count': legacy_submissions.count(),
        'test_attempt_count': test_attempts.count(),
    }
    
    return render(request, 'questions/submissions_list.html', context)


@login_required
def grade_submission(request, id):
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    sub = get_object_or_404(Submission, id=id)
    # Teachers may grade only submissions for their own questions
    if sub.question.author_id != request.user.id:
        return redirect('submissions_list')
    if request.method == 'POST':
        sub.graded = True
        sub.score = int(request.POST.get('score', 0))
        sub.feedback = request.POST.get('feedback', '')
        sub.save()
        return redirect('submissions_list')
    return render(request, 'questions/grade_submission.html', {'submission': sub})


@login_required
def grade_test_attempt(request, attempt_id):
    """Grade a test attempt - view and grade all subjective answers."""
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    
    attempt = get_object_or_404(
        TestAttempt.objects.select_related('test', 'student')
        .prefetch_related('answers__question__options'),
        id=attempt_id
    )
    
    # Verify teacher owns this test
    if attempt.test.created_by_id != request.user.id:
        return redirect('submissions_list')
    
    if request.method == 'POST':
        # Process grading for subjective questions
        for answer in attempt.answers.filter(question__type__in=['short', 'essay']):
            score_key = f'score_{answer.id}'
            if score_key in request.POST:
                try:
                    score = int(request.POST.get(score_key, 0))
                    answer.score = score
                    answer.save()
                except ValueError:
                    import logging
                    logging.getLogger(__name__).warning(f"Invalid score value for answer {answer.id}")
                    continue
        
        # Recalculate total score
        total = attempt.answers.filter(score__isnull=False).aggregate(Sum('score'))['score__sum'] or 0
        attempt.total_score = total
        attempt.save()
        
        # Notify student about graded result
        _create_notification(
            user=attempt.student,
            title=f"Results Published: {attempt.test.title}",
            message=f"Your test '{attempt.test.title}' has been graded. Total score: {total}. Click to view detailed results.",
            notification_type='result_published',
            link=f'/questions/review/{attempt.id}/'
        )
        
        # Send email notification to student
        try:
            email_service = EmailService()
            email_service.send_grade_notification(attempt)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send grade notification email: {e}")
        
        messages.success(request, f'Test graded successfully! Total score: {total}. Notification sent to student.')
        return redirect('submissions_list')
    
    # Get all answers with their questions
    answers_with_details = []
    for answer in attempt.answers.select_related('question').prefetch_related('question__options'):
        question = answer.question
        
        # Determine if this answer is correct (for objective questions)
        is_correct = None
        correct_answer = None
        
        if question.type == 'mcq_single':
            try:
                selected_option_id = int(answer.answer_text) if answer.answer_text else None
                correct_option = question.options.filter(is_correct=True).first()
                if correct_option:
                    is_correct = (selected_option_id == correct_option.id)
                    correct_answer = correct_option.text
            except (ValueError, TypeError):
                # Answer text is not a valid option ID
                is_correct = False
        elif question.type == 'true_false':
            correct_ans = question.answer_key.get('correct', None)
            if correct_ans is not None:
                is_correct = (answer.answer_text.lower() == str(correct_ans).lower())
                correct_answer = str(correct_ans)
        
        answers_with_details.append({
            'answer': answer,
            'question': question,
            'is_correct': is_correct,
            'correct_answer': correct_answer,
            'needs_grading': question.type in ['short', 'essay'] and answer.score is None,
        })
    
    # Get test question points
    test_questions = TestQuestion.objects.filter(test=attempt.test).select_related('question')
    question_points = {tq.question_id: tq.points for tq in test_questions}
    
    context = {
        'attempt': attempt,
        'answers_with_details': answers_with_details,
        'question_points': question_points,
        'subjective_count': attempt.answers.filter(question__type__in=['short', 'essay']).count(),
        'ungraded_count': attempt.answers.filter(question__type__in=['short', 'essay'], score__isnull=True).count(),
    }
    
    return render(request, 'questions/grade_test_attempt.html', context)


@login_required
def leaderboard(request):
    # Top students by total score
    agg = Submission.objects.filter(graded=True).values('student__username').annotate(
        total_score=Sum('score'), count=Count('id'), avg=Avg('score')
    ).order_by('-total_score')[:20]
    return render(request, 'questions/leaderboard.html', {'rows': agg})


@login_required
def export_performance_csv(request):
    if request.user.user_type not in (1, 2):
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
def tests_list(request):
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    tests = Test.objects.select_related('created_by').order_by('-created_at')
    # Teachers see only tests they created
    if request.user.user_type == 2:
        tests = tests.filter(created_by=request.user)
    return render(request, 'questions/tests_list.html', { 'tests': tests })


@login_required
def add_test(request):
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        subject = request.POST.get('subject', '').strip()
        q_ids = request.POST.getlist('question_ids')
        
        if not title:
            # Recompute allowed questions for teacher on validation error
            allowed_qs = Question.objects.all()
            if request.user.user_type == 2:
                allowed_qs = allowed_qs.filter(author=request.user)
            return render(request, 'questions/add_test.html', {
                'error': 'Title is required.',
                'questions': allowed_qs.order_by('-created_at')[:200]
            })
        
        if not q_ids:
            # No questions selected
            allowed_qs = Question.objects.all()
            if request.user.user_type == 2:
                allowed_qs = allowed_qs.filter(author=request.user)
            return render(request, 'questions/add_test.html', {
                'error': 'Please select at least one question.',
                'questions': allowed_qs.order_by('-created_at')[:200]
            })
        
        # Create test with basic info
        test = Test.objects.create(
            title=title, 
            subject=subject, 
            created_by=request.user,
            duration_minutes=30  # Default duration
        )
        
        # Attach selected questions in order
        order = 1
        for qid in q_ids:
            try:
                q = Question.objects.get(id=int(qid))
                TestQuestion.objects.create(test=test, question=q, order=order, points=1)
                order += 1
            except (Question.DoesNotExist, ValueError):
                continue
        
        messages.success(request, f'Test "{title}" created! Now arrange questions and set schedule.')
        # Redirect to edit_paper to arrange questions and set schedule
        return redirect('edit_paper', test_id=test.id)

    # Admins see all questions, teachers can only pick from their own questions
    all_qs = Question.objects.all()
    if request.user.user_type == 2:
        all_qs = all_qs.filter(author=request.user)
    all_questions = all_qs.order_by('-created_at')[:200]
    
    # Pass base_template based on user type
    base_template = 'dashboards/admin_base.html' if request.user.user_type == 1 else 'dashboards/teacher_base.html'
    return render(request, 'questions/add_test.html', { 'questions': all_questions, 'base_template': base_template })


@login_required
def paper_builder(request):
    """Paper Builder - Scheduling dashboard for prepared tests"""
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    
    # Get all tests created by this teacher
    if request.user.user_type == 1:
        tests = Test.objects.select_related('created_by').all()
    else:
        tests = Test.objects.select_related('created_by').filter(created_by=request.user)
    
    # Annotate with question count and calculated marks
    tests = tests.annotate(
        question_count=Count('questions'),
        calculated_marks=Sum('testquestion__points')
    ).order_by('-created_at')
    
    # Categorize tests
    scheduled_tests = []
    unscheduled_tests = []
    
    for test in tests:
        test_data = {
            'test': test,
            'question_count': test.question_count or 0,
            'total_marks': test.calculated_marks or test.total_marks or 0,
            'is_scheduled': test.start_at is not None or test.end_at is not None,
            'is_active': False,
            'is_expired': False,
        }
        
        # Check if test is currently active or expired
        now = timezone.now()
        if test.start_at or test.end_at:
            test_data['is_scheduled'] = True
            if test.start_at and now < test.start_at:
                test_data['status'] = 'upcoming'
            elif test.end_at and now > test.end_at:
                test_data['is_expired'] = True
                test_data['status'] = 'expired'
            else:
                test_data['is_active'] = True
                test_data['status'] = 'active'
        else:
            test_data['status'] = 'not_scheduled'
        
        if test_data['is_scheduled']:
            scheduled_tests.append(test_data)
        else:
            unscheduled_tests.append(test_data)
    
    return render(request, 'questions/paper_builder.html', {
        'scheduled_tests': scheduled_tests,
        'unscheduled_tests': unscheduled_tests,
        'total_tests': tests.count(),
    })


@login_required
def edit_paper(request, test_id: int):
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    # Admins can edit any test, teachers can only edit their own
    if request.user.user_type == 1:
        test = get_object_or_404(Test, id=test_id)
    else:
        test = get_object_or_404(Test, id=test_id, created_by=request.user)
    tqs = list(TestQuestion.objects.select_related('question').filter(test=test).order_by('order', 'id'))

    if request.method == 'POST':
        # Update test metadata
        test.title = (request.POST.get('test_title') or test.title).strip()
        test.subject = (request.POST.get('test_subject') or test.subject).strip()
        try:
            test.duration_minutes = int(request.POST.get('test_duration') or test.duration_minutes)
        except (ValueError, TypeError):
            # Keep existing duration if invalid value provided
            pass
        test.allow_immediate_review = request.POST.get('test_allow_review') == 'on'
        test.randomize_order = request.POST.get('test_randomize') == 'on'
        try:
            test.max_attempts = int(request.POST.get('test_max_attempts') or test.max_attempts)
        except (ValueError, TypeError):
            # Keep existing max_attempts if invalid value provided
            pass
        from django.utils.dateparse import parse_datetime
        st = request.POST.get('test_start_at', '').strip()
        en = request.POST.get('test_end_at', '').strip()
        old_start = test.start_at
        old_end = test.end_at
        if st:
            dt = parse_datetime(st)
            if dt:
                # Ensure timezone-aware
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                test.start_at = dt
            else:
                test.start_at = None
        if en:
            dt = parse_datetime(en)
            if dt:
                # Ensure timezone-aware
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                test.end_at = dt
            else:
                test.end_at = None
        test.save()
        
        # Create notifications for students if test was newly scheduled or rescheduled
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if (test.start_at != old_start or test.end_at != old_end) and (test.start_at or test.end_at):
            students = User.objects.filter(user_type=3, is_active=True)
            email_service = EmailService()
            
            # Prepare email tasks for async sending
            email_tasks = []
            
            for student in students:
                schedule_msg = f"The test '{test.title}' has been scheduled."
                if test.start_at:
                    schedule_msg += f" Starting: {test.start_at.strftime('%B %d, %Y at %I:%M %p')}"
                if test.end_at:
                    schedule_msg += f" Ending: {test.end_at.strftime('%B %d, %Y at %I:%M %p')}"
                
                # Create in-app notification (immediate)
                _create_notification(
                    user=student,
                    title=f"Test Scheduled: {test.title}",
                    message=schedule_msg,
                    notification_type='test_scheduled',
                    link=f'/questions/start/{test.id}/'
                )
                
                # Queue email for async sending
                if student.email:
                    email_tasks.append((
                        'send_test_published_notification',
                        (test, student),
                        {}
                    ))
            
            # Send all emails asynchronously in background
            if email_tasks:
                email_service.send_bulk_emails_async(email_tasks)
                messages.success(request, f'Test updated! {len(students)} students notified. Emails sending in background ({len(email_tasks)} queued).')
            else:
                messages.success(request, f'Test updated! {len(students)} students notified (in-app only).')
        else:
            messages.success(request, 'Paper updated successfully.')

        # Update existing question points/order/section or remove
        # Collect updates
        updated_items = []
        remove_ids = set()
        for tq in tqs:
            if request.POST.get(f'remove_{tq.id}') == 'on':
                remove_ids.add(tq.id)
                continue
            try:
                pts = int(request.POST.get(f'points_{tq.id}') or tq.points)
            except Exception:
                pts = tq.points
            try:
                ordv = int(request.POST.get(f'order_{tq.id}') or tq.order)
            except Exception:
                ordv = tq.order
            section = request.POST.get(f'section_{tq.id}', '').strip()
            updated_items.append((tq, pts, ordv, section))

        # Apply removals
        if remove_ids:
            TestQuestion.objects.filter(id__in=remove_ids, test=test).delete()

        # Apply updates (after removals)
        for tq, pts, ordv, section in updated_items:
            if tq.id in remove_ids:
                continue
            if tq.points != pts or tq.order != ordv or tq.section != section:
                tq.points = pts
                tq.order = ordv
                tq.section = section
                tq.save(update_fields=['points', 'order', 'section'])

        # Add new questions by id list
        add_ids = request.POST.getlist('add_question_ids')
        add_section = request.POST.get('add_section', '').strip()
        if add_ids:
            existing_qids = set(TestQuestion.objects.filter(test=test).values_list('question_id', flat=True))
            # Next order after current max
            next_order = (TestQuestion.objects.filter(test=test).aggregate(maxo=Max('order'))['maxo'] or 0) + 1
            for qid in add_ids:
                try:
                    qid_int = int(qid)
                except Exception:
                    continue
                if qid_int in existing_qids:
                    continue
                q = Question.objects.filter(id=qid_int, author=request.user).first()
                if not q:
                    continue
                TestQuestion.objects.create(test=test, question=q, order=next_order, points=1, section=add_section)
                next_order += 1

        return redirect('tests_list')

    # For additions, allow teacher to pick from own questions not already in this test
    existing_qids = set(tq.question_id for tq in tqs)
    addable = Question.objects.filter(author=request.user).exclude(id__in=existing_qids).order_by('-created_at')[:200]

    return render(request, 'questions/edit_paper.html', {
        'test': test,
        'tqs': tqs,
        'addable': addable,
    })


# ---------------- Student Test-Taking ---------------- #

@login_required
def available_tests(request):
    if request.user.user_type != 3:
        return redirect('questions_list')
    now = timezone.now()
    # Tests available if within window or if no window specified
    tests = Test.objects.all()
    tests = tests.filter(
        Q(start_at__isnull=True) | Q(start_at__lte=now),
        Q(end_at__isnull=True) | Q(end_at__gte=now)
    ).annotate(question_count=Count('questions')).filter(question_count__gt=0).order_by('-start_at', '-created_at')
    return render(request, 'questions/available_tests.html', { 'tests': tests })


def _get_or_create_attempt(test: Test, user):
    """Return an existing in-progress attempt or create a new one respecting max attempts."""
    attempts = TestAttempt.objects.select_related('test', 'student').filter(test=test, student=user).order_by('-attempt_number')
    latest = attempts.first()
    if latest and not latest.is_submitted:
        return latest
    # Determine max attempts (treat <=0 as unlimited)
    max_attempts = getattr(test, 'max_attempts', 1) or 1
    if max_attempts <= 0:
        max_attempts = 999999
    used = attempts.count()
    if used >= max_attempts:
        return None
    next_num = (latest.attempt_number + 1) if latest else 1
    return TestAttempt.objects.create(test=test, student=user, attempt_number=next_num, started_at=timezone.now())


@login_required
def start_test(request, test_id: int):
    if request.user.user_type != 3:
        return redirect('questions_list')
    test = get_object_or_404(Test, id=test_id)
    now = timezone.now()
    # Enforce start/end window
    # Make start_at timezone-aware if needed
    start_at = test.start_at
    if start_at and timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at)
    end_at = test.end_at
    if end_at and timezone.is_naive(end_at):
        end_at = timezone.make_aware(end_at)
    
    window_not_started = start_at and now < start_at
    window_ended = end_at and now > end_at
    
    if window_not_started or window_ended:
        return render(request, 'questions/take_test.html', { 
            'test': test, 
            'window_closed': True,
            'window_not_started': window_not_started,
            'window_ended': window_ended
        })

    attempt = _get_or_create_attempt(test, request.user)
    if attempt is None:
        return render(request, 'questions/take_test.html', { 'test': test, 'attempt_limit': True })
    # Build and persist question order on first entry
    if not attempt.question_order:
        q_ids = list(TestQuestion.objects.filter(test=test).order_by('order', 'id').values_list('question_id', flat=True))
        if not q_ids:
            # Test has no questions
            return render(request, 'questions/take_test.html', { 
                'test': test, 
                'no_questions': True,
                'error_message': 'This test has no questions yet. Please contact your teacher.'
            })
        if test.randomize_order:
            import random
            random.shuffle(q_ids)
        attempt.question_order = ",".join(str(qid) for qid in q_ids)
        attempt.started_at = timezone.now()
        attempt.save(update_fields=['question_order', 'started_at'])

    # Compute remaining time
    remaining_seconds = test.duration_minutes * 60
    elapsed = max(0, int((now - attempt.started_at).total_seconds()))
    remaining_seconds = max(0, remaining_seconds - elapsed)

    # Resolve ordered questions and points
    ordered_ids = [int(x) for x in attempt.question_order.split(',') if x.strip()]
    q_map = {q.id: q for q in Question.objects.filter(id__in=ordered_ids)}
    # points per question
    tq_map = {tq.question_id: tq.points for tq in TestQuestion.objects.filter(test=test, question_id__in=ordered_ids)}
    ordered_questions = [(q_map[qid], tq_map.get(qid, 1)) for qid in ordered_ids if qid in q_map]

    context = _get_student_context(request)
    context.update({
        'test': test,
        'attempt': attempt,
        'ordered_questions': ordered_questions,
        'remaining_seconds': remaining_seconds,
    })
    return render(request, 'questions/take_test.html', context)


@login_required
@transaction.atomic
def submit_test(request, attempt_id: int):
    if request.user.user_type != 3:
        return redirect('questions_list')
    attempt = get_object_or_404(TestAttempt.objects.select_related('test'), id=attempt_id, student=request.user)
    test = attempt.test
    now = timezone.now()

    if request.method != 'POST':
        return redirect('start_test', test_id=test.id)

    # Enforce duration and end window server-side
    hard_deadline = attempt.started_at + timedelta(minutes=test.duration_minutes)
    if test.end_at:
        hard_deadline = min(hard_deadline, test.end_at)

    total_score = 0
    ordered_ids = [int(x) for x in attempt.question_order.split(',') if x.strip()]
    # points per question
    points_map = {tq.question_id: tq.points for tq in TestQuestion.objects.filter(test=test, question_id__in=ordered_ids)}
    q_objs = {q.id: q for q in Question.objects.filter(id__in=ordered_ids)}

    for qid in ordered_ids:
        q = q_objs.get(qid)
        if not q:
            continue
        pts = int(points_map.get(qid, 1))
        qa, _ = TestAnswer.objects.get_or_create(attempt=attempt, question_id=qid)

        qtype = getattr(q, 'type', 'short')
        score = None
        # Capture per-question time
        try:
            qa.time_spent_seconds = max(0, int(request.POST.get(f"time_{qid}", "0") or 0))
        except Exception:
            qa.time_spent_seconds = qa.time_spent_seconds or 0
        # Collect and save answer by type
        if qtype == 'mcq_single':
            selected = request.POST.get(f"answer_{qid}", '').strip()
            qa.answer_text = selected
            try:
                sel_id = int(selected)
            except Exception:
                sel_id = None
            correct_ids = set(QuestionOption.objects.filter(question_id=qid, is_correct=True).values_list('id', flat=True))
            if sel_id and sel_id in correct_ids and len(correct_ids) == 1:
                score = pts
            else:
                score = 0
        elif qtype == 'mcq_multi':
            selected_list = request.POST.getlist(f"answer_{qid}")
            selected_ids = set()
            for s in selected_list:
                try:
                    selected_ids.add(int(s))
                except Exception:
                    continue
            qa.answer_text = ",".join(str(i) for i in sorted(selected_ids))
            correct_ids = set(QuestionOption.objects.filter(question_id=qid, is_correct=True).values_list('id', flat=True))
            # Partial credit: only if no wrong options selected; score proportionally to correct selected
            if selected_ids and selected_ids.issubset(set(QuestionOption.objects.filter(question_id=qid).values_list('id', flat=True))):
                if selected_ids.issubset(correct_ids) and len(correct_ids) > 0:
                    ratio = len(selected_ids) / len(correct_ids)
                    score = round(pts * ratio)
                else:
                    score = 0
            else:
                score = 0
        elif qtype == 'true_false':
            val = request.POST.get(f"answer_{qid}", '').strip().lower()
            qa.answer_text = val
            correct = False
            try:
                correct = bool(q.answer_key.get('correct'))
            except Exception:
                correct = False
            chosen = (val in ('true', '1', 'yes', 'y'))
            score = pts if chosen == correct else 0
        elif qtype == 'fill_in':
            text = (request.POST.get(f"answer_{qid}", '') or '').strip()
            qa.answer_text = text
            norm = text.casefold().strip()
            answers = []
            try:
                answers = [a.casefold().strip() for a in q.answer_key.get('answers', [])]
            except Exception:
                answers = []
            score = pts if norm and norm in answers else 0
        elif qtype == 'matching':
            # Expecting pairs via fields: answer_<qid>__key__<idx> and answer_<qid>__<idx>
            pairs = {}
            idx = 0
            while True:
                key_name = f"answer_{qid}__key__{idx}"
                left = request.POST.get(key_name)
                if left is None:
                    break
                right = request.POST.get(f"answer_{qid}__{idx}", '')
                pairs[left] = right
                idx += 1
            import json as _json
            qa.answer_text = _json.dumps(pairs)
            correct_pairs = {}
            try:
                correct_pairs = q.answer_key.get('pairs', {})
            except Exception:
                correct_pairs = {}
            # Partial credit: award proportional to number of correct mappings
            if correct_pairs:
                total = len(correct_pairs)
                correct = sum(1 for k, v in pairs.items() if k in correct_pairs and correct_pairs[k] == v)
                ratio = correct / total if total else 0
                score = round(pts * ratio)
            else:
                score = 0
        elif qtype == 'numerical':
            # Expect numeric answer with optional margin
            text = (request.POST.get(f"answer_{qid}", '') or '').strip()
            qa.answer_text = text
            try:
                val = float(text)
                key_val = float(q.answer_key.get('value'))
                margin = float(q.answer_key.get('margin', 0))
                score = pts if abs(val - key_val) <= margin else 0
            except Exception:
                score = 0
        else:
            # subjective: short/essay
            text = (request.POST.get(f"answer_{qid}", '') or '').strip()
            qa.answer_text = text
            score = None
        qa.score = score
        qa.save()

        if score is not None:
            total_score += int(score)

    # Mark submitted and store totals
    attempt.is_submitted = True
    attempt.submitted_at = min(now, hard_deadline)
    attempt.time_spent_seconds = max(0, int((attempt.submitted_at - attempt.started_at).total_seconds()))
    attempt.total_score = total_score
    attempt.save(update_fields=['is_submitted', 'submitted_at', 'time_spent_seconds', 'total_score'])

    return redirect('review_test', attempt_id=attempt.id)


@login_required
def review_test(request, attempt_id: int):
    attempt = get_object_or_404(TestAttempt.objects.select_related('test'), id=attempt_id)
    test = attempt.test
    # Access rules: student owner, admin, or teacher who owns the test/questions (optional expansion)
    if request.user.user_type == 3 and attempt.student_id != request.user.id:
        return redirect('questions_list')
    if request.user.user_type == 2 and test.created_by_id != request.user.id:
        return redirect('questions_list')

    # Review gating
    now = timezone.now()
    can_view = test.allow_immediate_review or (test.end_at and now >= test.end_at)
    if not can_view and request.user.user_type == 3:
        return render(request, 'questions/review_test.html', { 'attempt': attempt, 'locked': True })

    ordered_ids = [int(x) for x in attempt.question_order.split(',') if x.strip()]
    q_map = {q.id: q for q in Question.objects.filter(id__in=ordered_ids)}
    answers = {a.question_id: a for a in TestAnswer.objects.filter(attempt=attempt, question_id__in=ordered_ids)}
    tq_map = {tq.question_id: tq.points for tq in TestQuestion.objects.filter(test=test, question_id__in=ordered_ids)}
    rows = []
    for qid in ordered_ids:
        q = q_map.get(qid)
        if not q:
            continue
        pts = tq_map.get(qid, 1)
        ans = answers.get(qid)
        # Determine correctness if objective
        is_objective = getattr(q, 'type', 'short') in ('mcq_single','mcq_multi','true_false','fill_in','matching')
        correct = None
        if is_objective and ans is not None and ans.score is not None:
            correct = (ans.score == pts)
        rows.append({
            'question': q,
            'points': pts,
            'answer': ans,
            'is_objective': is_objective,
            'correct': correct,
        })
    return render(request, 'questions/review_test.html', { 'attempt': attempt, 'rows': rows })


# ---------------- Teacher Grading ---------------- #

@login_required
def attempts_list(request, test_id: int):
    # Teachers and admins only
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    # Admins can view any test's attempts, teachers can only view their own
    if request.user.user_type == 1:
        test = get_object_or_404(Test, id=test_id)
    else:
        test = get_object_or_404(Test, id=test_id, created_by=request.user)
    attempts = TestAttempt.objects.select_related('student').filter(test=test).order_by('-attempt_number', '-started_at')
    return render(request, 'questions/attempts_list.html', { 'test': test, 'attempts': attempts })


@login_required
@transaction.atomic
def grade_attempt(request, attempt_id: int):
    # Teachers only, and only their tests
    attempt = get_object_or_404(TestAttempt.objects.select_related('test', 'student'), id=attempt_id)
    if request.user.user_type != 2 or attempt.test.created_by_id != request.user.id:
        return redirect('questions_list')

    # Build rows with subjective questions
    ordered_ids = [int(x) for x in attempt.question_order.split(',') if x.strip()]
    q_map = {q.id: q for q in Question.objects.filter(id__in=ordered_ids)}
    answers = {a.question_id: a for a in TestAnswer.objects.filter(attempt=attempt, question_id__in=ordered_ids)}
    tq_map = {tq.question_id: tq.points for tq in TestQuestion.objects.filter(test=attempt.test, question_id__in=ordered_ids)}

    subjective_ids = [qid for qid in ordered_ids if getattr(q_map.get(qid), 'type', 'short') in ('short','essay')]
    rows = []
    for qid in subjective_ids:
        q = q_map.get(qid)
        if not q:
            continue
        rows.append({
            'question': q,
            'answer': answers.get(qid),
            'points': tq_map.get(qid, 1),
        })

    if request.method == 'POST':
        total = 0
        # Include objective scores already in DB
        for a in TestAnswer.objects.filter(attempt=attempt):
            if a.score is not None:
                total += int(a.score)
        # Update subjective scores from form
        for item in rows:
            q = item['question']
            pts = int(item['points'])
            field = f'score_{q.id}'
            try:
                val = request.POST.get(field)
                if val is None or val == '':
                    continue
                s = max(0, min(pts, int(val)))
            except Exception:
                s = 0
            ans = item['answer'] or TestAnswer.objects.create(attempt=attempt, question=q)
            ans.score = s
            if ans.answer_text is None:
                ans.answer_text = ''
            ans.save()
            total += s
        attempt.total_score = total
        attempt.save(update_fields=['total_score'])
        return redirect('attempts_list', test_id=attempt.test.id)

    return render(request, 'questions/grade_attempt.html', { 'attempt': attempt, 'rows': rows })


# ---------------- Materials (Uploads) ---------------- #

@login_required
def student_materials(request):
    # Students see public materials uploaded by any teacher
    mats = Resource.objects.filter(is_public=True).order_by('-created_at')
    subject = request.GET.get('subject')
    topic = request.GET.get('topic')
    if subject:
        mats = mats.filter(subject__iexact=subject)
    if topic:
        mats = mats.filter(topic__iexact=topic)
    
    context = _get_student_context(request)
    context['materials'] = mats
    return render(request, 'materials/student_materials.html', context)


@login_required
def teacher_materials(request):
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    
    mats = Resource.objects.filter(uploaded_by=request.user).order_by('-created_at')
    folder_id = request.GET.get('folder')
    subject = request.GET.get('subject')
    search = request.GET.get('q')
    
    # Apply filters
    if subject:
        mats = mats.filter(subject__iexact=subject)
    if search:
        mats = mats.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    # Apply folder filtering
    if folder_id:
        if folder_id == 'all':
            # Show all materials including those in folders
            pass
        else:
            # Show materials in specific folder
            mats = mats.filter(folders__id=folder_id)
    else:
        # Default: show only materials NOT in any folder
        mats = mats.filter(folders__isnull=True)
    
    # Get current folder for breadcrumb
    current_folder = None
    if folder_id and folder_id != 'all':
        try:
            current_folder = MaterialFolder.objects.get(id=folder_id, created_by=request.user)
        except MaterialFolder.DoesNotExist:
            pass
    
    # Get all folders for sidebar
    folders = MaterialFolder.objects.filter(
        created_by=request.user,
        parent=None,
        is_archived=False
    ).prefetch_related('subfolders', 'materials')
    
    return render(request, 'materials/teacher_materials.html', {
        'materials': mats,
        'current_folder': current_folder,
        'folders': folders
    })


@login_required
def upload_material(request):
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        subject = (request.POST.get('subject') or '').strip()
        topic = (request.POST.get('topic') or '').strip()
        description = (request.POST.get('description') or '').strip()
        is_public = request.POST.get('is_public') == 'on'
        f = request.FILES.get('file')
        if not title or not f:
            messages.error(request, 'Title and file are required.')
            return redirect('teacher_materials')
        resource = Resource.objects.create(
            title=title,
            description=description,
            subject=subject,
            topic=topic,
            file=f,
            is_public=is_public,
            uploaded_by=request.user,
        )
        
        # Notify students if material is public
        if is_public:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            students = User.objects.filter(user_type=3)
            for student in students:
                subject_info = f" ({subject})" if subject else ""
                _create_notification(
                    user=student,
                    title=f"New Material Available: {title}",
                    message=f"New study material '{title}'{subject_info} has been uploaded. Check it out in the Materials section.",
                    notification_type='material_uploaded',
                    link='/materials/student/'
                )
        
        messages.success(request, 'Material uploaded successfully.')
        return redirect('teacher_materials')
    # Fallback GET redirects to teacher list page
    return redirect('teacher_materials')


@login_required
def delete_material(request, resource_id: int):
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    res = get_object_or_404(Resource, id=resource_id, uploaded_by=request.user)
    if request.method == 'POST':
        res.file.delete(save=False)
        res.delete()
        messages.success(request, 'Material deleted.')
        return redirect('teacher_materials')
    return redirect('teacher_materials')


# ============ MATERIAL FOLDER MANAGEMENT ============ #

@login_required
def create_material_folder(request):
    """Create a new material folder."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            parent_id = data.get('parent_id')
            color = data.get('color', '#667eea')
            icon = data.get('icon', 'fas fa-folder')
            
            if not name:
                return JsonResponse({'success': False, 'error': 'Folder name is required'})
            
            parent = None
            if parent_id:
                try:
                    parent = MaterialFolder.objects.get(id=parent_id, created_by=request.user)
                except MaterialFolder.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Parent folder not found'})
            
            folder = MaterialFolder.objects.create(
                name=name,
                description=description,
                parent=parent,
                created_by=request.user,
                color=color,
                icon=icon
            )
            
            return JsonResponse({
                'success': True,
                'folder': {
                    'id': folder.id,
                    'name': folder.name,
                    'description': folder.description,
                    'color': folder.color,
                    'icon': folder.icon
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def edit_material_folder(request, folder_id):
    """Edit an existing material folder."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    folder = get_object_or_404(MaterialFolder, id=folder_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            folder.name = data.get('name', folder.name).strip()
            folder.description = data.get('description', folder.description).strip()
            folder.color = data.get('color', folder.color)
            folder.icon = data.get('icon', folder.icon)
            folder.save()
            
            return JsonResponse({
                'success': True,
                'folder': {
                    'id': folder.id,
                    'name': folder.name,
                    'description': folder.description,
                    'color': folder.color,
                    'icon': folder.icon
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def delete_material_folder(request, folder_id):
    """Delete a material folder."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    folder = get_object_or_404(MaterialFolder, id=folder_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            # Materials in this folder will become unassigned (many-to-many relationship)
            folder.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def move_materials_to_folder(request):
    """Move selected materials to a folder."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            material_ids = data.get('material_ids', [])
            folder_id = data.get('folder_id')
            
            if not material_ids:
                return JsonResponse({'success': False, 'error': 'No materials selected'})
            
            materials = Resource.objects.filter(id__in=material_ids, uploaded_by=request.user)
            
            if folder_id:
                folder = get_object_or_404(MaterialFolder, id=folder_id, created_by=request.user)
                for material in materials:
                    material.folders.add(folder)
            else:
                # Remove from all folders
                for material in materials:
                    material.folders.clear()
            
            return JsonResponse({'success': True, 'count': len(materials)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def get_material_folders_json(request):
    """Return material folders as JSON tree structure."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    def build_tree(parent=None):
        folders = MaterialFolder.objects.filter(created_by=request.user, parent=parent, is_archived=False)
        result = []
        for folder in folders:
            result.append({
                'id': folder.id,
                'name': folder.name,
                'description': folder.description,
                'color': folder.color,
                'icon': folder.icon,
                'material_count': folder.get_material_count(),
                'subfolders': build_tree(folder)
            })
        return result
    
    return JsonResponse({'folders': build_tree()})


# ============ COMPREHENSIVE STUDENT DASHBOARD ============ #

@login_required
def student_dashboard(request):
    """Comprehensive student dashboard with overview, exams, results, notifications."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    now = timezone.now()
    
    # Upcoming tests (within next 7 days)
    upcoming_tests = Test.objects.select_related('created_by').filter(
        Q(start_at__isnull=True) | Q(start_at__gte=now),
        Q(end_at__isnull=True) | Q(end_at__gte=now)
    ).order_by('start_at')[:5]
    
    # Recent results (last 5 submitted attempts)
    recent_attempts = TestAttempt.objects.select_related('test', 'test__created_by', 'student').filter(
        student=request.user, 
        is_submitted=True
    ).order_by('-submitted_at')[:5]
    
    # Unread notifications
    unread_notifications = Notification.objects.filter(
        user=request.user, 
        is_read=False
    )[:5]
    
    # Leaderboard rank (optimized - only calculate current student's stats)
    student_avg_score = TestAttempt.objects.filter(
        student=request.user,
        is_submitted=True, 
        total_score__isnull=False
    ).aggregate(avg_score=Avg('total_score'))['avg_score']
    
    # Only calculate rank if student has scores
    student_rank = None
    if student_avg_score is not None:
        # Count how many students have higher average
        student_rank = TestAttempt.objects.filter(
            is_submitted=True, 
            total_score__isnull=False
        ).values('student').annotate(
            avg_score=Avg('total_score')
        ).filter(avg_score__gt=student_avg_score).count() + 1
    
    # Activity summary
    total_tests_taken = TestAttempt.objects.filter(student=request.user, is_submitted=True).count()
    total_certificates = Certificate.objects.filter(student=request.user).count()
    
    # Total leaderboard entries (cached count)
    total_leaderboard_entries = TestAttempt.objects.filter(
        is_submitted=True, 
        total_score__isnull=False
    ).values('student').distinct().count()
    
    context = _get_student_context(request)
    context.update({
        'upcoming_tests': upcoming_tests,
        'recent_attempts': recent_attempts,
        'student_rank': student_rank,
        'student_avg_score': student_avg_score,
        'total_tests_taken': total_tests_taken,
        'total_certificates': total_certificates,
        'total_leaderboard_entries': total_leaderboard_entries,
    })
    
    return render(request, 'dashboards/student_dashboard.html', context)


@login_required
def student_all_exams(request):
    """Display all available exams for students."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    now = timezone.now()
    tests = Test.objects.filter(
        Q(start_at__isnull=True) | Q(start_at__lte=now),
        Q(end_at__isnull=True) | Q(end_at__gte=now)
    ).select_related('created_by').order_by('-created_at')
    
    # Attach attempt count directly to each test object
    for test in tests:
        test.attempt_count = TestAttempt.objects.filter(
            test=test, 
            student=request.user, 
            is_submitted=True
        ).count()
    
    context = _get_student_context(request)
    context.update({
        'tests': tests,
    })
    
    return render(request, 'questions/student_all_exams.html', context)


@login_required
def student_upcoming_exams(request):
    """Display upcoming exams."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    now = timezone.now()
    upcoming = Test.objects.select_related('created_by').filter(
        start_at__gte=now
    ).order_by('start_at')
    
    context = _get_student_context(request)
    context['tests'] = upcoming
    return render(request, 'questions/student_upcoming_exams.html', context)


@login_required
def student_attempted_exams(request):
    """Display exams student has attempted."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    attempts = TestAttempt.objects.select_related('test', 'test__created_by').filter(
        student=request.user, 
        is_submitted=True
    ).order_by('-submitted_at')
    
    context = _get_student_context(request)
    context['attempts'] = attempts
    return render(request, 'questions/student_attempted_exams.html', context)


@login_required
def student_pyqs(request):
    """Display previous year questions by subject."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    # Get all completed tests grouped by subject and year
    now = timezone.now()
    past_tests = Test.objects.select_related('created_by').filter(
        end_at__lt=now
    ).exclude(subject='').order_by('subject', '-created_at')
    
    # Group by subject
    subjects = {}
    for test in past_tests:
        subject = test.subject or 'General'
        year = test.created_at.year
        if subject not in subjects:
            subjects[subject] = []
        subjects[subject].append({
            'test': test,
            'year': year
        })
    
    context = _get_student_context(request)
    context['subjects'] = subjects
    return render(request, 'questions/student_pyqs.html', context)


@login_required
def student_results(request):
    """Display all student test results."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    attempts = TestAttempt.objects.select_related('test', 'test__created_by').filter(
        student=request.user, 
        is_submitted=True
    ).order_by('-submitted_at')
    
    context = _get_student_context(request)
    context['attempts'] = attempts
    return render(request, 'questions/student_results.html', context)


@login_required
def download_result_report(request, attempt_id):
    """Generate and download detailed result report as PDF."""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, student=request.user, is_submitted=True)
    test = attempt.test
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="result_report_{test.title}_{attempt.attempt_number}.pdf"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#667eea'), alignment=TA_CENTER, spaceAfter=30)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2d1b4e'), spaceAfter=12)
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("Test Result Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Summary Information Table
    summary_data = [
        ['Test Title:', test.title],
        ['Student:', request.user.username],
        ['Attempt Number:', str(attempt.attempt_number)],
        ['Started At:', attempt.started_at.strftime('%Y-%m-%d %H:%M:%S')],
        ['Submitted At:', attempt.submitted_at.strftime('%Y-%m-%d %H:%M:%S')],
        ['Total Score:', f"{attempt.total_score}%" if attempt.total_score else 'Not graded'],
        ['Time Spent:', f"{round(attempt.time_spent_seconds / 60, 2)} minutes"],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a1a')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Question Details Section
    elements.append(Paragraph("Question-wise Details", heading_style))
    elements.append(Spacer(1, 12))
    
    # Question Details Table
    ordered_ids = [int(x) for x in attempt.question_order.split(',') if x.strip()]
    questions = {q.id: q for q in Question.objects.filter(id__in=ordered_ids)}
    answers = {a.question_id: a for a in TestAnswer.objects.filter(attempt=attempt)}
    
    question_data = [['#', 'Question', 'Your Answer', 'Score', 'Time (s)']]
    
    for idx, qid in enumerate(ordered_ids, 1):
        q = questions.get(qid)
        if not q:
            continue
        ans = answers.get(qid)
        question_data.append([
            str(idx),
            Paragraph(q.question_text[:150] + ('...' if len(q.question_text) > 150 else ''), normal_style),
            Paragraph((ans.answer_text[:100] + ('...' if len(ans.answer_text) > 100 else '')) if ans else 'Not answered', normal_style),
            str(ans.score) if ans and ans.score is not None else 'N/A',
            str(ans.time_spent_seconds) if ans else '0'
        ])
    
    question_table = Table(question_data, colWidths=[0.4*inch, 2.8*inch, 2*inch, 0.6*inch, 0.6*inch])
    question_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1a1a1a')),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(question_table)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response


@login_required
def download_cumulative_report(request):
    """Generate cumulative performance report for all tests as PDF."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    attempts = TestAttempt.objects.select_related('test', 'test__created_by').filter(
        student=request.user, 
        is_submitted=True
    ).order_by('submitted_at')
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="cumulative_report_{request.user.username}.pdf"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#667eea'), alignment=TA_CENTER, spaceAfter=30)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2d1b4e'), spaceAfter=12)
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("Cumulative Performance Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Student Info
    info_data = [
        ['Student:', request.user.username],
        ['Generated On:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['Total Tests Taken:', str(attempts.count())],
    ]
    
    # Calculate average score
    graded_attempts = [a for a in attempts if a.total_score is not None]
    if graded_attempts:
        avg_score = sum(a.total_score for a in graded_attempts) / len(graded_attempts)
        info_data.append(['Average Score:', f"{avg_score:.2f}%"])
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a1a')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 30))
    
    # Test Results Section
    elements.append(Paragraph("Test Results", heading_style))
    elements.append(Spacer(1, 12))
    
    # Results Table
    results_data = [['#', 'Test Title', 'Attempt', 'Date', 'Score', 'Time (min)']]
    
    for idx, attempt in enumerate(attempts, 1):
        results_data.append([
            str(idx),
            Paragraph(attempt.test.title, normal_style),
            str(attempt.attempt_number),
            attempt.submitted_at.strftime('%Y-%m-%d %H:%M'),
            f"{attempt.total_score}%" if attempt.total_score is not None else 'Not graded',
            str(round(attempt.time_spent_seconds / 60, 2))
        ])
    
    results_table = Table(results_data, colWidths=[0.4*inch, 2.5*inch, 0.8*inch, 1.3*inch, 0.8*inch, 0.8*inch])
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1a1a1a')),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(results_table)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response


@login_required
def student_notifications(request):
    """Display all notifications for student."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
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
        return redirect('student_notifications')
    
    context = _get_student_context(request)
    context['notifications'] = notifications
    return render(request, 'questions/student_notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    # Redirect to notification link if exists, otherwise back to notifications page
    if notification.link:
        return redirect(notification.link)
    
    # Check for next parameter
    next_url = request.GET.get('next', '')
    if next_url:
        return redirect(next_url)
    
    return redirect('student_notifications')


@login_required
def view_leaderboard(request):
    """Display global leaderboard."""
    # Calculate average scores for all students
    leaderboard = TestAttempt.objects.select_related('student').filter(
        is_submitted=True, 
        total_score__isnull=False
    ).values('student__username', 'student__id').annotate(
        avg_score=Avg('total_score'),
        total_tests=Count('id'),
        total_score_sum=Sum('total_score')
    ).order_by('-avg_score')[:50]
    
    context = _get_student_context(request)
    context.update({
        'leaderboard': leaderboard,
        'current_user_id': request.user.id
    })
    return render(request, 'questions/leaderboard_view.html', context)


@login_required
def view_certificates(request):
    """Display all certificates earned by student."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    certificates = Certificate.objects.select_related('test', 'attempt', 'attempt__test', 'student').filter(student=request.user).order_by('-issued_date')
    context = _get_student_context(request)
    context['certificates'] = certificates
    return render(request, 'questions/student_certificates.html', context)


# ============ ENHANCED TEST TAKING WITH AUTO-SAVE ============ #

@login_required
def auto_save_answer(request):
    """Auto-save answer during test attempt (AJAX endpoint)."""
    if request.method != 'POST' or request.user.user_type != 3:
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    try:
        data = json.loads(request.body)
        attempt_id = data.get('attempt_id')
        question_id = data.get('question_id')
        answer_text = data.get('answer_text', '')
        time_spent = data.get('time_spent', 0)
        
        attempt = TestAttempt.objects.get(id=attempt_id, student=request.user, is_submitted=False)
        question = Question.objects.get(id=question_id)
        
        answer, created = TestAnswer.objects.get_or_create(
            attempt=attempt,
            question=question
        )
        answer.answer_text = answer_text
        answer.time_spent_seconds = time_spent
        answer.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def mark_question_for_review(request):
    """Mark a question for review (AJAX endpoint)."""
    if request.method != 'POST' or request.user.user_type != 3:
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    try:
        data = json.loads(request.body)
        attempt_id = data.get('attempt_id')
        question_id = data.get('question_id')
        mark = data.get('mark', True)
        
        attempt = TestAttempt.objects.get(id=attempt_id, student=request.user, is_submitted=False)
        question = Question.objects.get(id=question_id)
        
        if mark:
            MarkedQuestion.objects.get_or_create(attempt=attempt, question=question)
        else:
            MarkedQuestion.objects.filter(attempt=attempt, question=question).delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def send_test_reminder(request, test_id):
    """Send reminder notification (in-app + email) to students about a test."""
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    
    # Get test and verify ownership
    if request.user.user_type == 1:
        test = get_object_or_404(Test, id=test_id)
    else:
        test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    if request.method == 'POST':
        # Calculate hours remaining
        now = timezone.now()
        if test.end_at:
            hours_remaining = max(0, int((test.end_at - now).total_seconds() / 3600))
        else:
            hours_remaining = 24  # Default if no end time
        
        # Get all students
        from django.contrib.auth import get_user_model
        User = get_user_model()
        students = User.objects.filter(user_type=3, is_active=True)
        
        # Filter based on user selection
        send_to = request.POST.get('send_to', 'all')
        
        if send_to == 'not_attempted':
            # Only students who haven't attempted the test
            attempted_student_ids = TestAttempt.objects.filter(
                test=test,
                is_submitted=True
            ).values_list('student_id', flat=True)
            students = students.exclude(id__in=attempted_student_ids)
        
        # Send notifications
        email_service = EmailService()
        sent_count = 0
        email_tasks = []
        
        for student in students:
            # Create in-app notification (immediate)
            reminder_msg = f"Reminder: Test '{test.title}' is available."
            if test.end_at:
                reminder_msg += f" Deadline: {test.end_at.strftime('%B %d, %Y at %I:%M %p')}"
            if hours_remaining:
                reminder_msg += f" ({hours_remaining} hours remaining)"
            
            _create_notification(
                user=student,
                title=f"Reminder: {test.title}",
                message=reminder_msg,
                notification_type='test_reminder',
                link=f'/questions/start/{test.id}/'
            )
            sent_count += 1
            
            # Queue email for async sending
            if student.email:
                email_tasks.append((
                    'send_test_reminder',
                    (test, student, hours_remaining),
                    {}
                ))
        
        # Send all emails asynchronously in background
        if email_tasks:
            email_service.send_bulk_emails_async(email_tasks)
            messages.success(
                request, 
                f'Reminder sent successfully! In-app: {sent_count}, Emails sending in background ({len(email_tasks)} queued)'
            )
        else:
            messages.success(request, f'Reminder sent successfully! In-app notifications: {sent_count}')
        return redirect('tests_list')
    
    # GET request - show confirmation page
    now = timezone.now()
    
    # Get statistics
    from django.contrib.auth import get_user_model
    User = get_user_model()
    total_students = User.objects.filter(user_type=3, is_active=True).count()
    attempted_count = TestAttempt.objects.filter(test=test, is_submitted=True).values('student').distinct().count()
    not_attempted_count = total_students - attempted_count
    
    # Calculate hours remaining
    if test.end_at:
        hours_remaining = max(0, int((test.end_at - now).total_seconds() / 3600))
    else:
        hours_remaining = None
    
    context = {
        'test': test,
        'total_students': total_students,
        'attempted_count': attempted_count,
        'not_attempted_count': not_attempted_count,
        'hours_remaining': hours_remaining,
    }
    
    return render(request, 'questions/send_test_reminder.html', context)


# ============================================
# FOLDER MANAGEMENT VIEWS
# ============================================

@login_required
def folder_list(request):
    """Display all folders for current user in tree structure"""
    if request.user.user_type not in (1, 2):
        return redirect('questions_list')
    
    # Get root folders (no parent) for current user
    folders = QuestionFolder.objects.filter(
        created_by=request.user,
        parent=None,
        is_archived=False
    ).prefetch_related('subfolders', 'questions')
    
    return render(request, 'questions/folder_list.html', {'folders': folders})


@login_required
def create_folder(request):
    """Create a new question folder"""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            parent_id = data.get('parent_id')
            color = data.get('color', '#667eea')
            icon = data.get('icon', 'fas fa-folder')
            
            if not name:
                return JsonResponse({'success': False, 'error': 'Folder name is required'}, status=400)
            
            parent = None
            if parent_id:
                parent = get_object_or_404(QuestionFolder, id=parent_id, created_by=request.user)
            
            folder = QuestionFolder.objects.create(
                name=name,
                description=description,
                parent=parent,
                created_by=request.user,
                color=color,
                icon=icon
            )
            
            return JsonResponse({
                'success': True,
                'folder': {
                    'id': folder.id,
                    'name': folder.name,
                    'description': folder.description,
                    'color': folder.color,
                    'icon': folder.icon,
                    'full_path': folder.get_full_path()
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)


@login_required
def edit_folder(request, folder_id):
    """Edit an existing folder"""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    folder = get_object_or_404(QuestionFolder, id=folder_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            folder.name = data.get('name', folder.name).strip()
            folder.description = data.get('description', folder.description).strip()
            folder.color = data.get('color', folder.color)
            folder.icon = data.get('icon', folder.icon)
            
            if not folder.name:
                return JsonResponse({'success': False, 'error': 'Folder name is required'}, status=400)
            
            folder.save()
            
            return JsonResponse({
                'success': True,
                'folder': {
                    'id': folder.id,
                    'name': folder.name,
                    'description': folder.description,
                    'color': folder.color,
                    'icon': folder.icon,
                    'full_path': folder.get_full_path()
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({
        'folder': {
            'id': folder.id,
            'name': folder.name,
            'description': folder.description,
            'color': folder.color,
            'icon': folder.icon,
            'parent_id': folder.parent.id if folder.parent else None
        }
    })


@login_required
def delete_folder(request, folder_id):
    """Delete a folder (questions will not be deleted, only removed from folder)"""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    folder = get_object_or_404(QuestionFolder, id=folder_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            folder_name = folder.name
            # Questions are many-to-many, so they won't be deleted
            # Subfolders will be cascade deleted
            folder.delete()
            
            messages.success(request, f'Folder "{folder_name}" deleted successfully.')
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)


@login_required
def move_questions_to_folder(request):
    """Move multiple questions to a folder"""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            question_ids = data.get('question_ids', [])
            folder_id = data.get('folder_id')
            action = data.get('action', 'add')  # 'add' or 'remove'
            
            if not question_ids:
                return JsonResponse({'success': False, 'error': 'No questions selected'}, status=400)
            
            # Get questions that belong to current user
            questions = Question.objects.filter(
                id__in=question_ids,
                author=request.user
            )
            
            if action == 'remove':
                # Remove questions from folder
                if folder_id:
                    folder = get_object_or_404(QuestionFolder, id=folder_id, created_by=request.user)
                    for question in questions:
                        question.folders.remove(folder)
                    message = f'{questions.count()} question(s) removed from folder'
                else:
                    return JsonResponse({'success': False, 'error': 'Folder ID required for remove action'}, status=400)
            else:
                # Add questions to folder
                if folder_id:
                    folder = get_object_or_404(QuestionFolder, id=folder_id, created_by=request.user)
                    for question in questions:
                        question.folders.add(folder)
                    message = f'{questions.count()} question(s) added to folder "{folder.name}"'
                else:
                    return JsonResponse({'success': False, 'error': 'Folder ID required'}, status=400)
            
            return JsonResponse({'success': True, 'message': message})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)


@login_required
def get_folders_json(request):
    """API endpoint to get all folders for current user"""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    def build_tree(parent=None):
        folders = QuestionFolder.objects.filter(
            created_by=request.user,
            parent=parent,
            is_archived=False
        ).order_by('order', 'name')
        
        result = []
        for folder in folders:
            result.append({
                'id': folder.id,
                'name': folder.name,
                'description': folder.description,
                'color': folder.color,
                'icon': folder.icon,
                'question_count': folder.questions.count(),
                'subfolders': build_tree(folder)
            })
        return result
    
    return JsonResponse({'folders': build_tree()})

