from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'meetings', views.MeetingViewSet, basename='meeting')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', views.login, name='login'),
    path('validate-token/', views.validate_token, name='validate-token'),
    path('refresh-token/', views.refresh_token, name='refresh-token'),
    path('test/', views.test_api, name='test_api'),
    path('list/', views.list_meetings, name='list_meetings'),
    path('create/', views.create_meeting, name='create_meeting'),
    path('update/<str:meeting_id>/', views.update_meeting, name='update_meeting'),
    path('delete/<str:meeting_id>/', views.delete_meeting, name='delete_meeting'),
    path('recordings/', views.list_recordings, name='list_recordings'),
    path('recordings/<str:recording_id>/', views.delete_recording, name='delete_recording'),
    path('webhooks/recording/', views.recording_webhook, name='recording_webhook'),
    path('signature/', views.generate_signature, name='generate_signature'),
    path('<int:meeting_id>/join/', views.join_meeting, name='join_meeting'),
] 