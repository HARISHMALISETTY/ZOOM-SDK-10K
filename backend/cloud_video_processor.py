import os
import boto3
import logging
import uuid
from typing import Dict
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudVideoProcessor:
    def __init__(self, aws_access_key=None, aws_secret_key=None, region_name=None):
        """Initialize the cloud video processor."""
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.region_name = region_name or 'ap-south-1'
        
        # Create a session with AWS credentials
        session = boto3.Session(
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.region_name
        )
        
        # Get MediaConvert endpoint directly from environment variable
        endpoint_url = os.getenv('AWS_MEDIACONVERT_ENDPOINT')
        if not endpoint_url:
            raise ValueError("AWS_MEDIACONVERT_ENDPOINT environment variable is not set")
            
        # Initialize MediaConvert client with the endpoint
        self.mediaconvert_client = session.client(
            'mediaconvert',
            endpoint_url=endpoint_url,
            region_name=self.region_name
        )
        
        logger.info(f"Initialized MediaConvert client with endpoint: {endpoint_url}")
        
        # Get bucket names from environment
        self.upload_bucket = os.getenv('AWS_BUCKET_NAME')
        self.streaming_bucket = os.getenv('AWS_STREAMING_BUCKET')
        
        if not self.upload_bucket or not self.streaming_bucket:
            raise ValueError("AWS_BUCKET_NAME and AWS_STREAMING_BUCKET must be set in environment variables")
            
        logger.info(f"Initialized CloudVideoProcessor with upload bucket: {self.upload_bucket} and streaming bucket: {self.streaming_bucket}")

    def create_job(self, input_path, output_path):
        """Create a MediaConvert job."""
        try:
            logger.info(f"Creating MediaConvert job with input: {input_path} and output: {output_path}")
            
            job_settings = {
                "Queue": os.getenv('AWS_MEDIACONVERT_QUEUE', 'Default'),
                "Role": os.getenv('AWS_MEDIACONVERT_ROLE'),
                "Settings": {
                    "TimecodeConfig": {"Source": "ZEROBASED"},
                    "Inputs": [{
                        "TimecodeSource": "ZEROBASED",
                        "FileInput": input_path,
                        "AudioSelectors": {
                            "Audio Selector 1": {
                                "DefaultSelection": "DEFAULT"
                            }
                        },
                        "VideoSelector": {}
                    }],
                    "OutputGroups": [{
                        "Name": "Apple HLS",
                        "OutputGroupSettings": {
                            "Type": "HLS_GROUP_SETTINGS",
                            "HlsGroupSettings": {
                                "SegmentLength": 6,
                                "MinSegmentLength": 0,
                                "DirectoryStructure": "SINGLE_DIRECTORY",
                                "ManifestDurationFormat": "INTEGER",
                                "StreamInfResolution": "INCLUDE",
                                "ClientCache": "ENABLED",
                                "CaptionLanguageSetting": "OMIT",
                                "ManifestCompression": "NONE",
                                "CodecSpecification": "RFC_4281",
                                "OutputSelection": "MANIFESTS_AND_SEGMENTS",
                                "ProgramDateTime": "EXCLUDE",
                                "ProgramDateTimePeriod": 600,
                                "SegmentsPerSubdirectory": 1000,
                                "Destination": output_path + "/",
                                "KeepSegments": 90,
                                # Add settings for better handling of longer videos
                                "Mode": "VOD",
                                "HlsCacheFillPolicy": "ALL",
                                "IndexNSegments": 15,
                                "IframeOnlyManifest": "EXCLUDE"
                            }
                        },
                        "Outputs": [
                            {
                                "NameModifier": "_1080p",
                                "ContainerSettings": {
                                    "Container": "M3U8",
                                    "M3u8Settings": {
                                        "AudioFramesPerPes": 4,
                                        "PcrControl": "PCR_EVERY_PES_PACKET",
                                        "PmtPid": 480,
                                        "VideoPid": 481
                                    }
                                },
                                "VideoDescription": {
                                    "Width": 1920,
                                    "Height": 1080,
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "MaxBitrate": 8000000,
                                            "RateControlMode": "QVBR",
                                            "QvbrSettings": {
                                                "QvbrQualityLevel": 8
                                            },
                                            "GopSize": 90,
                                            "GopSizeUnits": "FRAMES",
                                            "ParControl": "INITIALIZE_FROM_SOURCE",
                                            "NumberReferenceFrames": 3,
                                            "EntropyEncoding": "CABAC",
                                            "FramerateControl": "INITIALIZE_FROM_SOURCE",
                                            "CodecProfile": "HIGH"
                                        }
                                    }
                                },
                                "AudioDescriptions": [{
                                    "CodecSettings": {
                                        "Codec": "AAC",
                                        "AacSettings": {
                                            "Bitrate": 192000,
                                            "CodingMode": "CODING_MODE_2_0",
                                            "SampleRate": 48000
                                        }
                                    }
                                }]
                            },
                            {
                                "NameModifier": "_720p",
                                "ContainerSettings": {
                                    "Container": "M3U8",
                                    "M3u8Settings": {
                                        "AudioFramesPerPes": 4,
                                        "PcrControl": "PCR_EVERY_PES_PACKET",
                                        "PmtPid": 480,
                                        "VideoPid": 481
                                    }
                                },
                                "VideoDescription": {
                                    "Width": 1280,
                                    "Height": 720,
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "MaxBitrate": 4000000,
                                            "RateControlMode": "QVBR",
                                            "QvbrSettings": {
                                                "QvbrQualityLevel": 7
                                            },
                                            "GopSize": 90,
                                            "GopSizeUnits": "FRAMES",
                                            "ParControl": "INITIALIZE_FROM_SOURCE",
                                            "NumberReferenceFrames": 3,
                                            "EntropyEncoding": "CABAC",
                                            "FramerateControl": "INITIALIZE_FROM_SOURCE",
                                            "CodecProfile": "HIGH"
                                        }
                                    }
                                },
                                "AudioDescriptions": [{
                                    "CodecSettings": {
                                        "Codec": "AAC",
                                        "AacSettings": {
                                            "Bitrate": 128000,
                                            "CodingMode": "CODING_MODE_2_0",
                                            "SampleRate": 48000
                                        }
                                    }
                                }]
                            },
                            {
                                "NameModifier": "_480p",
                                "ContainerSettings": {
                                    "Container": "M3U8",
                                    "M3u8Settings": {
                                        "AudioFramesPerPes": 4,
                                        "PcrControl": "PCR_EVERY_PES_PACKET",
                                        "PmtPid": 480,
                                        "VideoPid": 481
                                    }
                                },
                                "VideoDescription": {
                                    "Width": 854,
                                    "Height": 480,
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "MaxBitrate": 2000000,
                                            "RateControlMode": "QVBR",
                                            "QvbrSettings": {
                                                "QvbrQualityLevel": 7
                                            },
                                            "GopSize": 90,
                                            "GopSizeUnits": "FRAMES",
                                            "ParControl": "INITIALIZE_FROM_SOURCE",
                                            "NumberReferenceFrames": 3,
                                            "EntropyEncoding": "CABAC",
                                            "FramerateControl": "INITIALIZE_FROM_SOURCE",
                                            "CodecProfile": "MAIN"
                                        }
                                    }
                                },
                                "AudioDescriptions": [{
                                    "CodecSettings": {
                                        "Codec": "AAC",
                                        "AacSettings": {
                                            "Bitrate": 96000,
                                            "CodingMode": "CODING_MODE_2_0",
                                            "SampleRate": 48000
                                        }
                                    }
                                }]
                            }
                        ]
                    }]
                }
            }
            
            # Add error handling for job creation
            try:
                response = self.mediaconvert_client.create_job(**job_settings)
                job_id = response['Job']['Id']
                logger.info(f"Created MediaConvert job {job_id}")
                return job_id
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                logger.error(f"Error creating MediaConvert job: {error_code} - {error_message}")
                raise

        except Exception as e:
            logger.error(f"Error in create_job: {str(e)}")
            raise

    def get_job_status(self, job_id):
        """Get the status of a MediaConvert job."""
        try:
            response = self.mediaconvert_client.get_job(Id=job_id)
            return response['Job']['Status']
        except ClientError as e:
            logger.error(f"Error getting job status: {str(e)}")
            raise

    def process_video(self, input_key: str, meeting_id: str, recording_id: str) -> Dict:
        """Process video using AWS MediaConvert"""
        try:
            logger.info(f"Starting cloud video processing for {input_key}")
            
            # Define output path in streaming bucket
            output_path = f"s3://{self.streaming_bucket}/outputs/recordings/{meeting_id}/{recording_id}"
            input_path = f"s3://{self.upload_bucket}/{input_key}"
            
            logger.info(f"Input path: {input_path}")
            logger.info(f"Output path: {output_path}")
            
            # Create MediaConvert job
            job_id = self.create_job(input_path, output_path)
            
            return {
                'status': 'processing',
                'job_id': job_id,
                'output_path': f"outputs/recordings/{meeting_id}/{recording_id}",
                'streaming_url': f"{output_path}/master.m3u8"
            }
            
        except Exception as e:
            logger.error(f"Error in cloud video processing: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def check_job_status(self, job_id: str) -> Dict:
        """Check the status of a MediaConvert job"""
        try:
            status = self.get_job_status(job_id)
            
            return {
                'status': status.lower(),
                'job_details': {
                    'job_id': job_id,
                    'status': status
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking job status: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def upload_to_processing_bucket(self, file_path: str, meeting_id: str, recording_id: str) -> Dict:
        """Upload a file to the processing bucket"""
        try:
            # Generate S3 key
            file_extension = os.path.splitext(file_path)[1]
            s3_key = f"uploads/{meeting_id}/{recording_id}{file_extension}"
            
            # Upload file
            self.s3_client.upload_file(
                file_path,
                self.upload_bucket,
                s3_key
            )
            
            logger.info(f"Uploaded {file_path} to s3://{self.upload_bucket}/{s3_key}")
            
            return {
                'status': 'success',
                'bucket': self.upload_bucket,
                'key': s3_key
            }
            
        except Exception as e:
            logger.error(f"Error uploading to processing bucket: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            } 