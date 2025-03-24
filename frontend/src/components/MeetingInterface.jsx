import React, { useEffect } from "react";
import { Box } from "@mui/material";
import axios from "axios";
import ZoomMtg from "@zoomus/websdk";

const MeetingInterface = ({ meetingData }) => {
  useEffect(() => {
    const startMeeting = async () => {
      try {
        if (!meetingData) {
          console.error("Meeting data is missing");
          return;
        }
    
        const { meeting_id, host_email, password } = meetingData;
    
        // Get signature from backend
        const signatureResponse = await axios.post(
          "http://localhost:8000/api/meetings/signature/",
          {
            meetingNumber: meeting_id,
            role: 1, // Host role
          }
        );
    
        const { signature, sdkKey } = signatureResponse.data;
    
        // Initialize Zoom SDK
        ZoomMtg.setZoomJSLib("https://source.zoom.us/2.18.0/lib", "/av");
        ZoomMtg.preLoadWasm();
        ZoomMtg.prepareJssdk();
    
        ZoomMtg.init({
          leaveUrl: window.location.origin + "/mentor",
          success: () => {
            console.log("Zoom initialized successfully");
            ZoomMtg.join({
              meetingNumber: meeting_id,
              userName: "Host",
              userEmail: host_email,
              password: password,
              signature: signature,
              apiKey: sdkKey,
              success: (response) => {
                console.log("Meeting joined successfully", response);
              },
              error: (err) => {
                console.error("Failed to join meeting:", err);
              },
            });
          },
          error: (err) => {
            console.error("Failed to initialize Zoom:", err);
          },
        });
      } catch (error) {
        console.error("Error in startMeeting:", error);
      }
    };

    startMeeting();

    // Cleanup
    return () => {
      try {
        if (window.ZoomMtg) {
          window.ZoomMtg.leaveMeeting({});
        }
        // Remove Zoom scripts
        const scripts = document.querySelectorAll('script[src*="zoom"]');
        scripts.forEach(script => script.remove());
      } catch (error) {
        console.error("Error during cleanup:", error);
      }
    };
  }, [meetingData]);

  return (
    <Box sx={{ 
      width: '100%', 
      height: 'calc(100vh - 64px)', // Subtract the height of the AppBar
      position: 'relative',
      overflow: 'hidden',
      backgroundColor: '#fff'
    }}>
      <Box id="zmmtg-root" sx={{ 
        width: '100%', 
        height: '100%',
        position: 'absolute',
        top: 0,
        left: 0,
        zIndex: 1000
      }} />
    </Box>
  );
};

export default MeetingInterface;