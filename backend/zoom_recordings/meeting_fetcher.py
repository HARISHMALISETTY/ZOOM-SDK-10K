import requests
import base64
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zoom_meetings.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

class ZoomMeetingFetcher:
    def __init__(self):
        """
        Initialize Zoom API credentials from environment variables
        """
        self.account_id = os.getenv('ZOOM_ACCOUNT_ID')
        self.client_id = os.getenv('ZOOM_CLIENT_ID')
        self.client_secret = os.getenv('ZOOM_CLIENT_SECRET')
        self.access_token = None
        
        if not all([self.account_id, self.client_id, self.client_secret]):
            raise ValueError("Missing Zoom credentials in environment variables")
        
        logging.info("ZoomMeetingFetcher initialized with credentials")
        
    def _get_access_token(self):
        """
        Obtain OAuth access token from Zoom API
        
        :return: Access token string
        """
        logging.info("Getting Zoom access token...")
        # Encode credentials for basic authentication
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        # Prepare headers and payload
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        payload = {
            'grant_type': 'account_credentials',
            'account_id': self.account_id
        }
        
        # Make token request
        response = requests.post(
            'https://zoom.us/oauth/token', 
            headers=headers, 
            data=payload
        )
        
        if response.status_code == 200:
            # logging.info("Successfully obtained access token")
            return response.json()['access_token']
        else:
            error_msg = f"Failed to obtain access token: {response.text}"
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def fetch_meetings(self):
        """
        Fetch all scheduled meetings and organize them by date
        :return: Dictionary of meetings organized by date
        """
        logging.info("Starting to fetch all scheduled meetings...")
        # Ensure access token is valid
        if not self.access_token:
            self.access_token = self._get_access_token()
        
        # Prepare headers
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Make API request to fetch meetings
        response = requests.get(
            'https://api.zoom.us/v2/users/me/meetings', 
            headers=headers
        )
        
        if response.status_code == 200:
            meetings = response.json().get('meetings', [])
            logging.info(f"Successfully fetched {len(meetings)} meetings from Zoom")
            
            # Organize meetings by date
            meetings_by_date = defaultdict(list)
            
            for meeting in meetings:
                # Get meeting start time and convert to date
                start_time = meeting.get('start_time')
                if start_time:
                    try:
                        # Convert Zoom's ISO format to datetime
                        meeting_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        meeting_date = meeting_datetime.strftime('%Y-%m-%d')
                        
                        # Process meeting details
                        meeting_details = {
                            'meeting_id': meeting.get('id'),
                            'topic': meeting.get('topic'),
                            'start_time': start_time,
                            'duration': meeting.get('duration'),
                            'join_url': meeting.get('join_url'),
                            'host_email': meeting.get('host_email'),
                            'status': meeting.get('status'),
                            'type': meeting.get('type'),
                            'settings': meeting.get('settings', {}),
                            'time': meeting_datetime.strftime('%H:%M'),
                            'is_recurring': meeting.get('type') == 8,
                            'recurrence': meeting.get('recurrence', {}) if meeting.get('type') == 8 else None
                        }
                        
                        # Log meeting details
                        logging.info(f"\nMeeting Details:")
                        logging.info(f"Date: {meeting_date}")
                        logging.info(f"Time: {meeting_details['time']}")
                        logging.info(f"Topic: {meeting_details['topic']}")
                        logging.info(f"Duration: {meeting_details['duration']} minutes")
                        logging.info(f"Status: {meeting_details['status']}")
                        logging.info(f"Type: {'Recurring' if meeting_details['is_recurring'] else 'One-time'}")
                        if meeting_details['is_recurring']:
                            logging.info(f"Recurrence: {json.dumps(meeting_details['recurrence'], indent=2)}")
                        logging.info(f"Join URL: {meeting_details['join_url']}")
                        logging.info("-" * 50)
                        
                        # Add to meetings_by_date dictionary
                        meetings_by_date[meeting_date].append(meeting_details)
                    except Exception as e:
                        logging.error(f"Error processing meeting {meeting.get('id')}: {str(e)}")
                        continue
            
            # Convert defaultdict to regular dict and sort dates
            meetings_by_date = dict(sorted(meetings_by_date.items()))
            
            # Sort meetings within each date by start time
            for date in meetings_by_date:
                meetings_by_date[date].sort(key=lambda x: x['start_time'])
            
            logging.info(f"\nTotal meetings organized by {len(meetings_by_date)} dates")
            for date, meetings in meetings_by_date.items():
                logging.info(f"{date}: {len(meetings)} meetings")
            
            return meetings_by_date
        else:
            error_msg = f"Failed to fetch meetings: {response.text}"
            logging.error(error_msg)
            raise Exception(error_msg) 