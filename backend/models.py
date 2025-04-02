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
    file_path = Column(String)  # Store S3 key as file path
    status = Column(String, default='pending')
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with meeting
    meeting = relationship("Meeting", back_populates="recordings") 