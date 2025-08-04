# Create your models here.
# backend/api/models.py
from django.db import models
from django.contrib.auth.models import User

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Grade(models.Model):
    GRADE_CHOICES = [
        ('1', 'Grade 1'), ('2', 'Grade 2'), ('3', 'Grade 3'),
        ('4', 'Grade 4'), ('5', 'Grade 5'), ('6', 'Grade 6'),
        ('7', 'Grade 7'), ('8', 'Grade 8'), ('9', 'Grade 9'),
        ('10', 'Grade 10'), ('11', 'Grade 11'), ('12', 'Grade 12'),
    ]
    
    level = models.CharField(max_length=2, choices=GRADE_CHOICES, unique=True)
    name = models.CharField(max_length=50)
    
    def __str__(self):
        return f"Grade {self.level}"

class Topic(models.Model):
    name = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='topics')
    chapter_number = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.subject.name}"

class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('short', 'Short Answer'),
        ('long', 'Long Answer'),
        ('fill', 'Fill in the Blanks'),
        ('true_false', 'True/False'),
    ]
    
    BLOOM_LEVELS = [
        ('1', 'Remember'),
        ('2', 'Understand'),
        ('3', 'Apply'),
        ('4', 'Analyze'),
        ('5', 'Evaluate'),
        ('6', 'Create'),
    ]
    
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    bloom_level = models.CharField(max_length=1, choices=BLOOM_LEVELS, default='2')
    marks = models.IntegerField(default=1)
    time_to_solve = models.IntegerField(help_text="Time in minutes", default=2)
    
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions')
    answer = models.TextField()
    explanation = models.TextField(blank=True)
    
    # For MCQ type questions
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_option = models.CharField(max_length=1, blank=True, choices=[
        ('A', 'Option A'), ('B', 'Option B'), ('C', 'Option C'), ('D', 'Option D')
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.question_text[:50]}..."

class QuestionPaper(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    total_marks = models.IntegerField()
    duration = models.IntegerField(help_text="Duration in minutes")
    instructions = models.TextField(default="1. Read all questions carefully\n2. Write clearly and legibly\n3. Manage your time wisely")
    
    questions = models.ManyToManyField(Question, through='QuestionPaperQuestion')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.subject.name}"

class QuestionPaperQuestion(models.Model):
    question_paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    section = models.CharField(max_length=1, default='A')  # Section A, B, C, etc.
    order = models.IntegerField()  # Order within the section
    
    class Meta:
        ordering = ['section', 'order']