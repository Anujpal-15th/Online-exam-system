"""
File upload and parsing utilities for questions.

This module handles various file formats (CSV, JSON, TXT) and converts
them into Question objects with proper validation and error handling.

Supported Formats:
    - CSV: Comma-separated values with headers
    - JSON: Single object or array of question objects
    - TXT: Text file containing JSON data

Example Usage:
    from questions.utils.file_handlers import parse_question_file
    
    questions = parse_question_file(uploaded_file, author=request.user)
    # Returns list of created Question objects
"""

import json
import csv
from io import TextIOWrapper
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from django.core.files.uploadedfile import UploadedFile
from django.contrib.auth import get_user_model

from questions.models import Question, QuestionOption

if TYPE_CHECKING:
    from accounts.models import CustomUser as User
else:
    User = get_user_model()


class QuestionFileParser:
    """
    Handles parsing of question files in various formats.
    
    Attributes:
        supported_formats (tuple): File extensions that can be parsed
    """
    
    supported_formats = ('.json', '.txt', '.csv')
    
    @classmethod
    def parse_file(cls, uploaded_file: UploadedFile, author: User) -> tuple[int, List[str]]:
        """
        Parse an uploaded file and create questions.
        
        Args:
            uploaded_file: Django UploadedFile object
            author: User who is creating the questions
            
        Returns:
            tuple: (number_created, list_of_errors)
            
        Raises:
            ValueError: If file format is not supported
        """
        filename = (uploaded_file.name or '').lower()
        
        if not any(filename.endswith(fmt) for fmt in cls.supported_formats):
            raise ValueError(
                f"Unsupported file format. Please upload {', '.join(cls.supported_formats)}"
            )
        
        created_count = 0
        errors = []
        
        try:
            if filename.endswith('.json') or filename.endswith('.txt'):
                created_count, errors = cls._parse_json_file(uploaded_file, author)
            elif filename.endswith('.csv'):
                created_count, errors = cls._parse_csv_file(uploaded_file, author)
        except Exception as e:
            errors.append(f"Failed to process file: {str(e)}")
            
        return created_count, errors
    
    @classmethod
    def _parse_json_file(cls, uploaded_file: UploadedFile, author: User) -> tuple[int, List[str]]:
        """Parse JSON file containing question data."""
        text = uploaded_file.read().decode('utf-8', errors='ignore')
        data = json.loads(text)
        
        # Convert single object to list
        if isinstance(data, dict):
            data = [data]
            
        created_count = 0
        errors = []
        
        for idx, item in enumerate(data, 1):
            try:
                question = create_question_from_dict(item, author)
                if question:
                    created_count += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                
        return created_count, errors
    
    @classmethod
    def _parse_csv_file(cls, uploaded_file: UploadedFile, author: User) -> tuple[int, List[str]]:
        """Parse CSV file containing question data."""
        file_wrapper = TextIOWrapper(uploaded_file.file, encoding='utf-8', errors='ignore')
        reader = csv.DictReader(file_wrapper)
        
        created_count = 0
        errors = []
        
        for idx, row in enumerate(reader, 2):  # Start from 2 (1 is header)
            try:
                question = create_question_from_dict(row, author)
                if question:
                    created_count += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                
        return created_count, errors


def create_question_from_dict(data: Dict[str, Any], author: User) -> Optional[Question]:
    """
    Create a Question object from a dictionary.
    
    Args:
        data: Dictionary containing question fields
        author: User creating the question
        
    Returns:
        Created Question object or None if validation fails
        
    Expected Keys:
        - question_text (required)
        - type/question_type (default: 'short')
        - subject (optional)
        - topic (optional)
        - difficulty (default: 'easy')
        - answer_key (optional, JSON)
        - rubric_text (optional)
        - options (optional, list of dicts with 'text' and 'is_correct')
    """
    # Extract and clean data
    question_text = str(data.get('question_text', data.get('question', ''))).strip()
    
    if not question_text:
        raise ValueError("question_text is required")
    
    # Map common type names to internal types
    type_mapping = {
        'multiple_choice': 'mcq_single',
        'mcq': 'mcq_single',
        'true_false': 'true_false',
        'tf': 'true_false',
        'short_answer': 'short',
        'short': 'short',
        'essay': 'essay',
        'fill_blanks': 'fill_in',
        'fill_in': 'fill_in',
        'matching': 'matching',
        'numerical': 'numerical',
    }
    
    raw_type = str(data.get('type', data.get('question_type', 'short'))).lower().strip()
    question_type = type_mapping.get(raw_type, 'short')
    
    # Parse answer key if it's a string
    answer_key = data.get('answer_key', {})
    if isinstance(answer_key, str):
        try:
            answer_key = json.loads(answer_key)
        except json.JSONDecodeError:
            answer_key = {}
    
    # Create the question
    question = Question.objects.create(
        question_text=question_text,
        type=question_type,
        subject=str(data.get('subject', '')).strip(),
        topic=str(data.get('topic', '')).strip(),
        difficulty=str(data.get('difficulty', 'easy')).lower().strip(),
        author=author,
        answer_key=answer_key,
        rubric_text=str(data.get('rubric_text', data.get('rubric', ''))).strip(),
    )
    
    # Handle MCQ options
    if question_type in ('mcq_single', 'mcq_multi'):
        options_data = data.get('options', [])
        
        # Parse options from various formats
        if isinstance(options_data, str):
            try:
                options_data = json.loads(options_data)
            except json.JSONDecodeError:
                options_data = []
        
        if options_data and isinstance(options_data, list):
            for idx, opt in enumerate(options_data):
                if isinstance(opt, dict):
                    QuestionOption.objects.create(
                        question=question,
                        text=str(opt.get('text', '')).strip(),
                        is_correct=bool(opt.get('is_correct', False)),
                        order=idx
                    )
                elif isinstance(opt, str):
                    # Simple string format, mark first as correct by default
                    QuestionOption.objects.create(
                        question=question,
                        text=opt.strip(),
                        is_correct=(idx == 0),
                        order=idx
                    )
    
    return question


def validate_question_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate question data before creating a question.
    
    Args:
        data: Dictionary containing question fields
        
    Returns:
        tuple: (is_valid, list_of_error_messages)
    """
    errors = []
    
    # Required fields
    if not data.get('question_text') and not data.get('question'):
        errors.append("question_text is required")
    
    # Validate difficulty
    valid_difficulties = ('easy', 'medium', 'hard')
    difficulty = str(data.get('difficulty', 'easy')).lower()
    if difficulty and difficulty not in valid_difficulties:
        errors.append(f"difficulty must be one of: {', '.join(valid_difficulties)}")
    
    # Validate question type
    valid_types = (
        'mcq_single', 'mcq_multi', 'true_false', 'fill_in',
        'matching', 'short', 'essay', 'numerical'
    )
    q_type = str(data.get('type', data.get('question_type', 'short'))).lower()
    if q_type and q_type not in valid_types:
        errors.append(f"type must be one of: {', '.join(valid_types)}")
    
    return len(errors) == 0, errors
