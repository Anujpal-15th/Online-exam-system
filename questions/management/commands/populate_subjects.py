"""
Management command to populate initial subjects
"""
from django.core.management.base import BaseCommand
from questions.models import Subject


class Command(BaseCommand):
    help = 'Populate initial subjects for the exam system'

    def handle(self, *args, **options):
        subjects_data = [
            # Core Computer Science Subjects
            {'name': 'Data Structures', 'category': 'Computer Science', 'code': 'CS101'},
            {'name': 'Algorithms', 'category': 'Computer Science', 'code': 'CS102'},
            {'name': 'Database Management Systems', 'category': 'Computer Science', 'code': 'CS201'},
            {'name': 'Operating Systems', 'category': 'Computer Science', 'code': 'CS202'},
            {'name': 'Computer Networks', 'category': 'Computer Science', 'code': 'CS301'},
            {'name': 'Software Engineering', 'category': 'Computer Science', 'code': 'CS302'},
            {'name': 'Computer Architecture', 'category': 'Computer Science', 'code': 'CS303'},
            {'name': 'Theory of Computation', 'category': 'Computer Science', 'code': 'CS401'},
            {'name': 'Compiler Design', 'category': 'Computer Science', 'code': 'CS402'},
            {'name': 'Artificial Intelligence', 'category': 'Computer Science', 'code': 'CS501'},
            {'name': 'Machine Learning', 'category': 'Computer Science', 'code': 'CS502'},
            {'name': 'Web Development', 'category': 'Computer Science', 'code': 'CS503'},
            {'name': 'Mobile Computing', 'category': 'Computer Science', 'code': 'CS504'},
            {'name': 'Cloud Computing', 'category': 'Computer Science', 'code': 'CS505'},
            {'name': 'Cybersecurity', 'category': 'Computer Science', 'code': 'CS506'},
            {'name': 'Data Mining', 'category': 'Computer Science', 'code': 'CS507'},
            {'name': 'Big Data Analytics', 'category': 'Computer Science', 'code': 'CS508'},
            {'name': 'Internet of Things', 'category': 'Computer Science', 'code': 'CS509'},
            {'name': 'Computer Graphics', 'category': 'Computer Science', 'code': 'CS510'},
            {'name': 'Information Security', 'category': 'Computer Science', 'code': 'CS511'},
            
            # B.Tech Core Subjects
            {'name': 'Engineering Mathematics I', 'category': 'Mathematics', 'code': 'MATH101'},
            {'name': 'Engineering Mathematics II', 'category': 'Mathematics', 'code': 'MATH102'},
            {'name': 'Engineering Mathematics III', 'category': 'Mathematics', 'code': 'MATH201'},
            {'name': 'Discrete Mathematics', 'category': 'Mathematics', 'code': 'MATH202'},
            {'name': 'Probability and Statistics', 'category': 'Mathematics', 'code': 'MATH301'},
            {'name': 'Numerical Methods', 'category': 'Mathematics', 'code': 'MATH302'},
            
            {'name': 'Engineering Physics', 'category': 'Physics', 'code': 'PHY101'},
            {'name': 'Engineering Chemistry', 'category': 'Chemistry', 'code': 'CHEM101'},
            
            {'name': 'Digital Electronics', 'category': 'Electronics', 'code': 'EC101'},
            {'name': 'Electronic Devices and Circuits', 'category': 'Electronics', 'code': 'EC102'},
            {'name': 'Microprocessors', 'category': 'Electronics', 'code': 'EC201'},
            {'name': 'Basic Electronics Engineering', 'category': 'Electronics', 'code': 'EC301'},
            {'name': 'Digital Logic Design', 'category': 'Electronics', 'code': 'EC302'},
            
            {'name': 'C Programming', 'category': 'Programming', 'code': 'PROG101'},
            {'name': 'C++ Programming', 'category': 'Programming', 'code': 'PROG102'},
            {'name': 'Java Programming', 'category': 'Programming', 'code': 'PROG201'},
            {'name': 'Python Programming', 'category': 'Programming', 'code': 'PROG202'},
            {'name': 'Object Oriented Programming', 'category': 'Programming', 'code': 'PROG203'},
            
            {'name': 'Communication Skills', 'category': 'Humanities', 'code': 'HUM101'},
            {'name': 'Professional Ethics', 'category': 'Humanities', 'code': 'HUM201'},
            {'name': 'Technical Writing', 'category': 'Humanities', 'code': 'HUM202'},
            {'name': 'English', 'category': 'Humanities', 'code': 'HUM203'},
            
            {'name': 'Engineering Graphics', 'category': 'Engineering', 'code': 'ENG101'},
            {'name': 'Engineering Mechanics', 'category': 'Engineering', 'code': 'ENG102'},
            
            # General category
            {'name': 'General', 'category': 'General', 'code': ''},
            {'name': 'Mathematics', 'category': 'Mathematics', 'code': ''},
            {'name': 'Science', 'category': 'Science', 'code': ''},
            {'name': 'COA', 'category': 'Computer Science', 'code': 'CS304'},
        ]

        self.stdout.write(self.style.WARNING('Creating subjects...'))
        created_count = 0
        updated_count = 0
        
        for subject_data in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=subject_data['name'],
                defaults={
                    'category': subject_data['category'],
                    'code': subject_data['code']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {subject.name}"))
            else:
                # Update existing if needed
                if subject.category != subject_data['category'] or subject.code != subject_data['code']:
                    subject.category = subject_data['category']
                    subject.code = subject_data['code']
                    subject.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"  ↻ Updated: {subject.name}"))

        self.stdout.write(self.style.SUCCESS(f"\n✓ Summary:"))
        self.stdout.write(self.style.SUCCESS(f"  - Created: {created_count} new subjects"))
        self.stdout.write(self.style.SUCCESS(f"  - Updated: {updated_count} subjects"))
        self.stdout.write(self.style.SUCCESS(f"  - Total in database: {Subject.objects.count()}"))
