from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.contrib.auth import authenticate
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import transaction

from asgiref.sync import sync_to_async, async_to_sync
from concurrent.futures import ThreadPoolExecutor
import asyncio


from .models import Exercise, User, LlamaChatbot
from .serializers import ExerciseSerializer, UserSerializer

from video_feed import video_feed

import os
import traceback
import logging

logger = logging.getLogger(__name__)

class FileUploadView(APIView):
    parser_classes = [MultiPartParser]
    authentication_classes = [TokenAuthentication]  # Correct
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        print("FileUploadView: POST request received")
        print(f"User: {request.user}, Authenticated: {request.user.is_authenticated}")
        file = request.data.get('file')
        if not file:
            return Response({"error": "No file provided."}, status=400)
        
       
        file_name = default_storage.save(file.name, file)
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)
        
        if not file_path.endswith('.mp4'):
            return Response({"error": "Input file type must be mp4"}, status=400)
        
        
        print(f"File Name: {file_name}")
        print(f"File saved at: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        exercise_name = request.data.get('exercise_name')
        exercise_weight = request.data.get('exercise_weight')
        
        if int(exercise_weight) < 0:
            return Response({"error": "Exercise Weight must be a valid number"}, status=400)

        
        try:
            with transaction.atomic():
                #Create an exercise instance
                exercise = Exercise.objects.create(
                    input_video=file,
                    name=exercise_name,
                    exercise_weight=exercise_weight,
                )
                print("Exercise instance created")
                print(f"Video Upload: {exercise.input_video}")
                print(f"Exercise name: {exercise.name} , Exercise Weight: {exercise_weight}")
                
                stream_url, progress_url = async_to_sync(exercise.read_video)(user=request.user)
                serializer = ExerciseSerializer(exercise)
                return Response({
                    "exercise": serializer.data, 
                    "stream_url": stream_url, 
                    "progress_url": progress_url, 
                    "analysis_status": "processing"
                }, status=201)
        except Exception as e:
            print(f"Error: {e}")
            return Response({"error": str(e)}, status=500)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    def get(self, request):
        print("FileUploadView: GET Request received")
        results = Exercise.objects.all()
        serializer = ExerciseSerializer(results, many=True)
        return Response(serializer.data)

class AnalysisStatusView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, exercise_id):
        logger.info("AnalysisSatusView get called!")
        try:
            exercise = Exercise.objects.get(id=exercise_id)
            status = "completed" if exercise.chatbot_response else "processing"
            return Response({
                "status": status,
                "chatbot_response": exercise.chatbot_response if status == "completed" else None,
                })
        except Exercise.DoesNotExist:
            return Response({"error": "Exercise not found"}, status=404)
            

        

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        logger.info("LoginView get called!")
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        print(f"user found in LoginView: {user}")
        if user:
            token, created = Token.objects.get_or_create(user=user)
            print(f"token found in LoginView: {token}")
            return Response({'user_id': user.id, "username": user.username, "exists": True, 'token': token.key}, status=200)
        return Response({'error': 'Invalid credentials'}, status=400)
    def get(self, request):
        print("LoginView: GET Request received")
        results = User.objects.all()
        serializer = UserSerializer(results, many=True)
        return Response(serializer.data)

class NewUserView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        name = request.data.get('name')
        body_weight = request.data.get('weight')
        gender = request.data.get('gender')
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            name=name,
            body_weight=body_weight,
        )
        print(f"New user object created: {user}")
        if user:
            print("USER EXISTS")
            token, _ = Token.objects.get_or_create(user=user)
            # serializer = UserSerializer(user)
            return Response({"user_id": user.id, "exists": True, "token": token.key}, status=201)
        return Response({'error': 'Invalid credentials'}, status=400)
def get(self, request):
    print("NewUserView: GET Request received")
    results = User.objects.all()
    serializer = UserSerializer(results, many=True)
    return Response(serializer.data)