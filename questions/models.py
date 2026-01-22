from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class Tag(models.Model):
    """
    Tags for flexible question categorization and organization.
    
    Tags provide a way to label questions with custom attributes beyond
    folders and subjects (e.g., 'important', 'previous-year', 'tricky',
    'conceptual', 'numerical', 'theory').
    
    Attributes:
        name: Tag name (e.g., "Important", "PYQ 2023")
        slug: URL-friendly version of name
        color: Display color for the tag badge
        description: Optional description of tag purpose
        created_by: Teacher who created the tag
        is_global: Whether tag is available to all teachers
    """
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    color = models.CharField(
        max_length=7,
        default='#3b82f6',
        help_text='Hex color code for tag badge (e.g., #3b82f6)'
    )
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tags'
    )
    is_global = models.BooleanField(
        default=False,
        help_text='Global tags are available to all teachers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['created_by', 'name']),
            models.Index(fields=['is_global']),
        ]
        unique_together = [['created_by', 'name']]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Tag.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class QuestionFolder(models.Model):
    """
    Hierarchical folder structure for organizing questions.
    
    Teachers can create custom folders to organize their question bank,
    with support for nested folders (parent-child relationships).
    This makes it easier to manage large question collections.
    
    Attributes:
        name: Folder name (e.g., "Midterm 2024", "Data Structures")
        description: Optional detailed description
        parent: Parent folder for nested organization
        created_by: Teacher who created the folder
        color: Optional color code for visual distinction
        icon: Optional icon class (e.g., "fas fa-folder")
        is_archived: Whether folder is archived
        order: Display order among sibling folders
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='question_folders'
    )
    color = models.CharField(
        max_length=7,
        blank=True,
        default='#667eea',
        help_text='Hex color code (e.g., #667eea)'
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='fas fa-folder',
        help_text='FontAwesome icon class'
    )
    is_archived = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['created_by', 'parent']),
            models.Index(fields=['is_archived']),
        ]
        unique_together = [['created_by', 'parent', 'name']]
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def get_full_path(self):
        """Return full folder path (e.g., 'CS > Algorithms > Sorting')"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return ' > '.join(path)
    
    def get_question_count(self):
        """Return total number of questions in this folder and subfolders"""
        count = self.questions.count()
        for subfolder in self.subfolders.all():
            count += subfolder.get_question_count()
        return count


class Subject(models.Model):
    """
    Academic subjects for organizing questions, tests, and resources.
    
    Subjects can be predefined (e.g., Data Structures, Algorithms) or
    custom-added by teachers. Each subject has a category for grouping
    (e.g., Computer Science, Mathematics, Physics).
    
    Attributes:
        name: Subject name (e.g., "Data Structures")
        code: Optional subject code (e.g., "CS101")
        category: Subject category for grouping
        description: Detailed description
        is_active: Whether subject is active and available
        created_by: Teacher who added the subject (if custom)
    """
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, blank=True)
    category = models.CharField(
        max_length=100, 
        blank=True,
        help_text='E.g., Computer Science, Mathematics, Physics'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_subjects'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        if self.code:
            return f"{self.code} - {self.name}"
        return self.name


class Question(models.Model):
    """
    Represents an exam question.
    
    Supports multiple question types including MCQ, True/False, Fill-in-the-blank,
    Short answer, Essay, and Numerical questions. Each question can be categorized
    by subject, topic, and difficulty level.
    
    Attributes:
        question_text: The question content
        type: Question type (MCQ, True/False, etc.)
        subject: Academic subject (Math, Science, etc.)
        topic: Specific topic within subject
        difficulty: Question difficulty (easy, medium, hard)
        author: Teacher who created the question
        answer_key: JSON field containing correct answers/solution
        rubric_text: Grading rubric for subjective questions
    """
    
    DIFFICULTY_CHOICES = (
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    )

    QUESTION_TYPE_CHOICES = (
        ("mcq_single", "MCQ (Single Answer)"),
        ("mcq_multi", "MCQ (Multiple Answers)"),
        ("true_false", "True / False"),
        ("fill_in", "Fill in the Blank"),
        ("matching", "Matching"),
        ("short", "Short Answer"),
        ("essay", "Essay"),
        ("numerical", "Numerical"),
    )

    question_text = models.TextField()
    type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default="short")
    subject = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=100, blank=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="easy")
    marks = models.PositiveIntegerField(default=1, help_text="Points/marks for this question")
    folders = models.ManyToManyField(
        QuestionFolder,
        blank=True,
        related_name='questions',
        help_text='Folders this question belongs to'
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='questions',
        help_text='Tags for categorizing this question'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_questions",
    )
    # Generic answer key for objective types (JSON):
    # true_false: {"correct": true}
    # fill_in: {"answers": ["newton's second law", "f=ma"]}
    # matching: {"pairs": {"left1": "rightA", ...}}
    answer_key = models.JSONField(default=dict, blank=True)
    # Optional rubric for subjective grading
    rubric_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject', 'topic']),
            models.Index(fields=['author', '-created_at']),
        ]
    
    def __str__(self):
        preview = self.question_text[:50] + "..." if len(self.question_text) > 50 else self.question_text
        return f"{self.get_type_display()} - {preview}"


