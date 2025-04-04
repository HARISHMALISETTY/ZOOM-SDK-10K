from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import time
import logging
from datetime import datetime
from config import settings
import os
from dotenv import load_dotenv
from s3_uploader import ZoomRecordingS3Uploader
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Base, Meeting, Recording
from sqlalchemy import func
import boto3
from pydantic import BaseModel
from typing import Optional
import jwt
import hmac
import hashlib
import base64
import json

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Load environment variables
load_dotenv()

# Debug: Print current working directory and .env file location
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Looking for .env file in: {os.path.join(os.getcwd(), '.env')}")
logger.info(f".env file exists: {os.path.exists('.env')}")

# Log AWS credentials status (without exposing actual values)
logger.info("Checking AWS credentials...")
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION')
aws_bucket = os.getenv('AWS_BUCKET_NAME')

logger.info(f"AWS Region: {aws_region}")
logger.info(f"AWS Bucket: {aws_bucket}")
logger.info(f"AWS Access Key ID exists: {'Yes' if aws_access_key else 'No'}")
logger.info(f"AWS Secret Key exists: {'Yes' if aws_secret_key else 'No'}")

# Validate settings at startup
settings.validate()

app = FastAPI(title="Zoom Recordings API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize S3 uploader
s3_uploader = ZoomRecordingS3Uploader(
    aws_access_key=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)
logger.info("Initialized S3 uploader")

# AWS S3 Config
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

# S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=AWS_REGION
)

def get_access_token():
    """Get OAuth2 access token using client credentials"""
    url = "https://zoom.us/oauth/token"
    auth = (settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET)
    data = {
        "grant_type": "account_credentials",
        "account_id": settings.ZOOM_ACCOUNT_ID,
        "scope": "recording:read meeting:read meeting:write cloud_recording:read:list_recording_files cloud_recording:read:list_recording_files:admin"
    }
    
    logger.info(f"Requesting access token from Zoom API")
    response = requests.post(url, auth=auth, data=data)
    if response.status_code != 200:
        logger.error(f"Failed to get access token: {response.text}")
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to get access token: {response.text}"
        )
    logger.info("Successfully obtained access token")
    return response.json()["access_token"]

def get_host_info(host_id: str, access_token: str):
    """Get host information from Zoom API"""
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        url = f"https://api.zoom.us/v2/users/{host_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get host info: {response.text}")
            return None
            
        host_data = response.json()
        logger.info("=" * 50)
        logger.info("HOST INFORMATION FROM ZOOM:")
        logger.info(f"{host_data}")
        logger.info("=" * 50)
        return host_data
    except Exception as e:
        logger.error(f"Error getting host info: {str(e)}")
        return None

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Zoom Recordings API"}

@app.get("/api/recordings")
async def get_recordings_from_db(db: Session = Depends(get_db)):
    """Get recordings from database"""
    try:
        recordings = []
        db_recordings = db.query(Recording).all()
        
        logger.info(f"Found {len(db_recordings)} recordings in database")
        
        for rec in db_recordings:
            meeting = db.query(Meeting).filter(Meeting.id == rec.meeting_id).first()
            
            # Log detailed recording information
            logger.info("=" * 50)
            logger.info(f"Recording Details:")
            logger.info(f"ID: {rec.id}")
            logger.info(f"Recording ID: {rec.recording_id}")
            logger.info(f"Topic: {rec.topic or meeting.topic if meeting else 'Unknown'}")
            logger.info(f"Host Name: {rec.host_name}")
            logger.info(f"File Size: {rec.file_size or 0} bytes")
            logger.info(f"Created At: {rec.recording_start.isoformat() if rec.recording_start else 'Unknown'}")
            logger.info(f"Status: {rec.status}")
            logger.info(f"File Path: {rec.file_path}")
            
            recording_data = {
                "id": rec.id,
                "recording_id": rec.recording_id,
                "topic": rec.topic or meeting.topic if meeting else "Unknown",
                "host_name": rec.host_name,  # This will now be in format "First Name Last Name"
                "file_size": rec.file_size or 0,
                "created_at": rec.recording_start.isoformat() if rec.recording_start else None,
                "status": rec.status,
                "recording_type": rec.recording_type,
                "file_type": rec.file_type,
                "file_path": rec.file_path
            }
            recordings.append(recording_data)
            logger.info("=" * 50)
        
        logger.info(f"Successfully processed {len(recordings)} recordings")
        return recordings
    except Exception as e:
        logger.error(f"Error fetching recordings from database: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching recordings: {str(e)}"
        )

