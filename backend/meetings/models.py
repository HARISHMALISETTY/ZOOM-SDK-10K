from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Mentor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    zoom_account_id = models.CharField(max_length=255, unique=True)
    zoom_client_id = models.CharField(max_length=255)
    zoom_client_secret = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Mentor"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='students')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Student"

class Meeting(models.Model):
    MEETING_TYPES = (
        ('instant', 'Instant Meeting'),
        ('scheduled', 'Scheduled Meeting'),
    )
    
    RECORDING_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='meetings', null=True, blank=True)
    students = models.ManyToManyField(Student, related_name='meetings', blank=True)
    topic = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    duration = models.IntegerField()  # Duration in minutes
    meeting_id = models.CharField(max_length=255, unique=True)
    join_url = models.URLField()
    password = models.CharField(max_length=255, blank=True)
    host_email = models.EmailField()
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPES, default='instant')
    timezone = models.CharField(max_length=100, default='UTC')
    agenda = models.TextField(blank=True)
    settings = models.JSONField(default=dict)
    recurrence = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Recording information
    recording_status = models.CharField(max_length=20, choices=RECORDING_STATUS, default='pending')
    recording_url = models.URLField(blank=True)  # Main recording URL from Zoom
    recording_start_time = models.DateTimeField(null=True, blank=True)
    recording_end_time = models.DateTimeField(null=True, blank=True)
    recording_file_size = models.BigIntegerField(null=True, blank=True)
    
    # Meeting status
    is_active = models.BooleanField(default=True)
    reminder_sent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.topic} - {self.start_time}"
    
    def is_upcoming(self):
        """Check if the meeting is upcoming"""
        now = timezone.now()
        return self.start_time > now
    
    def is_past(self):
        """Check if the meeting is in the past"""
        now = timezone.now()
        return self.start_time < now
    
    def is_recurring(self):
        """Check if the meeting is recurring"""
        return bool(self.recurrence)
    
    def is_ongoing(self):
        now = timezone.now()
        return self.start_time <= now <= (self.start_time + timezone.timedelta(minutes=self.duration))
    
    def is_completed(self):
        return timezone.now() > (self.start_time + timezone.timedelta(minutes=self.duration))
    
    def should_send_reminder(self):
        if self.reminder_sent:
            return False
        now = timezone.now()
        reminder_time = self.start_time - timezone.timedelta(minutes=5)
        return now >= reminder_time and now < self.start_time

class Recording(models.Model):
    RECORDING_TYPES = (
        ('audio', 'Audio Only'),
        ('video', 'Video'),
        ('shared_screen', 'Shared Screen'),
        ('chat', 'Chat'),
    )
    
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='recordings')
    recording_url = models.URLField()  # Zoom recording URL
    recording_type = models.CharField(max_length=20, choices=RECORDING_TYPES)
    file_size = models.BigIntegerField(null=True, blank=True)  # Size in bytes
    duration = models.IntegerField(null=True, blank=True)  # Duration in seconds
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.meeting.topic} - {self.recording_type} - {self.created_at}"

    class Meta:
        ordering = ['-created_at'] 