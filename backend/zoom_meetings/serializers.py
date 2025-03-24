from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Meeting, Participant

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Participant
        fields = ['id', 'user', 'joined_at', 'left_at']

class MeetingSerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)
    participants = ParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Meeting
        fields = ['id', 'topic', 'start_time', 'duration', 'meeting_id',
                 'meeting_password', 'join_url', 'host', 'participants',
                 'created_at', 'updated_at']
        read_only_fields = ['meeting_id', 'meeting_password', 'join_url']

    def create(self, validated_data):
        validated_data['host'] = self.context['request'].user
        return super().create(validated_data) 