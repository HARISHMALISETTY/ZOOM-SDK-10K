import React, { useEffect, useState } from 'react';
import { Box, CircularProgress, Alert } from '@mui/material';

const ZoomMeeting = ({ meeting }) => {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const startMeeting = async () => {
      try {
        if (!meeting) {
          throw new Error('Meeting data is missing');
        }

        // Check for required environment variables
        const zoomClientId = import.meta.env.VITE_ZOOM_CLIENT_ID;
        if (!zoomClientId) {
          throw new Error('Zoom Client ID is not configured. Please check your environment variables.');
        }

        console.log('Starting meeting with data:', meeting);
        console.log('Using Zoom Client ID:', zoomClientId);

        // Wait for ZoomMtg to be available
        const waitForZoomMtg = () => {
          return new Promise((resolve) => {
            const checkZoomMtg = () => {
              if (window.ZoomMtg) {
                resolve(window.ZoomMtg);
              } else {
                setTimeout(checkZoomMtg, 100);
              }
            };
            checkZoomMtg();
          });
        };

        const ZoomMtg = await waitForZoomMtg();
        console.log('ZoomMtg loaded');

        // Set up Zoom SDK
        ZoomMtg.setZoomJSLib('https://source.zoom.us/2.18.0/lib', '/av');
        await ZoomMtg.preLoadWasm();
        await ZoomMtg.prepareWebSDK();
        console.log('Zoom SDK prepared');

        // Get meeting token from backend
        const backendUrl = import.meta.env.VITE_BACKEND_URL;
        const response = await fetch(`${backendUrl}/api/meetings/${meeting.meeting_id}/start-token`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to get meeting token');
        }
        const data = await response.json();
        console.log('Received meeting token data:', data);

        // Initialize Zoom SDK
        ZoomMtg.init({
          leaveUrl: window.location.origin,
          success: () => {
            console.log('Zoom SDK initialized successfully');
            
            // Join meeting
            ZoomMtg.join({
              signature: data.signature,
              meetingNumber: data.meeting_number,
              userName: data.host_name || 'Host',
              apiKey: zoomClientId,
              passWord: data.password || '',
              success: () => {
                console.log('Meeting joined successfully');
                setLoading(false);
              },
              error: (error) => {
                console.error('Error joining meeting:', error);
                setError('Failed to join meeting: ' + (error.message || 'Unknown error'));
              }
            });
          },
          error: (error) => {
            console.error('Error initializing Zoom SDK:', error);
            setError('Failed to initialize Zoom SDK: ' + (error.message || 'Unknown error'));
          }
        });
      } catch (error) {
        console.error('Error in startMeeting:', error);
        setError(error.message);
      }
    };

    startMeeting();

    // Cleanup function
    return () => {
      if (window.ZoomMtg) {
        window.ZoomMtg.leaveMeeting();
      }
    };
  }, [meeting]);

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <div id="zmmtg-root"></div>
    </Box>
  );
};

export default ZoomMeeting; 