import torch
import time
import sys
import os
import json
import random
import re
import logging
import requests
import asyncio
import tempfile
import traceback
import numpy as np
from io import BytesIO
import psutil
from typing import Any, List, Dict
from asgiref.sync import sync_to_async

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth import authenticate
from django.contrib.postgres.fields import ArrayField
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.conf import settings


from storages.backends.gcloud import GoogleCloudStorage
import requests
import tempfile

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, AutoConfig, AutoModel
from llama_cpp import Llama

from functools import lru_cache
import bitsandbytes as bnb
import onnxruntime as ort
from torch.fx import symbolic_trace
from torch.nn import functional as F
from torch.nn.utils import prune

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from read_input_files import process_video
from time_under_tension import calculate_force_vector, plot_reps
from ExerciseAssessmentSystem import ExerciseAssessmentSystem
from TinyLlama import TinyLlama

class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required")
        
        email=self.normalize_email(email)
        user=self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        
        return self.create_user(email, username, password, **extra_fields)
# Create your models here.
class User(AbstractBaseUser):
    id=models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    body_weight = models.IntegerField(null=True, blank=True)
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    # gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username' #Login field
    REQUIRED_FIELDS = ['email'] #required when creating superuser
    
    def user_exists(self):
        return authenticate(username=self.username, password=self.password) is not None
        
    def __str__(self):
        return f"User {self.name} weighs {self.body_weight} kg. Username: {self.username} , password: {self.password}" 
    
