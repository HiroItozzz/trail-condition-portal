from django.urls import path
from . import views

urlpatterns = [
    path('run-sync/', views.run_trail_sync, name='run_trail_sync'),
]