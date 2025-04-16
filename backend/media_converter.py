import os
import boto3
import logging
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MediaConvertProcessor:
    def __init__(self):
        self.endpoint = None
        self.client = None
        self.role_arn = os.getenv('AWS_MEDIACONVERT_ROLE')
        self.queue_arn = os.getenv('AWS_MEDIACONVERT_QUEUE', 'DEFAULT')
        self.setup_client()

    def setup_client(self):
        try:
            # Use hardcoded endpoint for ap-south-1
            self.endpoint = "https://xgitl3mi.mediaconvert.ap-south-1.amazonaws.com"
            logger.info(f"Using MediaConvert endpoint: {self.endpoint}")
            
            # Create a client using the endpoint
            self.client = boto3.client('mediaconvert',
                endpoint_url=self.endpoint,
                region_name=os.getenv('AWS_REGION'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
                aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
            )
            logger.info("MediaConvert client initialized successfully")
        except Exception as e:
            logger.error(f"Error setting up MediaConvert client: {str(e)}")
            raise

    def create_job(self, input_key):
        try:
            input_bucket = os.getenv('AWS_BUCKET_NAME')
            output_bucket = os.getenv('AWS_STREAMING_BUCKET')
            
            # Extract meeting_id and recording_id from the input path
            # Format: recordings/{meeting_id}/{recording_id}.mp4
            parts = input_key.split('/')
            if len(parts) >= 3:
                meeting_id = parts[1]
                recording_id = parts[2].split('.')[0]
                output_path = f"recordings/{meeting_id}/{recording_id}"
            else:
                raise ValueError("Invalid input key format")

            job_settings = {
                "TimecodeConfig": {"Source": "ZEROBASED"},
                "Inputs": [{
                    "TimecodeSource": "ZEROBASED",
                    "VideoSelector": {},
                    "AudioSelectors": {
                        "Audio Selector 1": {
                            "DefaultSelection": "DEFAULT"
                        }
                    },
                    "FileInput": f"s3://{input_bucket}/{input_key}"
                }],
                "OutputGroups": [{
                    "Name": "HLS Output",
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
                            "Destination": f"s3://{output_bucket}/{output_path}/",
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

            # Create the job
            try:
                response = self.client.create_job(
                    Role=self.role_arn,
                    Settings=job_settings,
                    Queue=self.queue_arn
                )
                job_id = response['Job']['Id']
                logger.info(f"Created MediaConvert job: {job_id}")
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
            response = self.client.get_job(Id=job_id)
            return response['Job']['Status']
        except ClientError as e:
            logger.error(f"Error getting job status: {str(e)}")
            raise 