class Exercise(models.Model):
    input_video = models.FileField(upload_to='uploads/', storage=GoogleCloudStorage)
    output_video = models.FileField(upload_to='pose_videos/', storage=GoogleCloudStorage, null=True, blank=True)
    output_image = models.FileField(upload_to='progress_images/', storage=GoogleCloudStorage, null=True, blank=True)
    name = models.CharField(max_length=100)
    exercise_weight = models.IntegerField()
    chatbot_response = models.TextField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    #Not using these fields for now, may lead to overcomplication.
    forces = ArrayField(models.FloatField(null=True, blank=True), default=list)
    angles = ArrayField(models.FloatField(null=True, blank=True), default=list)
    concentric_times = ArrayField(models.FloatField(null=True, blank=True), default=list)
    eccentric_times = ArrayField(models.FloatField(null=True, blank=True), default=list)
    reps = models.IntegerField(null=True, blank=True)
    
    def download_video_from_gcs(self, gcs_url):
        """Download video file from Google Cloud Storage to a temporary file.

        Args:
            gcs_url (str): url to video file on gcs bucket
        """
        response = requests.get(gcs_url, stream=True)
        if response.status_code == 200:
            temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            for chunk in response.iter_content(chunk_size=1024):
                temp_video.write(chunk)
            temp_video.close()
            return temp_video.name
        else:
            raise RuntimeError(f"Failed to download video from {gcs_url}, Status: {response.status_code}")

    
    async def read_video(self, user):
        print("ANALYZE VIDEO (ASYNC)")
        input_path = await asyncio.to_thread(self.download_video_from_gcs, self.input_video.url)
        print(f"Input path in read_video: {input_path}")
        output_file_name = f"pose_{os.path.basename(self.input_video.name)}"
        ouput_path = os.path.join(settings.MEDIA_ROOT, "pose_videos", output_file_name)
        
        #Ensure the output directory exists
        os.makedirs(os.path.dirname(ouput_path), exist_ok=True)
        try:
            print("Before reading video")
            print(f"Input Path: {input_path}")
            timestamps, joint_positions = await asyncio.to_thread(process_video, input_path=input_path, output_path=ouput_path,exercise_type=self.name)
            with open(ouput_path, 'rb') as f:
                await sync_to_async(self.output_video.save)(output_file_name, ContentFile(f.read()))
            print(f"Output video saved as: {self.output_video}")
            if not user:
                raise ValueError("No user found in the database.")
            else:
                print(f"User found in read_video: ${user}")
            forces, angles = await asyncio.to_thread(calculate_force_vector, joint_positions=joint_positions, timestamps=timestamps, body_weight=user.body_weight, lift_weight=self.exercise_weight, exercise_name=self.name)
            reps_list = await asyncio.to_thread(plot_reps,forces,angles,timestamps,self.name)
            progress_images = []
            concentric_times = []
            eccentric_times = []
            reps = []
            for i in range(len(reps_list)):
                reps_dict = reps_list[i]
                progress_images.append(reps_dict["image_file"])
                concentric_times.append(reps_dict["concentric_times"])
                eccentric_times.append(reps_dict["eccentric_times"])
                reps.append(reps_dict["reps"])
            print("---------PLOT REPS RETURNED VALUES----------")
            print(f"progress_images type: {type(progress_images)}")
            print(f"concentric_times type: {type(concentric_times)}")
            print(f"eccentric_times type: {type(eccentric_times)}")
            print(f"reps: {reps}")
            idx = np.argmax(reps)
            display_image = progress_images[idx]
            display_image_path = os.path.join(settings.MEDIA_ROOT, "progress_images", "best_rep.png")
            
            os.makedirs(os.path.dirname(display_image_path), exist_ok=True)
            
            #Save the PIL image to the file system
            display_image.save(display_image_path)
            
            #Save image asynchronously
            with open(display_image_path, 'rb') as f:
                await sync_to_async(self.output_image.save)("best_rep.png", ContentFile(f.read()))
            
            chatbot_response = await self.run_chatbot_analysis(joint_positions, timestamps, idx)
            
            print(f"Output video saved as: {self.output_video}")
            self.chatbot_response = chatbot_response
            await sync_to_async(self.save)()
            return self.output_video.url, self.output_image.url
        except Exception as e:
            raise RuntimeError(f"Error analyzing video: {e}")
    
    async def run_chatbot_analysis(self, joint_positions, timestamps, idx):
        try:
            joint_names = list(joint_positions[0].keys())
            max_joint = joint_names[idx]
            chatbot = BlokeLlamaChatbot()
            
            chatbot_response = await asyncio.to_thread(chatbot.video_feedback, self.name, joint_positions, timestamps, max_joint)
            # chatbot_response = await asyncio.to_thread(chatbot.generate_test_response)
            if not chatbot_response:
                raise ValueError("Chatbot returned empty response")
            print(f"Chatbot response generated: {chatbot_response[:100]}...")
            return chatbot_response
        except Exception as e:
            print(f"Chatbot analysis failed: {e}")
    def get_np_array(arrary_field):
        return np.array(arrary_field)

    
    def change_weight(self, new_weight):
        self.exercise_weight = new_weight
        self.save()
    
    def __str__(self):
        return self.name
    
