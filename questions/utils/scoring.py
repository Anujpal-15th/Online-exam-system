"""
Automatic scoring utilities for different question types.

This module provides functions to automatically score student answers
for objective question types (MCQ, True/False, Fill-in-the-Blank, etc.).

Example Usage:
    from questions.utils.scoring import score_answer
    
    score = score_answer(question, student_answer)
    # Returns (score, max_points, is_correct, feedback)
"""

from typing import Tuple, Optional
import re
from difflib import SequenceMatcher

from questions.models import Question, QuestionOption


def score_answer(
    question: Question,
    student_answer: str,
    max_points: int = 1
) -> Tuple[Optional[int], int, bool, str]:
    """
    Automatically score a student's answer based on question type.
    
    Args:
        question: Question object
        student_answer: Student's submitted answer
        max_points: Maximum points for this question
        
    Returns:
        tuple: (score, max_points, is_correct, feedback_message)
        score will be None for subjective questions requiring manual grading
    """
    question_type = question.type
    
    # Route to appropriate scoring function
    if question_type == 'mcq_single':
        return _score_mcq_single(question, student_answer, max_points)
    elif question_type == 'mcq_multi':
        return _score_mcq_multi(question, student_answer, max_points)
    elif question_type == 'true_false':
        return _score_true_false(question, student_answer, max_points)
    elif question_type == 'fill_in':
        return _score_fill_in(question, student_answer, max_points)
    elif question_type == 'numerical':
        return _score_numerical(question, student_answer, max_points)
    elif question_type in ('short', 'essay', 'matching'):
        # Subjective - requires manual grading
        return (None, max_points, False, "Requires manual grading")
    else:
        return (None, max_points, False, "Unknown question type")


def _score_mcq_single(
    question: Question,
    student_answer: str,
    max_points: int
) -> Tuple[int, int, bool, str]:
    """Score single-choice MCQ questions."""
    try:
        selected_option_id = int(student_answer)
        correct_option = question.options.filter(is_correct=True).first()
        
        if not correct_option:
            return (0, max_points, False, "No correct answer defined")
        
        is_correct = (selected_option_id == correct_option.id)
        score = max_points if is_correct else 0
        
        feedback = "Correct!" if is_correct else f"Incorrect. Correct answer: {correct_option.text}"
        return (score, max_points, is_correct, feedback)
        
    except (ValueError, TypeError):
        return (0, max_points, False, "Invalid answer format")


def _score_mcq_multi(
    question: Question,
    student_answer: str,
    max_points: int
) -> Tuple[int, int, bool, str]:
    """Score multiple-choice MCQ questions (can select multiple)."""
    try:
        # Parse comma-separated option IDs
        selected_ids = set()
        if student_answer:
            selected_ids = {int(id.strip()) for id in student_answer.split(',')}
        
        correct_option_ids = set(
            question.options.filter(is_correct=True).values_list('id', flat=True)
        )
        
        if not correct_option_ids:
            return (0, max_points, False, "No correct answers defined")
        
        # Calculate partial credit
        correct_selections = selected_ids & correct_option_ids
        incorrect_selections = selected_ids - correct_option_ids
        missed_selections = correct_option_ids - selected_ids
        
        # Partial scoring: (+1 for each correct, -0.5 for each wrong)
        score = len(correct_selections) - (0.5 * len(incorrect_selections))
        score = max(0, score)  # Don't go negative
        score = int((score / len(correct_option_ids)) * max_points)
        
        is_correct = (selected_ids == correct_option_ids)
        
        if is_correct:
            feedback = "Correct!"
        else:
            feedback = f"Partially correct. Score: {score}/{max_points}"
            
        return (score, max_points, is_correct, feedback)
        
    except (ValueError, TypeError):
        return (0, max_points, False, "Invalid answer format")


