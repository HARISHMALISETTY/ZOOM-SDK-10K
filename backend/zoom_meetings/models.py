from django.db import models
from django.contrib.auth.models import User

class Meeting(models.Model):
    topic = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    duration = models.IntegerField(help_text='Duration in minutes')
    meeting_id = models.CharField(max_length=200, blank=True)
    meeting_password = models.CharField(max_length=20, blank=True)
    join_url = models.URLField(blank=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.topic} - {self.start_time}"

class Participant(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['meeting', 'user']

    def __str__(self):
        return f"{self.user.username} - {self.meeting.topic}"