class DeepseekChatbot(models.Model):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Deepseek")
        
        self.offload_path = os.path.join(settings.BASE_DIR, "model_offload")
        print(f"Deepseek offload_path: {self.offload_path}")
        
        os.makedirs(self.offload_path, exist_ok=True)
        
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
            self.logger.info(f"Using MPS (Metal) backend for M1 Mac")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
            self.logger.info(f"Using CUDA (GPU)")
        else:
            self.device = torch.device("cpu")
            self.logger.info(f"Using CPU")
        self.logger.info("Loading model with optimizations...")
        self.model = self._load_optimized_model()
        print(f"Model type: {type(self.model)}")
        print(f"Model device: {next(self.model.parameters()).device}")
        self.tokenizer = self._load_tokenizer()
        
        self.setup_inference_optimizations()
    
    def _load_optimized_model(self):
        """Load TinyLlama model for fast inference with optimization techniques such as quantization

        Returns:
            pt: TinyLlama model initialized on device
        """
        try:
            model_name="deepseek-ai/deepseek-llm-7b-chat"
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map='auto',
                trust_remote_code=True,
                offload_folder = self.offload_path,
                use_cache=True,
                offload_state_dict=True,
                low_cpu_mem_usage=True,
            )
       
            return model
        except Exception as e:
            self.logger.warning(f"Failed to load model: {e}")
            raise
    
    def _load_tokenizer(self):
        tokenizer_name = "deepseek-ai/deepseek-llm-7b-chat"
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        tokenizer.pad_token = tokenizer.eos_token
        return tokenizer
    
    def setup_inference_optimizations(self):
        #Setup inference mode
        self.model.eval()
        torch.inference_mode(True)
        
        #Clear cache
        self.model.config.use_cache = True
        torch.cuda.empty_cache() #only for CUDA
        
        #Set optimal thread settings for CPU
        if self.device.type == "cpu":
            torch.set_num_threads(os.cpu_count())
            torch.set_num_interop_threads(1)
    
    @staticmethod
    def _batch_generate(prompts: List[str], model, tokenizer, max_length: int = 200):
        inputs = tokenizer(
            prompts,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=max_length
        )
        
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_length,
                num_beams=1,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                early_stopping=True,
                use_cache=True
            )
        
        return tokenizer.batch_decode(outputs, skip_special_tokens=True)

    def generate_deepseek_cached_response(self, prompt_text: str):
        """Generate response with caching for repeated prompts"""
        start_time = time.time()
        if self.pk is None: #Ensure model is saved
            self.save()
        cache_key = f"chatbot_response_{self.pk}_{hash(prompt_text)}"
        cached_response = cache.get(cache_key)
        if cached_response:
            end_time = time.time() - start_time
            print(f"Inference Time Deepseek: {end_time}")
            return cached_response
        inputs = self.tokenizer(
            prompt_text,
            return_tensors="pt",
            padding=True
        ).to(self.device)
        
        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=200,
                num_beams=1,
                do_sample=True,
                use_cache=True,
                temperature= 0.7,
                top_p= 0.9,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        response = self.tokenizer.decode(output[0], skip_special_tokens=True)
        end_time = time.time() - start_time
        print(f"Inference Time Deepseek: {end_time}")
        cache.set(cache_key, response, timeout=3600)
        return response
    
    def deepseek_video_feedback(self, exercise_type: str, joint_positions: List[Dict], 
                      timestamps: List[float], max_joint: str, num_frames: int = 5):
        """_summary_

        Args:
            exercise_type (str): _description_
            joint_positions (List[Dict]): _description_
            timestamps (List[float]): _description_
            max_joint (str): _description_
            num_frames (int, optional): _description_. Defaults to 5.

        Returns:
            _type_: _description_
        """
        assessment_system = ExerciseAssessmentSystem()
        tiny_llama = TinyLlama()
        keypoints = tiny_llama.format_keypoints(joint_positions=joint_positions, exercise_name=exercise_type,assessment_system=assessment_system)
        print(f"keypoints: {keypoints}")
        joint_angles = []
        for frame in joint_angles:
            angles = assessment_system.calculate_joint_angles(keypoints=frame, exercise_type=exercise_type)
            if angles:
                print(f"angles: {angles}")
                joint_angles.append(angles)
        print(f"joint_angles: {joint_angles}")
        
        rom = assessment_system.calculate_range_of_motion(joint_angles)
        prompt_text = self.create_deepseek_prompt(exercise_type=exercise_type, rom=rom)
        
        return self.generate_deepseek_cached_response(prompt_text)
    def create_deepseek_prompt(self, exercise_type, rom): # Deepseek prompt creation
        general_context = f"Listed below is a workout video data for a particular exercise with its corresponding range of motion calculated in degrees as the maximum minus the minimum joint angle recorded across the entire video. Please provide feedback based on if correct form was used and provide specific explanations to determine if proper technique was used based on biomechanics and exercise science.\n\n"

        rom_str = "; ".join(f"{k.replace('_', ' ').title()}: {v:.2f}" for k, v in rom.items())

        prompt = f"{general_context}\nExercise: {exercise_type}\nRange of Motion: {rom_str}"
        
        return prompt
    

