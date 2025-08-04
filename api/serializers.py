# backend/api/serializers.py
from rest_framework import serializers
from .models import Subject, Grade, Topic, Question, QuestionPaper

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = '__all__'

class TopicSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    grade_name = serializers.CharField(source='grade.name', read_only=True)
    
    class Meta:
        model = Topic
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    subject_name = serializers.CharField(source='topic.subject.name', read_only=True)
    
    class Meta:
        model = Question
        fields = '__all__'

class QuestionPaperSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    grade_name = serializers.CharField(source='grade.name', read_only=True)
    
    class Meta:
        model = QuestionPaper
        fields = '__all__'

class GenerateQuestionPaperSerializer(serializers.Serializer):
    grade = serializers.CharField(max_length=2)
    subject = serializers.CharField(max_length=100)
    topics = serializers.ListField(child=serializers.CharField())
    total_marks = serializers.IntegerField(min_value=1, max_value=100)
    duration = serializers.IntegerField(min_value=30, max_value=300)
    difficulty_distribution = serializers.DictField(required=False)
    question_types = serializers.ListField(
        child=serializers.ChoiceField(choices=['mcq', 'short', 'long', 'fill', 'true_false']),
        required=False
    )