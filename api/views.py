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
from .models import Subject, Grade, Topic, Question, QuestionPaper, QuestionPaperQuestion
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
    print("Received data:", request.data) # json data from frontend
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
            try:
                # Get or create topic
                topic_obj, _ = Topic.objects.get_or_create(
                    name=q_data.get('topic', data['topics'][0]),
                    subject=subject_obj,
                    grade=grade_obj
                )

                if q_data.get('question_type') == 'mcq':
                    options = q_data.get('options', {})
                    if not options or not all(k in options for k in ['A', 'B', 'C', 'D']):
                        print(f"Warning: MCQ question {i+1} has incomplete options, using fallback")
                        options = {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}
                else:
                    options = {}

                question = Question.objects.create(
                    question_text=q_data.get('question_text', f'Question {i+1}'),
                    question_type=q_data.get('question_type', 'short'),
                    difficulty=q_data.get('difficulty_level', 'medium'),
                    marks=q_data.get('marks', 2),
                    topic=topic_obj,
                    answer=q_data.get('answer', ''),
                    option_a=options.get('A', ''),
                    option_b=options.get('B', ''),
                    option_c=options.get('C', ''),
                    option_d=options.get('D', ''),
                    correct_option=q_data.get('correct_option', '')
                )
                saved_questions.append(question)
                
            except Exception as e:
                print(f"Error creating question {i+1}: {e}")
                print(f"Question data: {q_data}")
                # Continue with next question instead of failing completely
                continue

        # Add questions to paper with proper ordering
        for i, question in enumerate(saved_questions):
            
            # Create the relationship through the intermediate model
            QuestionPaperQuestion.objects.create(
                question_paper=question_paper,
                question=question,
                section='A',  # Default section
                order=i + 1   # Set the order (1, 2, 3, etc.)
            )
        
        
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
    Generate exactly {num_questions} educational questions for:
    - Subject: {subject}
    - Grade: {grade}
    - Topics: {topics_str}
    - Total marks should be around {total_marks}
    - Duration: {duration} minutes

    Include a mix of:
    - Multiple choice questions (question_type: "mcq")
    - Short answer questions (question_type: "short")
    - Long answer questions (question_type: "long")

    CRITICAL: Return ONLY a valid JSON array. No explanations, no markdown, no code blocks.

    Each question must be a JSON object with these exact keys:
    - "question_text": string (the actual question)
    - "question_type": one of "mcq", "short", "long"
    - "difficulty_level": one of "easy", "medium", "hard"
    - "marks": integer between 1 and 5
    - "answer": string (correct answer)
    - "topic": string (topic name)
    
    For MCQ questions, also include:
    - "options": {{"A": "option1", "B": "option2", "C": "option3", "D": "option4"}}
    - "correct_option": "A" or "B" or "C" or "D"

    Example format:
    [
        {{
            "question_text": "What is 2+2?",
            "question_type": "mcq",
            "difficulty_level": "easy",
            "marks": 1,
            "answer": "4",
            "topic": "arithmetic",
            "options": {{"A": "3", "B": "4", "C": "5", "D": "6"}},
            "correct_option": "B"
        }}
    ]

    Return the JSON array now:
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
        print("AI raw response:", content) # Test AI response

        # Clean the content - remove markdown code blocks if present
        if content.startswith('```json'):
            content = content[7:]  # Remove ```json
        if content.startswith('```'):
            content = content[3:]   # Remove ```
        if content.endswith('```'):
            content = content[:-3]  # Remove trailing ```
        
        content = content.strip()

        # Try to parse JSON from the response
        try:
            questions = json.loads(content)
            # Validate that it's a list
            if not isinstance(questions, list):
                raise ValueError("Response is not a JSON array")
            
            # Validate each question has required fields
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    raise ValueError(f"Question {i+1} is not a valid object")
                
                required_fields = ['question_text', 'question_type', 'difficulty_level', 'marks', 'answer', 'topic']
                for field in required_fields:
                    if field not in q:
                        print(f"Warning: Question {i+1} missing field '{field}', using default")
            
            return questions
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Problematic content: {content[:500]}...")
            
            # Try to extract JSON from the response using regex
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                try:
                    questions = json.loads(json_match.group())
                    return questions
                except json.JSONDecodeError:
                    print("Regex extraction also failed")
            
            # If all parsing fails, use fallback
            raise ValueError("No valid JSON found in response")
        
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
                "question_text": f"What is the main concept in {topic}?",
                "question_type": "mcq",
                "difficulty_level": "medium",
                "marks": 1,
                "topic": topic,
                "options": {
                    "A": f"Basic concept of {topic}",
                    "B": f"Advanced theory of {topic}",
                    "C": f"Application of {topic}",
                    "D": f"History of {topic}"
                },
                "correct_option": "A",
                "answer": f"Basic concept of {topic}"
            })
        elif i % 3 == 1:  # Short answer
            questions.append({
                "question_text": f"Explain the importance of {topic} in {subject}.",
                "question_type": "short",
                "difficulty_level": "medium",
                "marks": 3,
                "topic": topic,
                "answer": f"{topic} is important in {subject} because it forms the foundation for understanding key concepts."
            })
        else:  # Long answer
            questions.append({
                "question_text": f"Discuss the various aspects of {topic} and its applications.",
                "question_type": "long",
                "difficulty_level": "hard",
                "marks": 5,
                "topic": topic,
                "answer": f"Detailed explanation of {topic} covering theoretical aspects, practical applications, and real-world examples."
            })
    
    return questions


# Validate the structure of questions for later
# This function checks if the questions follow the expected schema
def validate_questions_schema(questions):
    for i, q in enumerate(questions):
        required_keys = ["question_text", "question_type", "difficulty_level", "marks", "answer", "topic"]
        for key in required_keys:
            if key not in q:
                raise ValueError(f"Missing key '{key}' in question {i+1}")
        
        if q["question_type"] == "mcq":
            if "options" not in q or "correct_option" not in q:
                raise ValueError(f"MCQ question {i+1} is missing 'options' or 'correct_option'")
            opts = q["options"]
            if not all(k in opts for k in ['A', 'B', 'C', 'D']):
                raise ValueError(f"MCQ options incomplete in question {i+1}")
