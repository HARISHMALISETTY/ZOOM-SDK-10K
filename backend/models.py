from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(String, unique=True, nullable=False)  # Zoom meeting ID
    topic = Column(String, nullable=False)
    host_id = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    uuid = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with recordings
    recordings = relationship("Recording", back_populates="meeting")

class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    recording_id = Column(String, unique=True)
    topic = Column(String)  # Store topic name
    host_name = Column(String)  # Store host name
    file_type = Column(String)  # Store file type (e.g., "MP4")
    file_extension = Column(String)  # Store file extension (e.g., ".mp4")
    file_size = Column(Integer)  # Store file size in bytes
    recording_start = Column(DateTime)  # Store recording start time
    recording_end = Column(DateTime)  # Store recording end time
    recording_type = Column(String)  # Store recording type
    file_path = Column(String)  # Store original S3 key as file path
    streaming_path = Column(String, nullable=True)  # Store HLS streaming path
    mediaconvert_job_id = Column(String, nullable=True)  # Store MediaConvert job ID
    status = Column(String, default='pending')  # pending, processing, completed, error
    error_message = Column(String, nullable=True)
    quality_variants = Column(String, nullable=True)  # Store available quality variants (e.g., "1080p,720p,480p")
    processing_start_time = Column(DateTime, nullable=True)  # When MediaConvert job started
    processing_end_time = Column(DateTime, nullable=True)  # When MediaConvert job completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with meeting
    meeting = relationship("Meeting", back_populates="recordings") 