import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Container, Typography, Alert } from '@mui/material';
import axios from 'axios';

const Meeting = () => {
  const { meetingId } = useParams();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initializeMeeting = async () => {
      try {
        // Get meeting details and signature
        const response = await axios.get(`http://localhost:8000/api/meetings/${meetingId}/`);
        const { meeting_number, signature, user_name, user_email } = response.data;

        // Initialize Zoom Web SDK
        const { ZoomMtg } = window;
        ZoomMtg.setZoomJSLib('https://source.zoom.us/2.18.0/lib', '/av');
        ZoomMtg.preLoadWasm();
        ZoomMtg.prepareWebSDK();

        // Initialize Zoom meeting
        ZoomMtg.init({
          leaveUrl: window.location.origin,
          success: (success) => {
            console.log('Init success:', success);
            ZoomMtg.join({
              signature: signature,
              meetingNumber: meeting_number,
              userName: user_name,
              userEmail: user_email,
              apiKey: import.meta.env.VITE_ZOOM_SDK_KEY,
              success: (joinSuccess) => {
                console.log('Join success:', joinSuccess);
                setLoading(false);
              },
              error: (error) => {
                console.error('Join error:', error);
                setError('Failed to join meeting');
                setLoading(false);
              },
            });
          },
          error: (error) => {
            console.error('Init error:', error);
            setError('Failed to initialize meeting');
            setLoading(false);
          },
        });
      } catch (error) {
        console.error('Error fetching meeting details:', error);
        setError('Failed to load meeting');
        setLoading(false);
      }
    };

    // Load Zoom SDK script
    const script = document.createElement('script');
    script.src = 'https://source.zoom.us/2.18.0/zoom-meeting-2.18.0.min.js';
    script.async = true;
    script.onload = initializeMeeting;
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, [meetingId]);

  return (
    <Container maxWidth="xl">
      <Box sx={{ mt: 4 }}>
        {loading && (
          <Typography variant="h6" align="center">
            Loading meeting...
          </Typography>
        )}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Box>
    </Container>
  );
};

export default Meeting; 