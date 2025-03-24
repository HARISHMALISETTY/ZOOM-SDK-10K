from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Meeting, Recording
from .utils import send_recording_notification
import hmac
import hashlib
import base64
from django.conf import settings
from datetime import datetime

def verify_webhook_signature(request):
    """Verify the webhook signature from Zoom"""
    try:
        # Get the signature from the request header
        signature = request.headers.get('X-Zm-Signature')
        if not signature:
            return False

        # Get the timestamp from the request header
        timestamp = request.headers.get('X-Zm-Request-Timestamp')
        if not timestamp:
            return False

        # Get the webhook secret from settings
        webhook_secret = settings.ZOOM_WEBHOOK_SECRET

        # Construct the message string
        message = f"v0:{timestamp}:{request.body.decode('utf-8')}"

        # Calculate the expected signature
        expected_signature = f"v0={hmac.new(webhook_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()}"

        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        print(f"Error verifying webhook signature: {str(e)}")
        return False

@csrf_exempt
@require_POST
def handle_recording_webhook(request):
    """Handle Zoom recording webhook events"""
    try:
        # Verify webhook signature
        if not verify_webhook_signature(request):
            return HttpResponse('Invalid signature', status=401)

        # Parse the webhook payload
        payload = json.loads(request.body)
        event = payload.get('event')
        payload_data = payload.get('payload', {})

        if event == 'recording.started':
            # Handle recording started event
            meeting_id = payload_data.get('object', {}).get('id')
            if meeting_id:
                meeting = Meeting.objects.get(meeting_id=meeting_id)
                meeting.recording_status = 'processing'
                meeting.recording_start_time = datetime.now()
                meeting.save()

        elif event == 'recording.stopped':
            # Handle recording stopped event
            meeting_id = payload_data.get('object', {}).get('id')
            if meeting_id:
                meeting = Meeting.objects.get(meeting_id=meeting_id)
                meeting.recording_status = 'completed'
                meeting.recording_end_time = datetime.now()
                meeting.save()

        elif event == 'recording.completed':
            # Handle recording completed event
            meeting_id = payload_data.get('object', {}).get('id')
            recording_files = payload_data.get('object', {}).get('recording_files', [])

            if meeting_id and recording_files:
                meeting = Meeting.objects.get(meeting_id=meeting_id)
                
                for file in recording_files:
                    # Create recording object with Zoom URL
                    recording = Recording.objects.create(
                        meeting=meeting,
                        recording_url=file.get('download_url'),
                        recording_type=file.get('recording_type', 'video'),
                        file_size=file.get('file_size'),
                        duration=file.get('duration')
                    )

                    # Send notification to students
                    send_recording_notification(recording)

        return HttpResponse('Webhook processed successfully', status=200)

    except Meeting.DoesNotExist:
        print(f"Meeting not found for webhook: {payload_data.get('object', {}).get('id')}")
        return HttpResponse('Meeting not found', status=404)
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return HttpResponse('Internal server error', status=500) 