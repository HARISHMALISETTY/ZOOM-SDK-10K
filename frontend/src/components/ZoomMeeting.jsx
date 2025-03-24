import React, { useEffect, useState } from 'react';
import { Box, Button, TextField, Typography, Container } from '@mui/material';
import { zoomConfig, generateSignature } from '../config/zoomConfig';

const ZoomMeeting = () => {
  const [meetingNumber, setMeetingNumber] = useState('');
  const [userName, setUserName] = useState('');
  const [isJoined, setIsJoined] = useState(false);

  useEffect(() => {
    // Initialize Zoom Web SDK
    const script = document.createElement('script');
    script.src = 'https://source.zoom.us/2.18.0/zoom-meeting-2.18.0.min.js';
    script.async = true;
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const joinMeeting = async () => {
    try {
      const signature = await generateSignature(meetingNumber, 0); // 0 for attendee
      zoomConfig.meetingNumber = meetingNumber;
      zoomConfig.userName = userName;
      zoomConfig.signature = signature;

      const { ZoomMtg } = window;
      ZoomMtg.setZoomJSLib('https://source.zoom.us/2.18.0/lib', '/av');
      ZoomMtg.preLoadWasm();
      ZoomMtg.prepareWebSDK();

      ZoomMtg.init({
        leaveUrl: window.location.origin,
        success: (success) => {
          console.log('Init success:', success);
          ZoomMtg.join({
            signature: zoomConfig.signature,
            meetingNumber: zoomConfig.meetingNumber,
            userName: zoomConfig.userName,
            apiKey: zoomConfig.apiKey,
            passWord: zoomConfig.passWord,
            success: (joinSuccess) => {
              console.log('Join success:', joinSuccess);
              setIsJoined(true);
            },
            error: (error) => {
              console.error('Join error:', error);
            },
          });
        },
        error: (error) => {
          console.error('Init error:', error);
        },
      });
    } catch (error) {
      console.error('Error joining meeting:', error);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Join Zoom Meeting
        </Typography>
        
        {!isJoined ? (
          <>
            <TextField
              label="Meeting Number"
              value={meetingNumber}
              onChange={(e) => setMeetingNumber(e.target.value)}
              fullWidth
              required
            />
            <TextField
              label="Your Name"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              fullWidth
              required
            />
            <Button
              variant="contained"
              color="primary"
              onClick={joinMeeting}
              disabled={!meetingNumber || !userName}
            >
              Join Meeting
            </Button>
          </>
        ) : (
          <Typography variant="h6" color="success.main">
            You are now in the meeting!
          </Typography>
        )}
      </Box>
    </Container>
  );
};

export default ZoomMeeting; 