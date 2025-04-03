from django.urls import path
from . import views

urlpatterns = [
    path('fetch/', views.fetch_recordings, name='fetch-recordings'),
    path('meetings/', views.fetch_meetings, name='fetch-meetings'),
] 