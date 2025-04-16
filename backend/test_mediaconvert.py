import os
import boto3
import logging
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_mediaconvert_client():
    """Get MediaConvert client with proper endpoint"""
    endpoint_url = os.getenv('AWS_MEDIACONVERT_ENDPOINT')
    if not endpoint_url:
        logger.error("AWS_MEDIACONVERT_ENDPOINT not set in environment variables")
        return None
        
    return boto3.client('mediaconvert',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
        region_name=os.getenv('AWS_REGION'),
        endpoint_url=endpoint_url
    )

def list_recent_jobs():
    """List recent MediaConvert jobs"""
    client = get_mediaconvert_client()
    if not client:
        return
        
    try:
        response = client.list_jobs(
            MaxResults=10,
            Order='DESCENDING',
            Status='ALL'
        )
        
        if 'Jobs' in response:
            logger.info("Recent MediaConvert jobs:")
            for job in response['Jobs']:
                logger.info(f"Job ID: {job['Id']}")
                logger.info(f"Status: {job['Status']}")
                logger.info(f"Created: {job['CreatedAt']}")
                if 'Settings' in job and 'OutputGroups' in job['Settings']:
                    logger.info(f"Output Group: {job['Settings']['OutputGroups'][0]['Name']}")
                logger.info("---")
        else:
            logger.info("No recent jobs found")
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")