class QuestionOption(models.Model):
    """
    Multiple choice options for MCQ questions.
    
    Each option belongs to a question and can be marked as correct.
    Options are ordered for consistent display.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
    
    def __str__(self):
        correct = "✓" if self.is_correct else "✗"
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"{correct} {preview}"


class Submission(models.Model):
    """
    Student submission for individual questions (legacy model).
    
    Note: This is primarily used for standalone question submissions.
    Test-based submissions use TestAnswer model instead.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    answer_text = models.TextField()
    graded = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        status = "Graded" if self.graded else "Pending"
        return f"{self.student.username} - Q{self.question.id} ({status})"


# Test, TestQuestion, TestAttempt, TestAnswer models moved to exams app


class Resource(models.Model):
    """
    Study materials and resources uploaded by teachers.
    
    Teachers can upload documents, PDFs, videos, and other educational
    materials that students can access. Resources can be categorized
    by subject and topic.
    
    Attributes:
        title: Resource name
        description: Detailed description of the resource
        subject: Academic subject
        topic: Specific topic
        file: Uploaded file
        is_public: Whether visible to all students
        uploaded_by: Teacher who uploaded the resource
    """
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to='materials/')
    is_public = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_resources')
    created_at = models.DateTimeField(auto_now_add=True)
    folders = models.ManyToManyField('MaterialFolder', related_name='materials', blank=True)

    class Meta:
        ordering = ['-created_at', 'id']
        indexes = [
            models.Index(fields=['subject', 'topic']),
        ]

    def __str__(self) -> str:
        return self.title


class MaterialFolder(models.Model):
    """
    Hierarchical folder structure for organizing study materials.
    
    Similar to QuestionFolder, allows teachers to organize materials
    into folders and subfolders for better categorization.
    
    Attributes:
        name: Folder name
        description: Optional description
        parent: Parent folder for nested structure
        created_by: Teacher who created the folder
        created_at: Creation timestamp
        color: UI color for folder display
        icon: Icon name for folder display
        is_archived: Whether folder is archived
        order: Display order
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='material_folders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    color = models.CharField(max_length=7, default='#667eea')
    icon = models.CharField(max_length=50, default='fas fa-folder')
    is_archived = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['created_by', 'parent']),
            models.Index(fields=['is_archived']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_full_path(self):
        """Return full path from root to this folder."""
        if self.parent:
            return f"{self.parent.get_full_path()} / {self.name}"
        return self.name
    
    def get_material_count(self):
        """Return count of materials in this folder."""
        return self.materials.count()


class Notification(models.Model):
    """
    System notifications sent to users.
    
    Notifications inform users about test schedules, result publications,
    new materials, and other important updates. Each notification has a type
    and can optionally link to relevant content.
    
    Attributes:
        user: Recipient of the notification
        title: Notification title
        message: Detailed notification content
        notification_type: Category (test_scheduled, result_published, etc.)
        is_read: Whether the user has viewed the notification
        link: Optional URL to relevant content
        created_at: When notification was created
    """
    NOTIFICATION_TYPES = (
        ('test_scheduled', 'Test Scheduled'),
        ('test_reminder', 'Test Reminder'),
        ('result_published', 'Result Published'),
        ('material_uploaded', 'Material Uploaded'),
        ('general', 'General'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='general')
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"{self.title} - {self.user.username} ({status})"


# Certificate model moved to exams app
# SupportTicket model removed - using HelpRequest in accounts app instead


# MarkedQuestion model moved to exams app