class LlamaChatbot(models.Model):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing TinyLlama")
        
        self.offload_path = os.path.join(settings.BASE_DIR, "llama_model_offload")
        
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
            self.logger.info(f"Using MPS (Metal) backend for M1 Mac")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
            self.logger.info(f"Using CUDA (GPU)")
        else:
            self.device = torch.device("cpu")
            self.logger.info(f"Using CPU")
        self.logger.info("Loading model with optimizations...")
        self.model = self._load_optimized_model()
        print(f"Model type: {type(self.model)}")
        print(f"Model device: {next(self.model.parameters()).device}")
        self.tokenizer = self._load_tokenizer()
        
        self.setup_inference_optimizations()
    
    def _load_optimized_model(self):
        """Load TinyLlama model for fast inference with optimization techniques such as quantization

        Returns:
            pt: TinyLlama model initialized on device
        """
        try:
            # model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
            model_name = os.path.join(settings.BASE_DIR.parent, "TinyLlama_fitness_chatbot")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                offload_folder = self.offload_path,
                use_cache=True,
                offload_state_dict=True,
                low_cpu_mem_usage=True,
                device_map=self.device
            ).to(self.device)

            return model
        except Exception as e:
            self.logger.warning(f"Failed to load model: {e}")
            raise
    
    def _load_tokenizer(self):
        tokenizer_name = os.path.join(settings.BASE_DIR.parent, "TinyLlama_fitness_chatbot")
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "left" #For better batch processing
        # #Add chat template
        tokenizer.chat_template ="{% for message in messages %}<|im_start|>{{ message.role }}\n{{ message.content }}<|im_end|>\n{% endfor %}"
        return tokenizer
    
    def setup_inference_optimizations(self):
        #Setup inference mode
        self.model.eval()
        torch.inference_mode(True)
        
        #Clear cache
        self.model.config.use_cache = True
        if self.device.type == "cuda":
            torch.cuda.empty_cache() #only for CUDA
        
        #Set optimal thread settings for CPU
        if self.device.type == "cpu":
            torch.set_num_threads(os.cpu_count())
            torch.set_num_interop_threads(1)
    
    @staticmethod
    def _batch_generate(prompts: List[str], model, tokenizer, max_length: int = 200):
        inputs = tokenizer(
            prompts,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=max_length
        )
        
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_length,
                num_beams=1,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                early_stopping=True,
                use_cache=True
            )
        
        return tokenizer.batch_decode(outputs, skip_special_tokens=True)

    def generate_cached_response(self, prompt_text: str, exercise_type: str):
        """Generate response with caching for repeated prompts"""
        start_time = time.time()
        if self.pk is None: #Ensure model is saved
            self.save()
        cache_key = f"chatbot_response_{self.pk}_{hash(prompt_text)}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response
        messages = [{"role": "user", "content": f"""
                Provide detailed feedback on form improvement for this {exercise_type}, based on these angle ranges: 
                {prompt_text}

                Specifically address:

                1.  Whether these angles are within a reasonable range for a proper {exercise_type}.
                2.  Potential issues with the form based on these angles.
                3.  Recommendations for improvement, referencing biomechanical principles and exercise science.
                """}]
        # print(f"messages['content']: {messages['content']}")
        input_text = self.tokenizer.apply_chat_template(messages, tokenize=False)
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            padding=True
        ).to(self.device)
        
        self._measure_resources("Before Inference")
        
        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=200,
                num_beams=1,
                do_sample=True,
                use_cache=True,
                temperature= 0.7,
                top_p= 0.9,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        self._measure_resources("After Inference")
        response = self.tokenizer.decode(output[0], skip_special_tokens=True)
        response = response.split("<|im_end|>")[-1].strip()
        end_time = time.time() - start_time
        print(f"Inference Time: {end_time}")
        cache.set(cache_key, response, timeout=3600)
        return response
    
    def generate_test_response(self):
        try:
            start_time = time.time()
            messages = [{"role": "user", "content": """
                            Provide detailed feedback on form improvement for this bench press, based on these angle ranges: 
                            Elbow Angle: 135.28; Opposite Elbow Angle: 56.13; Shoulder Angle: 91.77; Opposite Shoulder Angle: 112.97. 

                            Specifically address:

                            1.  Whether these angles are within a reasonable range for a proper bench press.
                            2.  Potential issues with the form based on these angles.
                            3.  Recommendations for improvement, referencing biomechanical principles and exercise science.
                            """}]
            input_text = self.tokenizer.apply_chat_template(messages, tokenize=False)
            
            inputs = self.tokenizer(input_text, return_tensors="pt", padding=True).to(self.device) #Tokenize in the same way as SFTTrainer
            
            self._measure_resources("Before Inference")
        
            with torch.inference_mode():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=200,  # Or a reasonable value
                    num_beams=1,
                    do_sample=True,
                    use_cache=True,
                    temperature= 0.7,
                    top_p = 0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            self._measure_resources("After Inference")
            test_response = self.tokenizer.decode(output[0], skip_special_tokens=True)
            test_response = test_response.split("<|im_end|>")[-1].strip() #Remove <|im_end|> and anything before it
            end_time = time.time() - start_time
            # print(f"Test response: {test_response}")
            print(f"Inference Time: {end_time}")
            return test_response
        except Exception as e:
            print(f"An error occurred in generate_test_response: {e}")  # Print the exception!
            traceback.print_exc() #Print the full traceback
            return None  # Or handle the error as appropriate
    
    def video_feedback(self, exercise_type: str, joint_positions: List[Dict], 
                      timestamps: List[float], max_joint: str, num_frames: int = 5):
        """_summary_

        Args:
            exercise_type (str): _description_
            joint_positions (List[Dict]): _description_
            timestamps (List[float]): _description_
            max_joint (str): _description_
            num_frames (int, optional): _description_. Defaults to 5.

        Returns:
            _type_: _description_
        """
        print("LlamaChatbot Video Feedback")
        assessment_system = ExerciseAssessmentSystem()
        tiny_llama = TinyLlama()
        keypoints = tiny_llama.format_keypoints(joint_positions=joint_positions, exercise_name=exercise_type,assessment_system=assessment_system)
        print(f"keypoints: {keypoints}")
        joint_angles = []
        for frame in keypoints:
            angles = assessment_system.calculate_joint_angles(keypoints=frame, exercise_type=exercise_type)
            if angles:
                print(f"angles: {angles}")
                joint_angles.append(angles)
        print(f"joint_angles: {joint_angles}")
        
        rom = assessment_system.calculate_range_of_motion(joint_angles)

        prompt_text = self.create_llama_prompt(rom)
        print(f"prompt_text: {prompt_text}")
        
        # return self.generate_test_response()
        return self.generate_cached_response(prompt_text, exercise_type)
    
    def create_llama_prompt(self, rom):
        rom_str = "; ".join(f"{k.replace('_', ' ').title()}: {v:.2f}" for k, v in rom.items())
        print(f"rom_string: {rom_str}")
        return rom_str
    
    def _measure_resources(self, stage: str):
        print(f"--- Resource Usage ({stage}) ---")
        print(f"CPU Usage: {psutil.cpu_percent()}%")
        mem = psutil.virtual_memory()
        print(f"RAM Usage: {mem.used / (1024 ** 2):.2f} MB / {mem.total / (1024 ** 2):.2f} MB")

        if self.device.type == "cuda":
            print(f"GPU Memory Allocated: {torch.cuda.memory_allocated() / (1024 ** 2):.2f} MB")
            print(f"GPU Memory Reserved: {torch.cuda.memory_reserved() / (1024 ** 2):.2f} MB")
        elif self.device.type == "mps":
            if hasattr(torch.mps, 'memory_allocated'):
                print(f"MPS Memory Allocated: {torch.mps.memory_allocated() / (1024 ** 2):.2f} MB")
            if hasattr(torch.mps, 'memory_reserved'):
                print(f"MPS Memory Reserved: {torch.mps.memory_reserved() / (1024 ** 2):.2f} MB")
        print("---")
            

