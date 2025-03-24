from django.conf import settings
import requests
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
import base64
from urllib.parse import urlencode

def get_zoom_access_token(mentor):
    """Get a Zoom access token using mentor's account credentials."""
    try:
        # Create the authorization header
        auth_string = f"{mentor.zoom_client_id}:{mentor.zoom_client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Prepare the request body
        data = {
            'grant_type': 'account_credentials',
            'account_id': mentor.zoom_account_id
        }
        
        response = requests.post(
            'https://zoom.us/oauth/token',
            headers=headers,
            data=urlencode(data)
        )
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        print(f"Error getting Zoom access token: {str(e)}")
        raise

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

def send_recording_notification(recording):
    """Send notification to students about available recording"""
    try:
        meeting = recording.meeting
        students = meeting.students.all()
        
        for student in students:
            subject = f'Recording Available: {meeting.topic}'
            message = f"""
            Dear {student.user.username},
            
            The recording for the following meeting is now available:
            
            Topic: {meeting.topic}
            Date: {meeting.start_time}
            Recording Type: {recording.recording_type}
            
            You can access the recording using this link:
            {recording.recording_url}
            
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
        print(f"Error sending recording notification: {str(e)}") 