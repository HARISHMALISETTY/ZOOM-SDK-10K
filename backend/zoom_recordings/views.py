from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from datetime import datetime
from .recording_fetcher import ZoomRecordingFetcher
from .meeting_fetcher import ZoomMeetingFetcher

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def fetch_recordings(request):
    """
    API endpoint to fetch Zoom recordings
    Optional query parameters:
    - from_date: Start date (YYYY-MM-DD)
    - to_date: End date (YYYY-MM-DD)
    """
    try:
        # Get date range from query parameters if provided
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        
        # Convert string dates to datetime objects if provided
        if from_date:
            from_date = datetime.strptime(from_date, '%Y-%m-%d')
        if to_date:
            to_date = datetime.strptime(to_date, '%Y-%m-%d')
        
        # Initialize fetcher and get recordings
        fetcher = ZoomRecordingFetcher()
        recordings = fetcher.fetch_recordings(from_date, to_date)
        
        return Response({
            'success': True,
            'recordings': recordings
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def fetch_meetings(request):
    """
    API endpoint to fetch all scheduled Zoom meetings organized by date
    """
    try:
        # Initialize fetcher and get meetings
        fetcher = ZoomMeetingFetcher()
        meetings_by_date = fetcher.fetch_meetings()
        
        return Response({
            'success': True,
            'meetings': meetings_by_date
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500) 