@app.get("/api/recordings/stats")
async def get_recordings_stats(db: Session = Depends(get_db)):
    """Get recordings statistics"""
    try:
        # Get all recordings
        recordings = db.query(Recording).all()
        
        # Calculate statistics
        total_recordings = len(recordings)
       
        total_storage = sum(rec.file_size or 0 for rec in recordings)
        total_hosts = db.query(Recording.host_name).distinct().count()
        
        # Get recordings by topic
        recordings_by_topic = db.query(
            Recording.topic,
            func.count(Recording.id).label('count')
        ).group_by(Recording.topic).all()
        
        logger.info(f"Stats calculated: {total_recordings} recordings, {total_storage} bytes storage, {total_hosts} hosts")
        
        return {
            "totalRecordings": total_recordings,
            "totalStorage": total_storage,
            "totalHosts": total_hosts,
            "recordingsByTopic": [
                {"topic": topic, "count": count}
                for topic, count in recordings_by_topic
            ]
        }
    except Exception as e:
        logger.error(f"Error calculating stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating statistics: {str(e)}"
        )

@app.get("/recordings/{recording_id}")
async def get_recording_by_id(
    recording_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific recording by ID
    """
    recording = db.query(Recording).filter(Recording.recording_id == recording_id).first()
    if not recording: 
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording

def process_recording_file(recording: dict, meeting: dict, host_name: str, access_token: str, db: Session, s3_uploader: ZoomRecordingS3Uploader) -> dict:
    """Shared function to process a single recording file"""
    try:
        recording_id = recording.get('id', '')
        meeting_topic = meeting.get('topic', '')
        meeting_id = str(meeting.get('id', ''))
        
        # Check if recording already exists
        existing_recording = db.query(Recording).filter(Recording.recording_id == recording_id).first()
        if existing_recording:
            logger.info(f"Recording {recording_id} already exists in database, skipping...")
            return {
                'id': recording_id,
                'topic': meeting_topic,
                'status': 'skipped'
            }
        
        # Create or update meeting in database
        db_meeting = db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()
        if not db_meeting:
            logger.info(f"Creating new meeting record: {meeting_topic}")
            db_meeting = Meeting(
                meeting_id=meeting_id,
                topic=meeting_topic,
                host_id=meeting.get('host_id', ''),
                start_time=datetime.fromisoformat(meeting.get('start_time', '').replace("Z", "+00:00")),
                uuid=meeting.get('uuid', '')
            )
            db.add(db_meeting)
            db.commit()
            db.refresh(db_meeting)
            logger.info(f"Created new meeting record: {meeting_topic}")
        
        # Store the recording in database
        db_recording = Recording(
            meeting_id=db_meeting.id,
            recording_id=recording_id,
            topic=meeting_topic,
            host_name=host_name,
            file_type=recording.get('file_type', 'MP4'),
            file_extension=recording.get('file_extension', '.mp4'),
            file_size=recording.get('file_size', 0),
            recording_start=datetime.fromisoformat(recording.get('recording_start', '').replace("Z", "+00:00")),
            recording_end=datetime.fromisoformat(recording.get('recording_end', '').replace("Z", "+00:00")),
            recording_type=recording.get('recording_type', 'shared_screen_with_speaker_view'),
            file_path=f"recordings/{meeting.get('uuid', '')}/{recording_id}.mp4",
            status='pending'
        )
        db.add(db_recording)
        db.commit()
        logger.info(f"Added new recording to database: {recording_id}")
        
        # Process the recording file
        s3_key = db_recording.file_path
        file_extension = recording.get('file_extension', '').upper()
        logger.info(f"Processing file with extension: {file_extension}")
        
        if file_extension == 'MP4' and not s3_uploader.check_file_exists(os.getenv('AWS_BUCKET_NAME'), s3_key):
            try:
                download_url = recording.get('download_url')
                if not download_url:
                    logger.warning(f"No download URL found for recording: {recording_id}")
                    return {
                        'id': recording_id,
                        'topic': meeting_topic,
                        'status': 'error',
                        'error': 'No download URL found'
                    }

                download_url = f"{download_url}?access_token={access_token}"
                logger.info(f"Downloading recording: {recording_id}")
                
                downloaded_file = s3_uploader.download_zoom_recording(download_url)
                if downloaded_file:
                    logger.info(f"Successfully downloaded recording: {recording_id}")
                    
                    try:
                        s3_uploader.upload_to_s3(
                            bucket_name=os.getenv('AWS_BUCKET_NAME'),
                            file_path=downloaded_file,
                            recording_data=recording
                        )
                        logger.info(f"Successfully uploaded to S3: {s3_key}")
                        
                        db_recording.status = 'completed'
                        db.commit()
                        
                        return {
                            'id': recording_id,
                            'topic': meeting_topic,
                            'status': 'processed'
                        }
                        
                    finally:
                        if os.path.exists(downloaded_file):
                            os.remove(downloaded_file)
                            logger.info(f"Cleaned up downloaded file: {downloaded_file}")
            except Exception as e:
                logger.error(f"Error processing recording {recording_id}: {str(e)}")
                db_recording.status = 'error'
                db_recording.error_message = str(e)
                db.commit()
                return {
                    'id': recording_id,
                    'topic': meeting_topic,
                    'status': 'error',
                    'error': str(e)
                }
        else:
            if file_extension != 'MP4':
                logger.info(f"Skipping non-MP4 file: {recording_id} with extension {file_extension}")
                return {
                    'id': recording_id,
                    'topic': meeting_topic,
                    'status': 'skipped',
                    'reason': 'Non-MP4 file'
                }
            else:
                db_recording.status = 'completed'
                db.commit()
                logger.info(f"Recording {recording_id} already exists in S3, updated status to completed")
                return {
                    'id': recording_id,
                    'topic': meeting_topic,
                    'status': 'processed'
                }
                
    except Exception as e:
        logger.error(f"Error in process_recording_file: {str(e)}")
        return {
            'id': recording_id,
            'topic': meeting_topic,
            'status': 'error',
            'error': str(e)
        }

@app.post("/api/recordings/process")
async def process_recordings(db: Session = Depends(get_db)):
    try:
        logger.info("Starting recordings processing workflow")
        
        # Get access token for Zoom API
        access_token = get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get user information
        user_url = "https://api.zoom.us/v2/users/me"
        user_response = requests.get(user_url, headers=headers)
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=user_response.status_code,
                detail=f"Failed to get user info: {user_response.text}"
            )
        
        user_data = user_response.json()
        user_id = user_data['id']
        
        # Get recordings list
        recordings_url = f"https://api.zoom.us/v2/users/{user_id}/recordings"
        recordings_response = requests.get(recordings_url, headers=headers)
        if recordings_response.status_code != 200:
            raise HTTPException(
                status_code=recordings_response.status_code,
                detail=f"Failed to get recordings: {recordings_response.text}"
            )
        
        response_data = recordings_response.json()
        meetings = response_data.get('meetings', [])
        logger.info(f"Found {len(meetings)} meetings with recordings")
        
        processed_recordings = []
        skipped_recordings = []
        
        for meeting in meetings:
            meeting_topic = meeting.get('topic', '')
            host_id = meeting.get('host_id', '')
            
            # Get host information
            host_info = get_host_info(host_id, access_token)
            host_name = f"{host_info.get('first_name', '')} {host_info.get('last_name', '')}".strip() if host_info else meeting.get('host_name', 'Unknown')
            
            recording_files = meeting.get('recording_files', [])
            for recording in recording_files:
                if recording.get('status') != 'completed':
                    continue
                    
                result = process_recording_file(recording, meeting, host_name, access_token, db, s3_uploader)
                if result['status'] == 'processed':
                    processed_recordings.append(result)
                elif result['status'] == 'skipped':
                    skipped_recordings.append(result)
        
        return {
            "message": f"Processed {len(processed_recordings)} new recordings, skipped {len(skipped_recordings)} existing recordings",
            "processed_recordings": processed_recordings,
            "skipped_recordings": skipped_recordings
        }
        
    except Exception as e:
        logger.error(f"Error processing recordings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing recordings: {str(e)}"
        )

@app.get("/api/s3-videos")
async def get_s3_videos():
    """Get list of videos from S3 bucket"""
    try:
        videos = s3_uploader.list_s3_videos(os.getenv('AWS_BUCKET_NAME'))
        return {
            "total_videos": len(videos),
            "videos": videos
        }
    except Exception as e:
        logger.error(f"Error getting S3 videos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting S3 videos: {str(e)}"
        )

@app.get("/api/recordings/get-signed-url/{recording_id}")
def get_signed_url(recording_id: str, db: Session = Depends(get_db)):
    """Get a pre-signed URL for a recording"""
    try:
        # Fetch the recording from the database
        db_recording = db.query(Recording).filter(Recording.recording_id == recording_id).first()
        if not db_recording:
            raise HTTPException(status_code=404, detail="Recording not found")

        # Use the stored file path as the S3 key
        s3_key = db_recording.file_path

        logger.info(f"Generating pre-signed URL for recording: {recording_id}")
        logger.info(f"S3 Key: {s3_key}")

        # Generate a pre-signed URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': AWS_BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600  # URL expires in 1 hour
        )

        logger.info(f"Successfully generated pre-signed URL for recording: {recording_id}")
        return {"presigned_url": presigned_url}

    except Exception as e:
        logger.error(f"Error generating pre-signed URL for recording {recording_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating pre-signed URL: {str(e)}")

class MeetingSchedule(BaseModel):
    topic: str
    start_time: str
    
    timezone: str = "UTC"
    settings: Optional[dict] = {
        "host_video": True,
        "participant_video": True,
        "join_before_host": False,
        "mute_upon_entry": True,
        "waiting_room": True,
        "meeting_authentication": True,
        "recording_consent": True
    }

@app.post("/api/meetings/schedule")
async def schedule_meeting(meeting: MeetingSchedule, db: Session = Depends(get_db)):
    """Schedule a new Zoom meeting"""
    try:
        logger.info("Starting meeting scheduling workflow")
        
        # Get access token for Zoom API
        access_token = get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get user information
        user_url = "https://api.zoom.us/v2/users/me"
        user_response = requests.get(user_url, headers=headers)
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=user_response.status_code,
                detail=f"Failed to get user info: {user_response.text}"
            )
        
        user_data = user_response.json()
        user_id = user_data['id']
        
        # Schedule meeting
        schedule_url = f"https://api.zoom.us/v2/users/{user_id}/meetings"
        schedule_data = {
            "topic": meeting.topic,
            "type": 2,  # Scheduled meeting
            "start_time": meeting.start_time,
           
            "timezone": meeting.timezone,
            "settings": meeting.settings
        }
        
        schedule_response = requests.post(schedule_url, headers=headers, json=schedule_data)
        if schedule_response.status_code != 201:
            raise HTTPException(
                status_code=schedule_response.status_code,
                detail=f"Failed to schedule meeting: {schedule_response.text}"
            )
        
        meeting_data = schedule_response.json()
        
        # Store meeting in database
        db_meeting = Meeting(
            meeting_id=str(meeting_data['id']),
            topic=meeting_data['topic'],
            host_id=meeting_data['host_id'],
            start_time=datetime.fromisoformat(meeting_data['start_time'].replace("Z", "+00:00")),
            
            uuid=meeting_data['uuid']
        )
        db.add(db_meeting)
        db.commit()
        db.refresh(db_meeting)
        
        logger.info(f"Successfully scheduled meeting: {meeting_data['topic']}")
        return {
            "message": "Meeting scheduled successfully",
            "meeting": {
                "id": meeting_data['id'],
                "topic": meeting_data['topic'],
                "start_time": meeting_data['start_time'],
                "join_url": meeting_data['join_url'],
                "host_email": meeting_data['host_email'],
                "status": meeting_data['status']
            }
        }
        
    except Exception as e:
        logger.error(f"Error scheduling meeting: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error scheduling meeting: {str(e)}"
        )

@app.get("/api/meetings/sync")
def sync_meetings_from_zoom(db: Session = Depends(get_db)):
    try:
        logger.info("Starting meetings sync from Zoom for today's meetings")
        
        # Get access token
        access_token = get_access_token()
        logger.info("Successfully obtained access token")
        
        # Get user info
        user_response = requests.get(
            "https://api.zoom.us/v2/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_response.status_code != 200:
            logger.error(f"Failed to get user info: {user_response.text}")
            raise HTTPException(
                status_code=user_response.status_code, 
                detail=f"Failed to get user info: {user_response.text}"
            )
        
        user_data = user_response.json()
        host_id = user_data.get("id")
        logger.info(f"Successfully got user info for host ID: {host_id}")
        
        # Get today's date in UTC
        today = datetime.utcnow().date()
        
        # Get meetings from Zoom API
        meetings_url = f"https://api.zoom.us/v2/users/{host_id}/meetings"
        meetings_response = requests.get(
            meetings_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if meetings_response.status_code != 200:
            logger.error(f"Failed to get meetings from Zoom: {meetings_response.text}")
            raise HTTPException(
                status_code=meetings_response.status_code, 
                detail=f"Failed to get meetings from Zoom: {meetings_response.text}"
            )
        
        all_meetings = meetings_response.json().get("meetings", [])
        
        # Filter for today's meetings only
        today_meetings = []
        for meeting in all_meetings:
            try:
                meeting_start = datetime.fromisoformat(meeting["start_time"].replace("Z", "+00:00"))
                if meeting_start.date() == today:
                    today_meetings.append(meeting)
            except Exception as e:
                logger.error(f"Error processing meeting date: {str(e)}")
                continue
        
        logger.info(f"Found {len(today_meetings)} meetings for today")
        
        # Store today's meetings in database
        for meeting in today_meetings:
            try:
                # Check if meeting already exists
                existing_meeting = db.query(Meeting).filter(Meeting.meeting_id == str(meeting["id"])).first()
                
                if not existing_meeting:
                    # Create new meeting record
                    db_meeting = Meeting(
                        meeting_id=str(meeting["id"]),
                        topic=meeting["topic"],
                        start_time=datetime.fromisoformat(meeting["start_time"].replace("Z", "+00:00")),
                        duration=meeting.get("duration", 60),
                        timezone=meeting.get("timezone", "UTC"),
                        host_id=host_id,
                        join_url=meeting.get("join_url", ""),
                        password=meeting.get("password", ""),
                        status="scheduled",
                        uuid=meeting.get("uuid", "")
                    )
                    db.add(db_meeting)
                    logger.info(f"Added new meeting to database: {meeting['topic']}")
                else:
                    # Update existing meeting
                    existing_meeting.topic = meeting["topic"]
                    existing_meeting.start_time = datetime.fromisoformat(meeting["start_time"].replace("Z", "+00:00"))
                    existing_meeting.duration = meeting.get("duration", 60)
                    existing_meeting.timezone = meeting.get("timezone", "UTC")
                    existing_meeting.join_url = meeting.get("join_url", "")
                    existing_meeting.password = meeting.get("password", "")
                    existing_meeting.status = "scheduled"
                    logger.info(f"Updated existing meeting in database: {meeting['topic']}")
            except Exception as e:
                logger.error(f"Error processing meeting {meeting.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Commit all changes to database
        db.commit()
        logger.info("Successfully synced today's meetings from Zoom to database")
        
        # Verify the meetings were stored
        stored_meetings = db.query(Meeting).filter(
            func.date(Meeting.start_time) == today
        ).all()
        logger.info(f"Total meetings in database for today: {len(stored_meetings)}")
        
        return {
            "message": "Today's meetings synced successfully",
            "count": len(today_meetings),
            "stored_count": len(stored_meetings),
            "meetings": today_meetings
        }
        
    except Exception as e:
        logger.error(f"Error syncing meetings from Zoom: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/meetings")
def get_meetings_from_db(db: Session = Depends(get_db)):
    try:
        # Get all meetings from database
        meetings = db.query(Meeting).all()
        return meetings
    except Exception as e:
        logger.error(f"Error fetching meetings from database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/meetings/{meeting_id}")
async def update_meeting(meeting_id: int, meeting: MeetingSchedule, db: Session = Depends(get_db)):
    """Update an existing meeting"""
    try:
        logger.info(f"Starting meeting update workflow for meeting ID: {meeting_id}")
        
        # Get the meeting from database
        db_meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Get access token for Zoom API
        access_token = get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Update meeting in Zoom
        update_url = f"https://api.zoom.us/v2/meetings/{db_meeting.meeting_id}"
        update_data = {
            "topic": meeting.topic,
            "start_time": meeting.start_time,
            "timezone": meeting.timezone,
            "settings": meeting.settings
        }
        
        update_response = requests.patch(update_url, headers=headers, json=update_data)
        if update_response.status_code != 204:
            raise HTTPException(
                status_code=update_response.status_code,
                detail=f"Failed to update meeting in Zoom: {update_response.text}"
            )
        
        # Update meeting in database
        db_meeting.topic = meeting.topic
        db_meeting.start_time = datetime.fromisoformat(meeting.start_time.replace("Z", "+00:00"))
        db.commit()
        db.refresh(db_meeting)
        
        logger.info(f"Successfully updated meeting: {meeting.topic}")
        return {
            "message": "Meeting updated successfully",
            "meeting": {
                "id": db_meeting.id,
                "topic": db_meeting.topic,
                "start_time": db_meeting.start_time.isoformat(),
                "meeting_id": db_meeting.meeting_id
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating meeting: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating meeting: {str(e)}"
        )

@app.get("/api/meetings/{meeting_id}/status")
async def get_meeting_status(meeting_id: str, db: Session = Depends(get_db)):
    """Get the current status of a meeting from Zoom"""
    try:
        # Get the meeting from database
        db_meeting = db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        # Get access token for Zoom API
        access_token = get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Get meeting details from Zoom
        meeting_url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
        meeting_response = requests.get(meeting_url, headers=headers)
        
        if meeting_response.status_code != 200:
            raise HTTPException(
                status_code=meeting_response.status_code,
                detail=f"Failed to get meeting status: {meeting_response.text}"
            )

        meeting_data = meeting_response.json()
        
        # Get meeting participants
        participants_url = f"https://api.zoom.us/v2/metrics/meetings/{meeting_id}/participants"
        participants_response = requests.get(participants_url, headers=headers)
        
        is_active = False
        participant_count = 0
        
        if participants_response.status_code == 200:
            participants_data = participants_response.json()
            is_active = participants_data.get('in_meeting', False)
            participants = participants_data.get('participants', [])
            participant_count = len(participants) if isinstance(participants, list) else 0

        return {
            "meeting_id": meeting_id,
            "topic": meeting_data.get('topic'),
            "status": meeting_data.get('status'),
            "is_active": is_active,
            "participant_count": participant_count,
            "start_time": meeting_data.get('start_time'),
            "duration": meeting_data.get('duration'),
            "host_id": meeting_data.get('host_id'),
            "join_url": meeting_data.get('join_url')
        }

    except Exception as e:
        logger.error(f"Error getting meeting status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting meeting status: {str(e)}"
        )

def generate_meeting_token(meeting_number: str, role: int = 1):
    """Generate a meeting token for Zoom Web SDK"""
    try:
        # Get current timestamp
        iat = int(time.time())
        exp = iat + 3600  # Token expires in 1 hour

        # Prepare the payload
        payload = {
            "sdkKey": settings.ZOOM_CLIENT_ID,
            "mn": meeting_number,
            "role": role,  # 1 for host, 0 for participant
            "iat": iat,
            "exp": exp,
            "tokenExp": exp
        }

        # Generate the token
        token = jwt.encode(payload, settings.ZOOM_CLIENT_SECRET, algorithm='HS256')
        return token

    except Exception as e:
        logger.error(f"Error generating meeting token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating meeting token: {str(e)}"
        )

@app.get("/api/meetings/{meeting_id}/start-token")
async def get_meeting_token(meeting_id: str, db: Session = Depends(get_db)):
    """Get a meeting token for starting a meeting"""
    try:
        logger.info(f"Generating token for meeting: {meeting_id}")
        
        # Get the meeting from database
        db_meeting = db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()
        if not db_meeting:
            logger.error(f"Meeting not found: {meeting_id}")
            raise HTTPException(status_code=404, detail="Meeting not found")

        # Get access token
        access_token = get_access_token()
        
        # Get meeting details from Zoom
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get meeting details
        meeting_response = requests.get(
            f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers=headers
        )
        
        if meeting_response.status_code != 200:
            logger.error(f"Failed to get meeting details: {meeting_response.text}")
            raise HTTPException(status_code=500, detail="Failed to get meeting details")

        meeting_data = meeting_response.json()
        
        # Generate meeting token
        token = generate_meeting_token(meeting_id, role=1)  # 1 for host
        logger.info(f"Generated token for meeting {meeting_id}")

        response_data = {
            "signature": token,
            "meeting_number": meeting_id,
            "password": meeting_data.get('password', ''),
            "host_name": meeting_data.get('host_name', ''),
            "topic": meeting_data.get('topic', '')
        }
        logger.info(f"Returning token data: {response_data}")
        return response_data

    except Exception as e:
        logger.error(f"Error getting meeting token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting meeting token: {str(e)}"
        )

@app.get("/api/meetings/{meeting_id}/join-url")
def get_meeting_join_url(meeting_id: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"Getting host start URL for meeting ID: {meeting_id}")
        
        # Get meeting from database
        meeting = db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()
        if not meeting:
            logger.error(f"Meeting not found in database: {meeting_id}")
            raise HTTPException(status_code=404, detail="Meeting not found")

        logger.info(f"Found meeting in database: {meeting.meeting_id}")
        
        # Get access token
        access_token = get_access_token()
        
        # Get meeting details from Zoom API
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Get meeting details
        response = requests.get(
            f"https://api.zoom.us/v2/meetings/{meeting_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Zoom API error: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Failed to get meeting details from Zoom: {response.text}")
        
        meeting_data = response.json()
        logger.info(f"Successfully got meeting data from Zoom: {meeting_data.get('topic')}")
        
        # Return the start URL for host
        return {
            "join_url": meeting_data.get("start_url"),  # Changed from join_url to start_url
            "meeting_id": meeting_id,
            "password": meeting_data.get("password", "")
        }
        
    except Exception as e:
        logger.error(f"Error getting meeting start URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class ZoomWebhookPayload(BaseModel):
    event: str
    payload: dict

@app.post("/api/webhooks/zoom")
async def zoom_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        # Get the request body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Check for Zoom's validation request
        if body_str == '{"event":"endpoint.url_validation"}':
            # This is a validation request from Zoom
            return {
                "plainToken": "plainToken",
                "encryptedToken": hmac.new(
                    os.getenv('ZOOM_WEBHOOK_SECRET').encode('utf-8'),
                    "plainToken".encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
            }

        # Verify webhook signature for actual webhook events
        webhook_secret = os.getenv('ZOOM_WEBHOOK_SECRET')
        if not webhook_secret:
            raise HTTPException(status_code=500, detail="Webhook secret not configured")

        signature = request.headers.get('x-zm-signature')
        if not signature:
            raise HTTPException(status_code=401, detail="No signature found")

        # Verify signature
        timestamp = signature.split('&')[0].split('=')[1]
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            f"{timestamp}&{body_str}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if signature.split('&')[1].split('=')[1] != expected_signature:
            raise HTTPException(status_code=401, detail="Invalid signature")

        webhook_data = json.loads(body_str)
        logger.info(f"Received webhook: {webhook_data}")

        if webhook_data.get('event') == 'recording.completed':
            payload = webhook_data.get('payload', {})
            object = payload.get('object', {})
            
            # Get access token
            access_token = get_access_token()
            
            # Get host information
            host_id = object.get('host_id')
            host_info = get_host_info(host_id, access_token)
            host_name = f"{host_info.get('first_name', '')} {host_info.get('last_name', '')}".strip() if host_info else object.get('host_name', 'Unknown')
            
            # Process each recording file
            recording_files = object.get('recording_files', [])
            for recording in recording_files:
                if recording.get('status') != 'completed':
                    continue
                    
                result = process_recording_file(recording, object, host_name, access_token, db, s3_uploader)
                logger.info(f"Processed recording: {result}")
            
            return {"message": "Recording processed successfully"}
        
        return {"message": "Webhook received but not a recording completion event"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/webhooks/zoom/test")
async def test_webhook(db: Session = Depends(get_db)):
    """Test endpoint for webhook that simulates a recording completion event"""
    try:
        # Simulate a recording completion webhook payload
        test_payload = {
            "event": "recording.completed",
            "payload": {
                "object": {
                    "id": "123456789",
                    "topic": "Test Meeting",
                    "host_id": "test_host",
                    "host_name": "Test Host",
                    "start_time": "2024-01-01T00:00:00Z",
                    "uuid": "test-uuid-123",
                    "recording_files": [
                        {
                            "id": "rec_123",
                            "status": "completed",
                            "file_type": "MP4",
                            "file_extension": ".mp4",
                            "file_size": 1024,
                            "recording_start": "2024-01-01T00:00:00Z",
                            "recording_end": "2024-01-01T01:00:00Z",
                            "recording_type": "shared_screen_with_speaker_view",
                            "download_url": "https://example.com/download"
                        }
                    ]
                }
            }
        }
        
        # Get access token
        access_token = get_access_token()
        
        # Process the test recording
        result = process_recording_file(
            test_payload["payload"]["object"]["recording_files"][0],
            test_payload["payload"]["object"],
            test_payload["payload"]["object"]["host_name"],
            access_token,
            db,
            s3_uploader
        )
        
        return {
            "message": "Test webhook processed successfully",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error processing test webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing test webhook: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    import subprocess
    import threading
    import time
    
    def start_ngrok():
        try:
            # Start ngrok in a separate process
            subprocess.run(['ngrok', 'http', '8001'])
        except Exception as e:
            logger.error(f"Error starting ngrok: {str(e)}")
    
    # Start ngrok in a separate thread
    ngrok_thread = threading.Thread(target=start_ngrok)
    ngrok_thread.daemon = True  # This ensures the thread will be killed when the main program exits
    ngrok_thread.start()
    
    # Give ngrok a moment to start
    time.sleep(2)
    
    # Start the FastAPI server
    logger.info("Starting Zoom Recordings API server")
    uvicorn.run(app, host="0.0.0.0", port=8001) 