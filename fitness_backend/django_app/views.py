from django.shortcuts import render
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
from django.core.files.base import ContentFile

import requests  # Import requests

from .models import Exercise, User
from .serializers import ExerciseSerializer, UserSerializer

import os
import traceback
import logging

logger = logging.getLogger(__name__)

class FileUploadView(APIView):
    parser_classes = [MultiPartParser]
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info("FileUploadView: POST request received")
        logger.info(f"User: {request.user}, Authenticated: {request.user.is_authenticated}")
        file = request.data.get('file')
        if not file:
            return Response({"error": "No file provided."}, status=400)

        file_name = default_storage.save(file.name, file)
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)

        if not file_path.endswith('.mp4'):
            return Response({"error": "Input file type must be mp4"}, status=400)

        logger.info(f"File Name: {file_name}")
        logger.info(f"File saved at: {file_path}")
        logger.info(f"File exists: {os.path.exists(file_path)}")

        exercise_name = request.data.get('exercise_name')
        exercise_weight = request.data.get('exercise_weight')

        if int(exercise_weight) < 0:
            return Response({"error": "Exercise Weight must be a valid number"}, status=400)

        try:
            with transaction.atomic():
                exercise = Exercise.objects.create(
                    input_video=file,
                    name=exercise_name,
                    exercise_weight=exercise_weight,
                )
                logger.info("Exercise instance created")
                logger.info(f"Video Upload: {exercise.input_video}")
                logger.info(f"Exercise name: {exercise.name} , Exercise Weight: {exercise_weight}")
                
                # Call mediapipe API
                mediapipe_response = requests.post(
                    'http://mediapipe:8002/process_video',
                    json={
                        'user': request.user.body_weight,  # Use username as identifier
                        'exercise_name' : exercise.name,
                        'exercise_weight' : exercise.exercise_weight,
                        'input_video_url' : exercise.input_video.url,
                        'input_video_name' : exercise.input_video.name,
                    },
                )
                mediapipe_data = mediapipe_response.json()
                
                output_file_name = mediapipe_data.get('output_file_name')
                logger.info(f"output_file_name: {output_file_name}")
                output_path = mediapipe_data.get('output_path')
                logger.info(f"output_path: {output_path}")
                # Construct the path to the processed video on the shared volume (from Django's perspective)
                shared_output_path = os.path.join(settings.MEDIA_ROOT, 'pose_videos', output_file_name)
                logger.info(f"Django accessing shared output path: {shared_output_path}")
                try:
                    with open(output_path, 'rb') as f:
                        video_content = f.read()
                        logger.info(f"Size of video content read from shared volume: {len(video_content)} bytes")
                        exercise.output_video.save(output_file_name, ContentFile(video_content))
                except FileNotFoundError:
                    logger.error(f"FileNotFoundError: Could not find processed video at {output_path}")
                    return Response({"error": "Processed video file not found."}, status=500)
                except Exception as e:
                    logger.error(f"Error opening processed video: {e}")
                    return Response({"error": f"Error opening processed video: {e}"}, status=500)
                logger.info(f"exercise.output_video saved as: {exercise.output_video}")
                display_image_name = os.path.basename(mediapipe_data.get('display_image_path')) # Extract filename
                logger.info(f"display_image_name: {display_image_name}")
                shared_display_image_path = os.path.join(settings.MEDIA_ROOT, 'progress_images', display_image_name)
                logger.info(f"Django accessing shared display image path: {shared_display_image_path}")
                try:
                    with open(shared_display_image_path, 'rb') as f:
                        exercise.output_image.save("best_rep.png", ContentFile(f.read()))
                except FileNotFoundError:
                    logger.error(f"FileNotFoundError: Could not find display image at {shared_display_image_path}")
                    return Response({"error": "Progress image file not found."}, status=500)
                except Exception as e:
                    logger.error(f"Error opening display image: {e}")
                    return Response({"error": f"Error opening display image: {e}"}, status=500)
                
                joint_positions = mediapipe_data.get('joint_positions')
                logger.info(f"joint_positions: {joint_positions}")
                timestamps = mediapipe_data.get('timestamps')
                logger.info("timestamps: {timestamps}")
                # Call llama API (example prompt - adjust as needed)
                llama_response = requests.post(
                    'http://llama:8001/generate_text',
                    json={
                        'joint_positions': joint_positions,
                        'timestamps': timestamps,
                        'exercise_type': exercise_name,
                        },
                )
                llama_data = llama_response.json()

                exercise.chatbot_response = llama_data.get('chatbot_response')  # Save llama response

                logger.info(f"Video URL (Exercise.input_video.url) BEFORE SAVE: {exercise.input_video.url}") # ADDED LOG
                exercise.save() # Ensure the object is saved
                logger.info(f"Video URL (Exercise.input_video.url) AFTER SAVE: {exercise.input_video.url}") # ADDED LOG
                logger.info(f"exercise.output_video.name after save: {exercise.output_video.name}")
                logger.info(f"exercise.output_video.url after save: {exercise.output_video.url}")
                logger.info(f"exercise.output_image.url after save: {exercise.output_video.url}")
                serializer = ExerciseSerializer(exercise)
                return Response({
                    "exercise": serializer.data,
                    "stream_url": exercise.output_video.url,
                    "progress_url": exercise.output_image.url,
                    "analysis_status": "completed" if exercise.chatbot_response else "processing",
                }, status=201)

        except requests.exceptions.RequestException as e:
            logger.error(f"API Call Error: {e}")
            logger.error(traceback.format_exc())
            return Response({"error": f"API call failed: {e}"}, status=500)
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.error(traceback.format_exc())
            return Response({"error": str(e)}, status=500)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    def get(self, request):
        logger.info("FileUploadView: GET Request received")
        results = Exercise.objects.all()
        serializer = ExerciseSerializer(results, many=True)
        return Response(serializer.data)

