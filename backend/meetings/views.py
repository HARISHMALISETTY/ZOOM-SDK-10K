from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import BaseAuthentication
from rest_framework.response import Response
from django.conf import settings
import requests
import json
from datetime import datetime
import jwt
import time
from .models import Meeting, Recording, Mentor, Student
from .utils import get_zoom_access_token, send_meeting_invitations, send_recording_notification
import base64
from urllib.parse import urlencode
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
import logging
from rest_framework import status
import hmac
import hashlib
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

class NoAuthentication(BaseAuthentication):
    def authenticate(self, request):
        return None

def generate_zoom_jwt_token():
    """Generate a JWT token for Zoom Server-to-Server OAuth"""
    client_id = settings.ZOOM_CLIENT_ID
    client_secret = settings.ZOOM_CLIENT_SECRET
    account_id = settings.ZOOM_ACCOUNT_ID
    
    # Generate JWT token
    token = jwt.encode(
        {
            'iss': client_id,
            'sub': account_id,
            'exp': int(time.time()) + 3600,  # Token expires in 1 hour
            'iat': int(time.time())
        },
        client_secret,
        algorithm='HS256'
    )
    return token

def get_zoom_access_token(mentor=None):
    """Get Zoom access token using account credentials"""
    try:
        # Zoom OAuth endpoint
        oauth_url = 'https://zoom.us/oauth/token'
        
        # Use mentor credentials if provided, otherwise use global settings
        client_id = mentor.zoom_client_id if mentor else settings.ZOOM_CLIENT_ID
        client_secret = mentor.zoom_client_secret if mentor else settings.ZOOM_CLIENT_SECRET
        account_id = mentor.zoom_account_id if mentor else settings.ZOOM_ACCOUNT_ID
        
        # Create Basic Auth header
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        # Request headers
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Request body
        data = {
            'grant_type': 'account_credentials',
            'account_id': account_id
        }
        
        # Make request to get access token
        response = requests.post(
            oauth_url,
            headers=headers,
            data=urlencode(data)
        )
        response.raise_for_status()
        
        token_data = response.json()
        return token_data.get('access_token')
        
    except Exception as e:
        logger.error(f"Error getting Zoom access token: {str(e)}")
        raise

