# Register your models here.
# backend/api/admin.py
from django.contrib import admin
from .models import Subject, Grade, Topic, Question, QuestionPaper, QuestionPaperQuestion

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['level', 'name']
    ordering = ['level']

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'grade', 'chapter_number']
    list_filter = ['subject', 'grade']
    search_fields = ['name', 'subject__name']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text_short', 'question_type', 'difficulty', 'marks', 'topic', 'created_at']
    list_filter = ['question_type', 'difficulty', 'marks', 'topic__subject', 'topic__grade']
    search_fields = ['question_text', 'topic__name']
    readonly_fields = ['created_at']
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question'

@admin.register(QuestionPaper)
class QuestionPaperAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'grade', 'total_marks', 'duration', 'created_at']
    list_filter = ['subject', 'grade', 'created_at']
    search_fields = ['title', 'subject__name']
    readonly_fields = ['created_at']