class AnalysisStatusView(APIView):
    def get(self, request, exercise_id):
        logger.info("AnalysisStatusView GET method called!")
        logger.info(f"Received exercise_id: {exercise_id}")
        if exercise_id:
            try:
                exercise = Exercise.objects.get(pk=exercise_id)
                status_code = "completed" if exercise.chatbot_response else "processing"
                status_data = {
                    "id": exercise.id,
                    "status": status_code,
                    "chatbot_response": exercise.chatbot_response if status_code == "completed" else None,
                }
                return Response(status_data, status=status.HTTP_200_OK)
            except Exercise.DoesNotExist:
                return Response({"error": f"Analysis with ID {exercise_id} not found"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"error": "Please provide an exercise ID as a query parameter (e.g., ?exercise_id=123)."}, status=status.HTTP_400_BAD_REQUEST)
        

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        logger.info("UserView POST method called!")
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        logger.info(f"user found in LoginView: {user}")
        if user:
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"token found in LoginView: {token}")
            return Response({'user_id': user.id, "username": user.username, "exists": True, 'token': token.key}, status=200)
        return Response({'error': 'Invalid credentials'}, status=400)
    def get(self, request):
        logger.info("LoginView GET method called!")
        results = User.objects.all()
        serializer = UserSerializer(results, many=True)
        return Response(serializer.data)

class NewUserView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        logger.info("NewUserView POST method called!")
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
        logger.info(f"New user object created: {user}")
        if user:
            logger.info("USER EXISTS")
            token, _ = Token.objects.get_or_create(user=user)
            # serializer = UserSerializer(user)
            return Response({"user_id": user.id, "exists": True, "token": token.key}, status=201)
        return Response({'error': 'Invalid credentials'}, status=400)
    def get(self, request):
        logger.info("NewUserView GET method called!")
        results = User.objects.all()
        serializer = UserSerializer(results, many=True)
        return Response(serializer.data)
    
