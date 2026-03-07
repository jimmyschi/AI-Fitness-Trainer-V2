from django.urls import path
from .views import LoginView, FileUploadView, NewUserView, AnalysisStatusView

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='upload'),
    path('analysis-status/<int:exercise_id>/', AnalysisStatusView.as_view(), name='analysis-status'),
    path('login/', LoginView.as_view(), name='login'), #Login endpoint
    path('new/', NewUserView.as_view(), name='new'),
]
