import React, { useEffect, useState } from "react";
import { Box, Button, Typography, Container, Alert } from "@mui/material";
import axios from "axios";
import './MeetingInterface.css';

const MeetingInterface = ({ meetingData }) => {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [zoomScript, setZoomScript] = useState(null);

  useEffect(() => {
    const loadZoomScript = () => {
      return new Promise((resolve, reject) => {
        // Check if script already exists
        const existingScript = document.querySelector('script[src*="zoom-meeting-2.18.0.min.js"]');
        if (existingScript) {
          resolve(existingScript);
          return;
        }

        const script = document.createElement('script');
        script.src = 'https://source.zoom.us/2.18.0/zoom-meeting-2.18.0.min.js';
        script.async = true;
        script.onload = () => {
          setZoomScript(script);
          resolve(script);
        };
        script.onerror = reject;
        document.body.appendChild(script);
      });
    };

    const startMeeting = async () => {
      try {
        if (!meetingData) {
          throw new Error("Meeting data is missing");
        }

        console.log("Meeting data received:", meetingData);
        const token = localStorage.getItem('access_token');
        
        if (!token) {
          throw new Error("Authentication token is missing");
        }

        console.log("Attempting to join meeting with ID:", meetingData.id);

        // Load Zoom SDK script first
        await loadZoomScript();

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

        // Set up Zoom SDK
        ZoomMtg.setZoomJSLib("https://source.zoom.us/2.18.0/lib", "/av");
        await ZoomMtg.preLoadWasm();
        await ZoomMtg.prepareWebSDK();

        // Get meeting join details
        const response = await axios.get(`http://localhost:8001/api/meetings/${meetingData.meeting_id}/start-token`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        console.log("Join response:", response.data);

        if (response.data) {
          const { signature, meeting_number } = response.data;
          
          // Initialize Zoom SDK
          ZoomMtg.init({
            leaveUrl: window.location.origin,
            success: () => {
              console.log('Zoom SDK initialized successfully');
              setLoading(false);
              
              // Create a container for the meeting
              const meetingContainer = document.getElementById('zmmtg-root');
              if (!meetingContainer) {
                const container = document.createElement('div');
                container.id = 'zmmtg-root';
                document.body.appendChild(container);
              }

              // Join meeting with embedded view
              ZoomMtg.join({
                signature: signature,
                meetingNumber: meeting_number,
                userName: 'Host',
                apiKey: import.meta.env.VITE_ZOOM_CLIENT_ID,
                passWord: meetingData.password || '',
                success: () => {
                  console.log('Meeting joined successfully');
                  // Set the meeting container to be visible
                  const container = document.getElementById('zmmtg-root');
                  if (container) {
                    container.style.display = 'block';
                    container.style.position = 'fixed';
                    container.style.top = '0';
                    container.style.left = '0';
                    container.style.width = '100%';
                    container.style.height = '100%';
                    container.style.zIndex = '9999';
                  }
                },
                error: (error) => {
                  console.error('Error joining meeting:', error);
                  setError('Failed to join meeting');
                }
              });
            },
            error: (error) => {
              console.error('Error initializing Zoom SDK:', error);
              setError('Failed to initialize Zoom SDK');
            }
          });
        } else {
          throw new Error('Failed to get meeting details');
        }
      } catch (error) {
        console.error("Error in startMeeting:", error);
        console.error("Error response:", error.response?.data);
        console.error("Error status:", error.response?.status);
        setError(error.response?.data?.error || error.message || "Failed to join meeting");
        setLoading(false);
      }
    };

    startMeeting();

    // Cleanup function
    return () => {
      if (zoomScript && zoomScript.parentNode) {
        zoomScript.parentNode.removeChild(zoomScript);
      }
      // Clean up the meeting container
      const container = document.getElementById('zmmtg-root');
      if (container) {
        container.remove();
      }
    };
  }, [meetingData]);

  if (loading) {
    return (
      <Container>
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="h6">Loading meeting interface...</Typography>
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Box sx={{ mt: 4 }}>
          <Alert severity="error">{error}</Alert>
        </Box>
      </Container>
    );
  }

  return (
    <Container>
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6">Meeting interface loaded</Typography>
      </Box>
    </Container>
  );
};

export default MeetingInterface; 