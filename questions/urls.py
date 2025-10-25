from django.urls import path
from .views import (
    questions_list,
    add_question,
    edit_question,
    delete_question,
    take_question,
    submissions_list,
    grade_submission,
    leaderboard,
    export_performance_csv,
    student_submissions,
    mock_test,
)

urlpatterns = [
    path('', questions_list, name='questions_list'),
    path('add/', add_question, name='add_question'),
    path('edit/<int:id>/', edit_question, name='edit_question'),
    path('delete/<int:id>/', delete_question, name='delete_question'),
    path('take/<int:id>/', take_question, name='take_question'),
    path('submissions/', submissions_list, name='submissions_list'),
    path('grade/<int:id>/', grade_submission, name='grade_submission'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('export/performance.csv', export_performance_csv, name='export_performance_csv'),
    path('me/submissions/', student_submissions, name='student_submissions'),
    path('mock-test/', mock_test, name='mock_test'),
]