def check_s3_files(bucket, prefix):
    """Check if HLS files exist in S3"""
    s3 = boto3.client('s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    
    try:
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        if 'Contents' in response:
            logger.info("Found files in S3:")
            for obj in response['Contents']:
                logger.info(f"- {obj['Key']}")
            return True
        else:
            logger.info("No files found in S3")
            return False
    except Exception as e:
        logger.error(f"Error checking S3 files: {str(e)}")
        return False

def create_mediaconvert_job(input_video):
    """Create a MediaConvert job for video transcoding."""
    client = get_mediaconvert_client()
    if not client:
        return None
        
    # Get credentials from environment
    mediaconvert_role = os.getenv('AWS_MEDIACONVERT_ROLE')
    input_bucket = os.getenv('AWS_BUCKET_NAME')
    output_bucket = os.getenv('AWS_STREAMING_BUCKET')

    # Extract meeting ID and recording ID from input path
    path_parts = input_video.split('/')
    meeting_id = path_parts[1]  # JOgWA
    recording_id = path_parts[3].split('.')[0]  # 18eccf02-67c9-4cbb-ae91-2abbb8df414e
    
    # Define output path with quality levels
    output_path = f"recordings/{meeting_id}/{recording_id}"

    # Job settings
    job_settings = {
        "Queue": "Default",
        "Role": mediaconvert_role,
        "Settings": {
            "Inputs": [{
                "FileInput": f"s3://{input_bucket}/{input_video}",
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
                        "SegmentLength": 10,
                        "MinSegmentLength": 0,
                        "DirectoryStructure": "SINGLE_DIRECTORY",
                        "Destination": f"s3://{output_bucket}/{output_path}/",
                        "ManifestDurationFormat": "INTEGER",
                        "ProgramDateTime": "EXCLUDE",
                        "TimedMetadataId3Frame": "PRIV",
                        "TimedMetadataId3Period": 10,
                        "CaptionLanguageMappings": [],
                        "CaptionLanguageSetting": "OMIT",
                        "DestinationSettings": {
                            "S3Settings": {
                                "AccessControl": {
                                    "CannedAcl": "PUBLIC_READ"
                                }
                            }
                        }
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
                                "PrivateMetadataPid": 503,
                                "ProgramNumber": 1,
                                "PatInterval": 0,
                                "PmtInterval": 0,
                                "Scte35Source": "NONE",
                                "TimedMetadata": "NONE",
                                "TimedMetadataPid": 502,
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
                                    }
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
                    },
                    {
                        "NameModifier": "_720p",
                        "ContainerSettings": {
                            "Container": "M3U8",
                            "M3u8Settings": {
                                "AudioFramesPerPes": 4,
                                "PcrControl": "PCR_EVERY_PES_PACKET",
                                "PmtPid": 480,
                                "PrivateMetadataPid": 503,
                                "ProgramNumber": 1,
                                "PatInterval": 0,
                                "PmtInterval": 0,
                                "Scte35Source": "NONE",
                                "TimedMetadata": "NONE",
                                "TimedMetadataPid": 502,
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
                                    }
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

    try:
        response = client.create_job(**job_settings)
        job_id = response['Job']['Id']
        logger.info(f"Created MediaConvert job {job_id}")
        return job_id
    except Exception as e:
        logger.error(f"Error creating MediaConvert job: {str(e)}")
        raise

def check_job_status(job_id):
    """Check MediaConvert job status and output details"""
    client = get_mediaconvert_client()
    if not client:
        return
        
    try:
        response = client.get_job(Id=job_id)
        status = response['Job']['Status']
        logger.info(f"Job {job_id} status: {status}")
        
        if status == 'COMPLETE':
            # Check output details
            for output_group in response['Job']['Settings']['OutputGroups']:
                if output_group['OutputGroupSettings']['Type'] == 'HLS_GROUP_SETTINGS':
                    destination = output_group['OutputGroupSettings']['HlsGroupSettings']['Destination']
                    logger.info(f"HLS Output destination: {destination}")
                    
                    # Log each output (quality level)
                    for output in output_group['Outputs']:
                        if 'NameModifier' in output:
                            quality = output['NameModifier']
                            width = output['VideoDescription'].get('Width', 'N/A')
                            height = output['VideoDescription'].get('Height', 'N/A')
                            bitrate = output['VideoDescription']['CodecSettings']['H264Settings'].get('MaxBitrate', 'N/A')
                            logger.info(f"Quality level found: {quality} - Resolution: {width}x{height}, Bitrate: {bitrate}")
                            
        return status
    except Exception as e:
        logger.error(f"Error checking job status: {str(e)}")
        return None

def check_s3_output_files(bucket, prefix):
    """Check HLS files in S3 output location"""
    s3 = boto3.client('s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    
    try:
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        if 'Contents' in response:
            logger.info(f"\nFound {len(response['Contents'])} files in output location:")
            # Group files by quality level
            quality_files = {}
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.m3u8'):
                    if '_1080p' in key:
                        quality = '1080p'
                    elif '_720p' in key:
                        quality = '720p'
                    else:
                        quality = 'master'
                    
                    if quality not in quality_files:
                        quality_files[quality] = []
                    quality_files[quality].append(key)
            
            # Log files by quality
            for quality, files in quality_files.items():
                logger.info(f"\n{quality} playlist files:")
                for file in files:
                    logger.info(f"- {file}")
            
            return True
        else:
            logger.info("No files found in output location")
            return False
    except Exception as e:
        logger.error(f"Error checking S3 files: {str(e)}")
        return False

if __name__ == "__main__":
    load_dotenv()
    
    # Check recent jobs
    logger.info("Checking recent MediaConvert jobs...")
    list_recent_jobs()
    
    # Get the most recent job ID
    client = get_mediaconvert_client()
    if client:
        try:
            jobs = client.list_jobs(
                MaxResults=1,
                Order='DESCENDING',
                Status='ALL'
            )
            
            if 'Jobs' in jobs and jobs['Jobs']:
                job_id = jobs['Jobs'][0]['Id']
                logger.info(f"\nChecking most recent job: {job_id}")
                
                # Check job status
                status = check_job_status(job_id)
                
                if status == 'COMPLETE':
                    # Check output files
                    output_bucket = os.getenv('AWS_STREAMING_BUCKET')
                    output_prefix = f"recordings/"  # Adjust this based on your output path
                    logger.info(f"\nChecking output files in s3://{output_bucket}/{output_prefix}")
                    check_s3_output_files(output_bucket, output_prefix)
                else:
                    logger.info(f"Job is not complete yet. Current status: {status}")
            else:
                logger.info("No recent jobs found")
                
        except Exception as e:
            logger.error(f"Error: {str(e)}")
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    