def _score_true_false(
    question: Question,
    student_answer: str,
    max_points: int
) -> Tuple[int, int, bool, str]:
    """Score True/False questions."""
    # Normalize answer
    answer = student_answer.lower().strip()
    
    # Get correct answer from answer_key
    answer_key = question.answer_key or {}
    correct_answer = answer_key.get('correct', True)  # Default to True
    
    # Convert to boolean
    if answer in ('true', 't', '1', 'yes', 'y'):
        student_bool = True
    elif answer in ('false', 'f', '0', 'no', 'n'):
        student_bool = False
    else:
        return (0, max_points, False, "Invalid answer format. Please enter True or False")
    
    is_correct = (student_bool == correct_answer)
    score = max_points if is_correct else 0
    
    feedback = "Correct!" if is_correct else f"Incorrect. Correct answer: {correct_answer}"
    return (score, max_points, is_correct, feedback)


def _score_fill_in(
    question: Question,
    student_answer: str,
    max_points: int
) -> Tuple[int, int, bool, str]:
    """Score fill-in-the-blank questions with fuzzy matching."""
    answer_key = question.answer_key or {}
    accepted_answers = answer_key.get('answers', [])
    
    if not accepted_answers:
        return (None, max_points, False, "No accepted answers defined")
    
    # Normalize student answer
    student_normalized = normalize_text(student_answer)
    
    # Check against all accepted answers with fuzzy matching
    best_match_ratio = 0.0
    for accepted in accepted_answers:
        accepted_normalized = normalize_text(str(accepted))
        
        # Use sequence matcher for fuzzy comparison
        ratio = SequenceMatcher(None, student_normalized, accepted_normalized).ratio()
        best_match_ratio = max(best_match_ratio, ratio)
    
    # Accept if 85% or higher match
    is_correct = (best_match_ratio >= 0.85)
    
    if is_correct:
        score = max_points
        feedback = "Correct!"
    elif best_match_ratio >= 0.6:
        # Partial credit for close answers
        score = int(max_points * 0.5)
        feedback = f"Partially correct. Accepted answers: {', '.join(map(str, accepted_answers))}"
    else:
        score = 0
        feedback = f"Incorrect. Accepted answers: {', '.join(map(str, accepted_answers))}"
    
    return (score, max_points, is_correct, feedback)


def _score_numerical(
    question: Question,
    student_answer: str,
    max_points: int
) -> Tuple[int, int, bool, str]:
    """Score numerical questions with tolerance."""
    answer_key = question.answer_key or {}
    correct_value = answer_key.get('value')
    tolerance = answer_key.get('tolerance', 0.01)  # Default 1% tolerance
    
    if correct_value is None:
        return (None, max_points, False, "No correct answer defined")
    
    try:
        # Parse student answer
        student_value = float(student_answer.strip())
        correct_value = float(correct_value)
        
        # Calculate absolute difference
        difference = abs(student_value - correct_value)
        tolerance_value = abs(correct_value * tolerance)
        
        is_correct = (difference <= tolerance_value)
        score = max_points if is_correct else 0
        
        feedback = "Correct!" if is_correct else f"Incorrect. Correct answer: {correct_value}"
        return (score, max_points, is_correct, feedback)
        
    except (ValueError, TypeError):
        return (0, max_points, False, "Invalid numerical format")


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison (case-insensitive, no extra spaces).
    
    Args:
        text: Input text
        
    Returns:
        Normalized lowercase text with single spaces
    """
    # Convert to lowercase
    text = text.lower().strip()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common punctuation that doesn't affect meaning
    text = re.sub(r'[.,;:!?"\']', '', text)
    
    return text


def calculate_percentage(score: float, max_score: float) -> float:
    """
    Calculate percentage score.
    
    Args:
        score: Points earned
        max_score: Maximum possible points
        
    Returns:
        Percentage (0-100)
    """
    if max_score == 0:
        return 0.0
    return round((score / max_score) * 100, 2)


def get_grade_letter(percentage: float) -> str:
    """
    Convert percentage to letter grade.
    
    Args:
        percentage: Score percentage (0-100)
        
    Returns:
        Letter grade (A+, A, B+, etc.)
    """
    if percentage >= 95:
        return "A+"
    elif percentage >= 90:
        return "A"
    elif percentage >= 85:
        return "B+"
    elif percentage >= 80:
        return "B"
    elif percentage >= 75:
        return "C+"
    elif percentage >= 70:
        return "C"
    elif percentage >= 65:
        return "D+"
    elif percentage >= 60:
        return "D"
    else:
        return "F"
