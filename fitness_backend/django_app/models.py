# container_models.py
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.contrib.auth import authenticate

from storages.backends.gcloud import GoogleCloudStorage

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

class User(AbstractBaseUser):
    id=models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    body_weight = models.IntegerField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username' #Login field
    REQUIRED_FIELDS = ['email'] #required when creating superuser
    
    def user_exists(self):
        return authenticate(username=self.username, password=self.password) is not None
        
    def __str__(self):
        return f"User {self.name} weighs {self.body_weight} kg. Username: {self.username}"

class Exercise(models.Model):
    input_video = models.FileField(upload_to='uploads/', storage=GoogleCloudStorage)
    output_video = models.FileField(upload_to='pose_videos/', storage=GoogleCloudStorage, null=True, blank=True)
    output_image = models.FileField(upload_to='progress_images/', storage=GoogleCloudStorage, null=True, blank=True)
    name = models.CharField(max_length=100)
    exercise_weight = models.IntegerField()
    chatbot_response = models.TextField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name