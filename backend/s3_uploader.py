import os
import requests
import boto3
from botocore.exceptions import ClientError
import json
from datetime import datetime
import logging
import tempfile
import time
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZoomRecordingS3Uploader:
    def __init__(self, aws_access_key=None, aws_secret_key=None, region_name='us-east-1'):
        """Initialize S3 client with AWS credentials"""
        logger.info("Initializing S3 uploader with AWS credentials")
        
        # Get credentials from parameters or environment variables
        access_key = aws_access_key or os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        region = region_name or os.getenv('AWS_REGION')
        
        if not access_key or not secret_key:
            logger.error("AWS credentials not found. Please check your environment variables.")
            raise ValueError("AWS credentials not found. Please check your environment variables.")
            
        logger.info(f"Using AWS Region: {region}")
        logger.info("AWS credentials found and validated")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        logger.info("S3 client initialized successfully")

    def download_zoom_recording(self, download_url: str) -> str:
        """Download recording from Zoom"""
        filename = None
        try:
            logger.info(f"Starting download from Zoom URL: {download_url}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Create downloads directory if it doesn't exist
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
                logger.info("Created downloads directory")
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"downloads/recording_{timestamp}.mp4"
            logger.info(f"Saving recording to: {filename}")
            
            # Save file
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Successfully downloaded recording to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error downloading recording: {str(e)}")
            # Clean up file if it exists
            if filename and os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Cleaned up failed download: {filename}")
            raise

    def upload_to_s3(self, bucket_name: str, file_path: str, recording_data: dict) -> str:
        """Upload recording to S3"""
        try:
            logger.info(f"Starting S3 upload for file: {file_path}")
            
            # Generate S3 key
            meeting_id = recording_data.get('meeting_id', 'unknown')
            recording_id = recording_data.get('id', 'unknown')
            s3_key = f"recordings/{meeting_id}/{recording_id}.mp4"
            logger.info(f"Generated S3 key: {s3_key}")
            
            # Upload file
            self.s3_client.upload_file(file_path, bucket_name, s3_key)
            logger.info(f"Successfully uploaded file to S3: {s3_key}")
            
            # Generate URL
            s3_url = f"https://{bucket_name}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_key}"
            logger.info(f"Generated S3 URL: {s3_url}")
            
            return s3_url
            
        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            raise

    def check_file_exists(self, bucket_name: str, key: str) -> bool:
        """Check if a file exists in S3 bucket"""
        try:
            logger.info(f"Checking if file exists in S3: {key}")
            self.s3_client.head_object(Bucket=bucket_name, Key=key)
            logger.info(f"File exists in S3: {key}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.info(f"File does not exist in S3: {key}")
                return False
            logger.error(f"Error checking file existence in S3: {str(e)}")
            raise

    def list_s3_videos(self, bucket_name: str) -> list:
        """List all video files in S3 bucket"""
        try:
            logger.info(f"Listing videos in S3 bucket: {bucket_name}")
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix='recordings/'
            )
            
            videos = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.mp4'):
                        videos.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat()
                        })
            
            logger.info(f"Found {len(videos)} videos in S3 bucket")
            return videos
            
        except Exception as e:
            logger.error(f"Error listing S3 videos: {str(e)}")
            return []

    def estimate_storage_cost(self, file_size_bytes):
        """
        Estimate S3 storage costs
        
        :param file_size_bytes: Size of the file in bytes
        :return: Estimated monthly storage cost
        """
        # Convert bytes to GB
        file_size_gb = file_size_bytes / (1024 ** 3)
        
        # S3 Standard pricing (as of 2024, may vary)
        # First 50 TB / month is $0.023 per GB
        monthly_cost = file_size_gb * 0.023
        
        return {
            'file_size_gb': round(file_size_gb, 2),
            'estimated_monthly_cost': f"${monthly_cost:.2f}"
        }

    def generate_presigned_url(self, bucket_name: str, key: str, expiration: int = 3600) -> str:
        """Generate a pre-signed URL for accessing an object"""
        try:
            logger.info(f"Generating pre-signed URL for: {key}")
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            logger.info(f"Generated pre-signed URL for: {key}")
            return url
        except Exception as e:
            logger.error(f"Error generating pre-signed URL: {str(e)}")
            raise 