@api_view(['GET'])
@permission_classes([AllowAny])
def test_api(request):
    """Test endpoint to verify API is working"""
    return Response({
        'message': 'Hello! You can start the meeting now.',
        'status': 'success'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_meetings(request):
    """List all meetings for the authenticated mentor"""
    try:
        mentor = Mentor.objects.get(user=request.user)
        meetings = Meeting.objects.filter(mentor=mentor)
        
        meetings_data = [{
            'meeting_id': meeting.meeting_id,
            'topic': meeting.topic,
            'start_time': meeting.start_time,
            'duration': meeting.duration,
            'join_url': meeting.join_url,
            'password': meeting.password,
            'meeting_type': meeting.meeting_type,
            'recording_url': meeting.recording_url,
            'recording_status': meeting.recording_status,
            'is_active': meeting.is_active,
            'students': [{
                'id': student.id,
                'name': student.user.username,
                'email': student.user.email
            } for student in meeting.students.all()]
        } for meeting in meetings]
        
        return Response(meetings_data)
    except Mentor.DoesNotExist:
        return Response(
            {'error': 'Mentor profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error listing meetings: {str(e)}")
        return Response(
            {'error': 'Failed to list meetings'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def create_meeting(request):
    """Create a new meeting"""
    try:
        logger.info(f"Creating meeting with data: {request.data}")
        logger.info(f"User: {request.user}")
        
        # Get or create mentor profile with better error handling
        try:
            mentor, created = Mentor.objects.get_or_create(
                user=request.user,
                defaults={
                    'zoom_account_id': settings.ZOOM_ACCOUNT_ID,
                    'zoom_client_id': settings.ZOOM_CLIENT_ID,
                    'zoom_client_secret': settings.ZOOM_CLIENT_SECRET
                }
            )
            logger.info(f"Mentor profile {'created' if created else 'found'}: {mentor.id}")
        except Exception as e:
            logger.error(f"Error creating/getting mentor profile: {str(e)}")
            return Response(
                {'error': f'Failed to create/get mentor profile: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Validate required fields
        if not request.data.get('topic'):
            return Response(
                {'error': 'Topic is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get Zoom access token using mentor credentials
        try:
            access_token = get_zoom_access_token(mentor)
            logger.info("Successfully obtained Zoom access token")
        except Exception as e:
            logger.error(f"Error getting Zoom access token: {str(e)}")
            return Response(
                {'error': f'Failed to get Zoom access token: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Prepare meeting data
        meeting_type = request.data.get('type', 2)  # 1 for instant, 2 for scheduled
        meeting_data = {
            'topic': request.data.get('topic'),
            'type': meeting_type,
            'duration': request.data.get('duration', 60),
            'timezone': request.data.get('timezone', 'UTC'),
            'agenda': request.data.get('description', ''),
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': False,
                'mute_upon_entry': True,
                'waiting_room': True,
                'recording_consent': True
            }
        }
        
        # Add start_time only for scheduled meetings
        if meeting_type == 2 and request.data.get('start_time'):
            meeting_data['start_time'] = request.data.get('start_time')
        
        logger.info(f"Prepared meeting data: {meeting_data}")
        
        # Create meeting in Zoom
        try:
            response = requests.post(
                'https://api.zoom.us/v2/users/me/meetings',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=meeting_data
            )
            
            if response.status_code != 201:
                logger.error(f"Zoom API error: {response.text}")
                return Response(
                    {'error': f'Failed to create meeting in Zoom: {response.text}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            zoom_data = response.json()
            logger.info(f"Zoom API response: {zoom_data}")
        except Exception as e:
            logger.error(f"Error creating meeting in Zoom: {str(e)}")
            return Response(
                {'error': f'Failed to create meeting in Zoom: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create meeting in database
        try:
            meeting = Meeting.objects.create(
                mentor=mentor,
                topic=zoom_data['topic'],
                start_time=datetime.fromisoformat(zoom_data['start_time'].replace('Z', '+00:00')) if 'start_time' in zoom_data else datetime.now(),
                duration=int(zoom_data.get('duration', 60)),  # Ensure duration is an integer
                meeting_id=zoom_data['id'],
                join_url=zoom_data['join_url'],
                password=zoom_data.get('password', ''),
                host_email=zoom_data['host_email'],
                meeting_type='instant' if meeting_type == 1 else 'scheduled',
                timezone=zoom_data['timezone'],
                agenda=zoom_data.get('agenda', ''),
                settings=zoom_data.get('settings', {})
            )
            
            logger.info(f"Created meeting in database: {meeting.id}")
        except Exception as e:
            logger.error(f"Error creating meeting in database: {str(e)}")
            return Response(
                {'error': f'Failed to create meeting in database: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'id': meeting.id,
            'meeting_id': meeting.meeting_id,
            'topic': meeting.topic,
            'join_url': meeting.join_url,
            'password': meeting.password,
            'start_time': meeting.start_time,
            'duration': meeting.duration,
            'host_email': meeting.host_email,
            'batch_name': 'N/A'  # We'll handle batch name in the frontend
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating meeting: {str(e)}")
        return Response(
            {'error': f'Failed to create meeting: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([AllowAny])
def update_meeting(request, meeting_id):
    """Update an existing meeting"""
    try:
        meeting = Meeting.objects.get(meeting_id=meeting_id)
        
        # Get updated data
        topic = request.data.get('topic', meeting.topic)
        duration = request.data.get('duration', meeting.duration)
        start_time = request.data.get('start_time', meeting.start_time)
        timezone = request.data.get('timezone', meeting.timezone)
        agenda = request.data.get('agenda', meeting.agenda)
        settings = request.data.get('settings', meeting.settings)

        # Get Zoom access token
        access_token = get_zoom_access_token()
        
        # Zoom API endpoint
        url = f'https://api.zoom.us/v2/meetings/{meeting_id}'
        
        # Request headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Prepare update data
        data = {
            'topic': topic,
            'duration': duration,
            'timezone': timezone,
            'agenda': agenda,
            'settings': settings
        }

        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                data['start_time'] = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                return Response({
                    'success': False,
                    'error': 'Invalid start_time format. Use ISO 8601 format.'
                }, status=400)

        # Make request to Zoom API
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        
        # Update local meeting object
        meeting.topic = topic
        meeting.duration = duration
        meeting.start_time = start_time
        meeting.timezone = timezone
        meeting.agenda = agenda
        meeting.settings = settings
        meeting.save()
        
        return Response({
            'success': True,
            'meeting': {
                'id': meeting.meeting_id,
                'topic': meeting.topic,
                'start_time': meeting.start_time,
                'duration': meeting.duration,
                'join_url': meeting.join_url,
                'timezone': meeting.timezone,
                'agenda': meeting.agenda,
                'settings': meeting.settings
            }
        })

    except Meeting.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Meeting not found'
        }, status=404)
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to update meeting: {str(e)}'
        }, status=500)

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_meeting(request, meeting_id):
    """Delete a meeting"""
    try:
        mentor = Mentor.objects.get(user=request.user)
        meeting = get_object_or_404(Meeting, meeting_id=meeting_id, mentor=mentor)
        
        # Get Zoom access token
        access_token = get_zoom_access_token(mentor)
        
        # Delete meeting from Zoom
        response = requests.delete(
            f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code not in [204, 404]:
            logger.error(f"Zoom API error: {response.text}")
            # Continue with database deletion even if Zoom deletion fails
        
        # Delete meeting from database
        meeting.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    except Mentor.DoesNotExist:
        return Response(
            {'error': 'Mentor profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Meeting.DoesNotExist:
        return Response(
            {'error': 'Meeting not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error deleting meeting: {str(e)}")
        return Response(
            {'error': 'Failed to delete meeting'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_recordings(request):
    """List all recordings for the authenticated mentor"""
    try:
        mentor = Mentor.objects.get(user=request.user)
        recordings = Recording.objects.filter(meeting__mentor=mentor).order_by('-created_at')
        recordings_data = [{
            'id': recording.id,
            'meeting_id': recording.meeting.meeting_id,
            'meeting_topic': recording.meeting.topic,
            'recording_url': recording.recording_url,
            'recording_type': recording.recording_type,
            'created_at': recording.created_at,
            'file_size': recording.file_size,
            'duration': recording.duration
        } for recording in recordings]
        return Response({
            'success': True,
            'recordings': recordings_data
        })
    except Exception as e:
        logger.error(f"Error listing recordings: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to list recordings'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_recording(request, recording_id):
    """Delete a recording"""
    try:
        mentor = Mentor.objects.get(user=request.user)
        recording = Recording.objects.get(id=recording_id, meeting__mentor=mentor)
        
        # Get Zoom access token
        access_token = get_zoom_access_token(mentor)
        
        # Zoom API endpoint
        url = f'https://api.zoom.us/v2/meetings/{recording.meeting.meeting_id}/recordings/{recording_id}'
        
        # Request headers
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        # Make request to Zoom API
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        # Delete local recording object
        recording.delete()
        
        return Response({
            'success': True,
            'message': 'Recording deleted successfully'
        })

    except Recording.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Recording not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting recording: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to delete recording'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def send_meeting_invitations(meeting, student_ids):
    """Send meeting invitations to students"""
    try:
        students = Student.objects.filter(id__in=student_ids)
        for student in students:
            # Send email to student with meeting details
            subject = f'Meeting Invitation: {meeting.topic}'
            message = f"""
            Dear {student.user.username},
            
            You have been invited to join the following meeting:
            
            Topic: {meeting.topic}
            Date: {meeting.start_time}
            Duration: {meeting.duration} minutes
            Join URL: {meeting.join_url}
            Password: {meeting.password}
            
            Please join the meeting using the link above.
            
            Best regards,
            {meeting.mentor.user.username}
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [student.user.email],
                fail_silently=False,
            )
    except Exception as e:
        print(f"Error sending meeting invitations: {str(e)}")

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([NoAuthentication])
def handle_recording_webhook(request):
    """Handle Zoom recording webhooks"""
    try:
        # Verify webhook signature
        payload = request.body
        signature = request.headers.get('X-Zm-Signature')
        timestamp = request.headers.get('X-Zm-Request-Timestamp')
        
        if not signature or not timestamp:
            return Response({'error': 'Missing signature or timestamp'}, status=400)
        
        # Verify signature
        message = f"v0:{timestamp}:{payload.decode('utf-8')}"
        expected_signature = f"v0={hmac.new(settings.ZOOM_WEBHOOK_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()}"
        
        if not hmac.compare_digest(signature, expected_signature):
            return Response({'error': 'Invalid signature'}, status=401)
        
        # Parse webhook payload
        data = json.loads(payload)
        event = data.get('event')
        payload_data = data.get('payload', {})
        
        if event == 'recording.started':
            meeting_id = payload_data.get('object', {}).get('id')
            if meeting_id:
                meeting = Meeting.objects.filter(meeting_id=meeting_id).first()
                if meeting:
                    meeting.recording_status = 'processing'
                    meeting.recording_start_time = datetime.now()
                    meeting.save()
                    logger.info(f"Recording started for meeting {meeting_id}")
        
        elif event == 'recording.stopped':
            meeting_id = payload_data.get('object', {}).get('id')
            if meeting_id:
                meeting = Meeting.objects.filter(meeting_id=meeting_id).first()
                if meeting:
                    meeting.recording_status = 'completed'
                    meeting.recording_end_time = datetime.now()
                    meeting.save()
                    logger.info(f"Recording stopped for meeting {meeting_id}")
        
        elif event == 'recording.completed':
            meeting_id = payload_data.get('object', {}).get('id')
            if meeting_id:
                meeting = Meeting.objects.filter(meeting_id=meeting_id).first()
                if meeting:
                    # Get recording details from Zoom
                    access_token = get_zoom_access_token()
                    response = requests.get(
                        f'https://api.zoom.us/v2/meetings/{meeting_id}/recordings',
                        headers={
                            'Authorization': f'Bearer {access_token}',
                            'Content-Type': 'application/json'
                        }
                    )
                    
                    if response.status_code == 200:
                        recordings_data = response.json()
                        for recording_data in recordings_data.get('recording_files', []):
                            recording = Recording.objects.create(
                                meeting=meeting,
                                recording_url=recording_data.get('download_url'),
                                recording_type=recording_data.get('recording_type', 'video'),
                                file_size=recording_data.get('file_size'),
                                duration=recording_data.get('duration')
                            )
                            
                            # Send notification to students
                            send_recording_notification(recording)
                    
                    meeting.recording_status = 'completed'
                    meeting.save()
                    logger.info(f"Recording completed for meeting {meeting_id}")
        
        return Response({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error handling recording webhook: {str(e)}")
        return Response({'error': 'Failed to process webhook'}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login endpoint for mentors"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate user
        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get or create mentor profile
        mentor, created = Mentor.objects.get_or_create(
            user=user,
            defaults={
                'zoom_account_id': settings.ZOOM_ACCOUNT_ID,
                'zoom_client_id': settings.ZOOM_CLIENT_ID,
                'zoom_client_secret': settings.ZOOM_CLIENT_SECRET
            }
        )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response({
            'access_token': access_token,
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_mentor': True
            }
        })

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response(
            {'error': f'Login failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def generate_signature(request):
    """Generate a signature for joining a Zoom meeting"""
    try:
        meeting_number = request.data.get('meetingNumber')
        role = request.data.get('role', 0)  # 0 for attendee, 1 for host

        # Get current timestamp
        timestamp = int(time.time() * 1000)  # Current time in milliseconds

        # Prepare the message string with all required parameters
        msg = f'{settings.ZOOM_SDK_KEY}.{meeting_number}.{timestamp}.{role}'

        # Generate the hash using SHA256
        hash_object = hmac.new(
            settings.ZOOM_SDK_SECRET.encode(),
            msg.encode(),
            hashlib.sha256
        )
        signature = base64.b64encode(hash_object.digest()).decode()

        return Response({
            'signature': signature,
            'sdkKey': settings.ZOOM_SDK_KEY,
            'timestamp': timestamp
        })
    except Exception as e:
        logger.error(f"Error generating signature: {str(e)}")
        return Response(
            {'error': f'Failed to generate signature: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 