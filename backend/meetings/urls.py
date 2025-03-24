from django.urls import path
from . import views
from . import auth

urlpatterns = [
    path('login/', views.login, name='login'),
    path('validate-token/', auth.ValidateTokenView.as_view(), name='validate-token'),
    path('refresh-token/', auth.RefreshTokenView.as_view(), name='refresh-token'),
    path('test/', views.test_api, name='test_api'),
    path('list/', views.list_meetings, name='list_meetings'),
    path('create/', views.create_meeting, name='create_meeting'),
    path('update/<str:meeting_id>/', views.update_meeting, name='update_meeting'),
    path('delete/<str:meeting_id>/', views.delete_meeting, name='delete_meeting'),
    path('recordings/', views.list_recordings, name='list_recordings'),
    path('recordings/<str:recording_id>/', views.delete_recording, name='delete_recording'),
    path('webhooks/recording/', views.handle_recording_webhook, name='recording_webhook'),
    path('signature/', views.generate_signature, name='generate_signature'),
] 