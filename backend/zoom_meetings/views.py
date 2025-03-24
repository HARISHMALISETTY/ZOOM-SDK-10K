from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
import jwt
import time
import json
from datetime import datetime, timedelta
import requests

from .models import Meeting, Participant
from .serializers import MeetingSerializer, ParticipantSerializer

class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Meeting.objects.filter(host=self.request.user)

    def generate_zoom_signature(self, meeting_number, role):
        iat = int(time.time())
        exp = iat + 60 * 60 * 2  # Token expires in 2 hours

        token_payload = {
            'sdkKey': settings.ZOOM_SDK_KEY,
            'mn': meeting_number,
            'role': role,
            'iat': iat,
            'exp': exp,
            'appKey': settings.ZOOM_SDK_KEY,
            'tokenExp': iat + 60 * 60 * 2
        }

        return jwt.encode(token_payload, settings.ZOOM_SDK_SECRET, algorithm='HS256')

    def generate_jwt_token(self):
        """Generate a JWT token for Zoom API authentication"""
        token = jwt.encode(
            {
                'iss': settings.ZOOM_API_KEY,
                'exp': time.time() + 3600
            },
            settings.ZOOM_API_SECRET,
            algorithm='HS256'
        )
        return token

    @action(detail=False, methods=['post'])
    def create_meeting(self, request):
        """Create a new Zoom meeting"""
        try:
            # Generate JWT token
            token = self.generate_jwt_token()
            
            # Prepare meeting data
            meeting_data = {
                'topic': request.data.get('topic', 'New Meeting'),
                'type': 2,  # Scheduled meeting
                'start_time': request.data.get('start_time'),
                'duration': request.data.get('duration', 60),  # Default 60 minutes
                'settings': {
                    'host_video': True,
                    'participant_video': True,
                    'join_before_host': False,
                    'mute_upon_entry': True,
                    'waiting_room': True,
                    'meeting_authentication': True
                }
            }

            # Create meeting using Zoom API
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://api.zoom.us/v2/users/me/meetings',
                headers=headers,
                json=meeting_data
            )
            
            if response.status_code == 201:
                meeting_info = response.json()
                
                # Save meeting details to database
                meeting = Meeting.objects.create(
                    topic=meeting_info['topic'],
                    meeting_id=meeting_info['id'],
                    join_url=meeting_info['join_url'],
                    password=meeting_info.get('password', ''),
                    host_email=meeting_info['host_email'],
                    created_by=request.user
                )
                
                return Response({
                    'success': True,
                    'meeting': {
                        'id': meeting.id,
                        'topic': meeting.topic,
                        'join_url': meeting.join_url,
                        'meeting_id': meeting.meeting_id,
                        'password': meeting.password
                    }
                })
            else:
                return Response({
                    'success': False,
                    'error': response.json()
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def join_meeting(self, request, pk=None):
        """Get meeting details for joining"""
        try:
            meeting = self.get_object()
            return Response({
                'success': True,
                'meeting': {
                    'id': meeting.id,
                    'topic': meeting.topic,
                    'join_url': meeting.join_url,
                    'meeting_id': meeting.meeting_id,
                    'password': meeting.password
                }
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        meeting = serializer.save()
        zoom_meeting = self.create_zoom_meeting(
            meeting.topic,
            meeting.start_time,
            meeting.duration
        )
        
        meeting.meeting_id = zoom_meeting['id']
        meeting.meeting_password = zoom_meeting['password']
        meeting.join_url = zoom_meeting['join_url']
        meeting.save()

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        meeting = self.get_object()
        participant = Participant.objects.create(
            meeting=meeting,
            user=request.user,
            joined_at=datetime.now()
        )
        
        signature = self.generate_zoom_signature(
            meeting.meeting_id,
            0 if request.user != meeting.host else 1
        )
        
        return Response({
            'signature': signature,
            'meeting_number': meeting.meeting_id,
            'password': meeting.meeting_password,
            'user_name': request.user.username,
            'user_email': request.user.email,
        })

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        meeting = self.get_object()
        participant = Participant.objects.get(
            meeting=meeting,
            user=request.user,
            left_at__isnull=True
        )
        participant.left_at = datetime.now()
        participant.save()
        return Response(status=status.HTTP_200_OK)
