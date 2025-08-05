from django.shortcuts import render

# Create your views here.
# backend/api/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
import openai
import json
import random
from .models import Subject, Grade, Topic, Question, QuestionPaper
from .serializers import (
    SubjectSerializer, GradeSerializer, TopicSerializer, 
    QuestionSerializer, QuestionPaperSerializer, GenerateQuestionPaperSerializer
)

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Set up OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



class SubjectListView(generics.ListCreateAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

class GradeListView(generics.ListCreateAPIView):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer

class TopicListView(generics.ListCreateAPIView):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    
    def get_queryset(self):
        queryset = Topic.objects.all()
        subject = self.request.query_params.get('subject')
        grade = self.request.query_params.get('grade')
        
        if subject:
            queryset = queryset.filter(subject__name__icontains=subject)
        if grade:
            queryset = queryset.filter(grade__level=grade)
            
        return queryset

class QuestionListView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

@api_view(['POST'])
def generate_question_paper(request):
    serializer = GenerateQuestionPaperSerializer(data=request.data)
    # print("Received data:", request.data) # json data from frontend
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        # Get or create subject and grade
        subject_obj, _ = Subject.objects.get_or_create(
            name=data['subject'],
            defaults={'code': data['subject'][:3].upper()}
        )
        grade_obj, _ = Grade.objects.get_or_create(
            level=data['grade'],
            defaults={'name': f"Grade {data['grade']}"}
        )
        
        # Generate questions using AI
        questions = generate_ai_questions(
            subject=data['subject'],
            topics=data['topics'],
            grade=data['grade'],
            total_marks=data['total_marks'],
            duration=data['duration']
        )
        
        # Create question paper
        question_paper = QuestionPaper.objects.create(
            title=f"{data['subject']} - Grade {data['grade']} Question Paper",
            subject=subject_obj,
            grade=grade_obj,
            total_marks=data['total_marks'],
            duration=data['duration']
        )
        
        # Save generated questions
        saved_questions = []
        for i, q_data in enumerate(questions):
            # Get or create topic
            topic_obj, _ = Topic.objects.get_or_create(
                name=q_data.get('topic', data['topics'][0]),
                subject=subject_obj,
                grade=grade_obj
            )
            
            question = Question.objects.create(
                question_text=q_data['question'],
                question_type=q_data.get('type', 'short'),
                difficulty=q_data.get('difficulty', 'medium'),
                marks=q_data.get('marks', 2),
                topic=topic_obj,
                answer=q_data.get('answer', ''),
                option_a=q_data.get('option_a', ''),
                option_b=q_data.get('option_b', ''),
                option_c=q_data.get('option_c', ''),
                option_d=q_data.get('option_d', ''),
                correct_option=q_data.get('correct_option', '')
            )
            saved_questions.append(question)
        
        # Add questions to paper
        for i, question in enumerate(saved_questions):
            question_paper.questions.add(question)
        
        # Serialize and return
        serializer = QuestionPaperSerializer(question_paper)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to generate question paper: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def generate_ai_questions(subject, topics, grade, total_marks, duration):
    """Generate questions using OpenAI GPT"""
    
    # Calculate number of questions based on marks
    num_questions = min(total_marks // 2, 10)  # Limit to 10 questions for demo
    
    topics_str = ", ".join(topics)
    
    prompt = f"""
    Generate {num_questions} educational questions for:
    - Subject: {subject}
    - Grade: {grade}
    - Topics: {topics_str}
    - Total marks should be around {total_marks}
    - Duration: {duration} minutes
    
    Create a mix of question types:
    - Multiple choice questions (4 options each)
    - Short answer questions
    - Long answer questions
    
    For each question, provide:
    1. Question text
    2. Question type (mcq, short, long)
    3. Difficulty level (easy, medium, hard)
    4. Marks (1-5 based on complexity)
    5. Answer
    6. For MCQ: 4 options (A, B, C, D) and correct option
    7. Topic it belongs to
    
    Return as a JSON array where each question is an object.
    Make questions age-appropriate for grade {grade} students.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert teacher creating educational questions. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        # print("AI raw response:", content) # Test AI response

        # Try to parse JSON from the response
        try:
            questions = json.loads(content)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")
        
        return questions
        
    except Exception as e:
        # Fallback: return sample questions if AI fails
        print(f"AI generation failed: {e}")
        return generate_fallback_questions(subject, topics, num_questions)

def generate_fallback_questions(subject, topics, num_questions):
    """Generate fallback questions when AI fails"""
    questions = []
    
    for i in range(num_questions):
        topic = topics[i % len(topics)]
        
        if i % 3 == 0:  # MCQ
            questions.append({
                "question": f"What is the main concept in {topic}?",
                "type": "mcq",
                "difficulty": "medium",
                "marks": 1,
                "topic": topic,
                "option_a": f"Basic concept of {topic}",
                "option_b": f"Advanced theory of {topic}",
                "option_c": f"Application of {topic}",
                "option_d": f"History of {topic}",
                "correct_option": "A",
                "answer": f"Basic concept of {topic}"
            })
        elif i % 3 == 1:  # Short answer
            questions.append({
                "question": f"Explain the importance of {topic} in {subject}.",
                "type": "short",
                "difficulty": "medium",
                "marks": 3,
                "topic": topic,
                "answer": f"{topic} is important in {subject} because it forms the foundation for understanding key concepts."
            })
        else:  # Long answer
            questions.append({
                "question": f"Discuss the various aspects of {topic} and its applications.",
                "type": "long",
                "difficulty": "hard",
                "marks": 5,
                "topic": topic,
                "answer": f"Detailed explanation of {topic} covering theoretical aspects, practical applications, and real-world examples."
            })
    
    return questions