class BlokeLlamaChatbot(models.Model):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self.logger.info("Initializing BlokeLlamaChatbot")

        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.device = "mps"
            self.logger.info(f"Using MPS (Metal) backend for M1 Mac")
        elif hasattr(torch, 'cuda') and torch.cuda.is_available():
            self.device = "cuda"
            self.logger.info(f"Using CUDA (GPU)")
        else:
            self.device = "cpu"
            self.logger.info(f"Using CPU")
        self.logger.info("Loading base model...")
        self.model = self._load_base_model()
        print(f"Model type: {type(self.model)}")

    def _load_base_model(self):
        """Load the base TinyLlama model without optimizations."""
        try:
            model_path = os.path.join(
                os.path.expanduser("~/Downloads"), 
                "tinyllama-1.1b-chat-v0.3.Q8_0.gguf"
            )
            
            # Ensure the model file exists
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found at {model_path}")
            
            stop = ["Q", "\n"]

            # Initialize the model with appropriate parameters
            model = Llama(
                model_path=model_path,
                n_ctx=4096,  # Context window size
                n_batch=512,  # Batch size
                n_gpu_layers=-1 if self.device == "cuda" else 0  # Use GPU acceleration if available
            )
            
            return model
        except Exception as e:
            self.logger.error(f"Failed to load base model: {e}")
            raise
    
    def generate_cached_response(self, prompt_text: str):
        """Generate response with caching for repeated prompts"""
        print("Generate Cached Response")
        start_time = time.time()
        if self.pk is None: #Ensure model is saved
            self.save()
        cache_key = f"chatbot_response_{self.pk}_{hash(prompt_text)}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response
        try:
            start_time = time.time()
            self._measure_resources("Before Inference")
            
            output = self.model(
                prompt=prompt_text,
                max_tokens=10000,
                temperature=random.uniform(0.7,1.0),
                top_p=0.9,
                top_k=random.randint(40,60),
                repeat_penalty=random.uniform(1.1,1.3),
                # stop=["###", "\n\n"],
            )
            generated_text = output['choices'][0]['text']
            # Find the starting index after "<|im_start|>assistant"
            start_index = generated_text.find("<|im_start|>assistant") + len("<|im_start|>assistant")
            # Extract the desired output
            response = generated_text[start_index:].strip()
            # Clean up the response
            response = re.sub(r'<[^>]+>', '', response)
            response = re.sub(r'\s+', ' ', response)
            
            end_time = time.time() - start_time
            self._measure_resources("After Inference")
            print(f"Inference Time: {end_time}")
            print(f"Response: {response}")
            return response
        except Exception as e:
            print(f"An error occurred in generate_test_response: {e}")
            traceback.print_exc()
            return None

    def generate_test_response(self):
        try:
            start_time = time.time()
            prompt = """<|im_start|>user
            Biomechanical Analysis of Bench Press Form

            Given the following precise joint angle measurements:
            - Right Elbow Angle: 135.28°
            - Left Elbow Angle: 56.13°
            - Right Shoulder Angle: 91.77°
            - Left Shoulder Angle: 112.97°

            Provide a comprehensive, unique technical assessment focusing on:
            1. Detailed analysis of each angle's implications for bench press technique
            2. Specific biomechanical recommendations for form improvement
            3. Potential compensation patterns or injury risks
            4. Precise adjustments to optimize movement efficiency

            Your response should be original, technical, and provide actionable insights.<|im_end|>
            <|im_start|>assistant
            """
            print(f"Base Model Input Text: {prompt}")
            self._measure_resources("Before Inference")
            
            output = self.model(
                prompt=prompt,
                max_tokens=500,
                temperature=random.uniform(0.7,1.0),
                top_p=0.9,
                top_k=random.randint(40,60),
                repeat_penalty=random.uniform(1.1,1.3),
                # stop=["###", "\n\n"],
            )
            
            self._measure_resources("After Inference")
            generated_text = output['choices'][0]['text']
            # Find the starting index after "<|im_start|>assistant"
            start_index = generated_text.find("<|im_start|>assistant") + len("<|im_start|>assistant")
            # Extract the desired output
            test_response = generated_text[start_index:].strip()
            # Clean up the response
            test_response = re.sub(r'<[^>]+>', '', test_response)
            test_response = re.sub(r'\s+', ' ', test_response)
            
            end_time = time.time() - start_time
            
            print(f"Inference Time: {end_time}")
            print(f"Test response: {test_response}")
            return test_response
        except Exception as e:
            print(f"An error occurred in generate_test_response: {e}")
            traceback.print_exc()
            return None
        
    def video_feedback(self, exercise_type: str, joint_positions: List[Dict], 
                    timestamps: List[float], max_joint: str, num_frames: int = 5):
        """_summary_

        Args:
            exercise_type (str): _description_
            joint_positions (List[Dict]): _description_
            timestamps (List[float]): _description_
            max_joint (str): _description_
            num_frames (int, optional): _description_. Defaults to 5.

        Returns:
            _type_: _description_
        """
        print("VIDEO FEEDBACK IN BLOKELLAMACHATBOT")
        assessment_system = ExerciseAssessmentSystem()
        tiny_llama = TinyLlama()
        keypoints = tiny_llama.format_keypoints(joint_positions=joint_positions, exercise_name=exercise_type,assessment_system=assessment_system)
        print(f"keypoints: {keypoints}")
        joint_angles = []
        for frame in keypoints:
            angles = assessment_system.calculate_joint_angles(keypoints=frame, exercise_type=exercise_type)
            if angles:
                print(f"angles: {angles}")
                joint_angles.append(angles)
        print(f"joint_angles: {joint_angles}")
        
        rom = assessment_system.calculate_range_of_motion(joint_angles)
        print(f"rom: {rom}")


        prompt_text = self.create_llama_prompt(
            exercise_type, rom
        )
        print(f"prompt_text: {prompt_text}")
        
        # return self.generate_cached_response(prompt_text)
        return self.generate_test_response()
    
    def create_llama_prompt(self, exercise_type, rom):
        

        rom_str = "; ".join(f"{k.replace('_', ' ').title()}: {v:.2f}" for k, v in rom.items())
        print(f"rom_str: {rom_str}")
        prompt = f"""<|im_start|>user
            Biomechanical Analysis of {exercise_type} Form

            Given the following precise joint angle measurements:
            {rom_str}

            Provide a comprehensive, unique technical assessment focusing on:
            1. Detailed analysis of each angle's implications for {exercise_type} technique
            2. Specific biomechanical recommendations for form improvement
            3. Potential compensation patterns or injury risks
            4. Precise adjustments to optimize movement efficiency

            Your response should be original, technical, and provide actionable insights.<|im_end|>
            <|im_start|>assistant
            """

        return prompt

    def _measure_resources(self, stage: str):
        print(f"--- Resource Usage ({stage}) ---")
        print(f"CPU Usage: {psutil.cpu_percent()}%")
        mem = psutil.virtual_memory()
        print(f"RAM Usage: {mem.used / (1024 ** 2):.2f} MB / {mem.total / (1024 ** 2):.2f} MB")

        if self.device == "cuda":
            print(f"GPU Memory Allocated: {torch.cuda.memory_allocated() / (1024 ** 2):.2f} MB")
            print(f"GPU Memory Reserved: {torch.cuda.memory_reserved() / (1024 ** 2):.2f} MB")
        elif self.device == "mps":
            if hasattr(torch.mps, 'memory_allocated'):
                print(f"MPS Memory Allocated: {torch.mps.memory_allocated() / (1024 ** 2):.2f} MB")
            if hasattr(torch.mps, 'memory_reserved'):
                print(f"MPS Memory Reserved: {torch.mps.memory_reserved() / (1024 ** 2):.2f} MB")
        print("---")


    

    
