# backend/api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('subjects/', views.SubjectListView.as_view(), name='subject-list'),
    path('grades/', views.GradeListView.as_view(), name='grade-list'),
    path('topics/', views.TopicListView.as_view(), name='topic-list'),
    path('questions/', views.QuestionListView.as_view(), name='question-list'),
    path('generate-paper/', views.generate_question_paper, name='generate-paper'),
]