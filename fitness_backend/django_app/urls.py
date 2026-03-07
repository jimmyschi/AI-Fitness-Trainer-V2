# django_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('upload/', views.FileUploadView.as_view(), name='upload'),
    path('users/', views.NewUserView.as_view(), name='users'),
    path('analysis-status/<int:exercise_id>/', views.AnalysisStatusView.as_view(), name='analysis_status'),
    path('new/', views.NewUserView.as_view(), name='new_user'),
]