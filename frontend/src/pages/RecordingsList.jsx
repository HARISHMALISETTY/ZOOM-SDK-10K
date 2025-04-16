import React, { useEffect, useState } from "react";
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  ButtonGroup,
} from "@mui/material";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import CloseIcon from "@mui/icons-material/Close";
import RefreshIcon from "@mui/icons-material/Refresh";
import VideoPlayer from '../components/VideoPlayer';

const RecordingsList = () => {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [openVideoDialog, setOpenVideoDialog] = useState(false);

  useEffect(() => {
    fetchRecordings();
  }, []);

  const fetchRecordings = async () => {
    try {
      // console.log("Fetching recordings from database...");
      const response = await fetch("http://localhost:8001/api/recordings");
      if (!response.ok) {
        throw new Error("Failed to fetch recordings");
      }
      const data = await response.json();
      // console.log("Raw data from database:", data);

      // Log each recording's details
      // data.forEach((recording, index) => {
        // console.log(`\nRecording ${index + 1} Details:`);
        // console.log(recording);
        // console.log('Topic:', recording.topic);
        // console.log('Host Name:', recording.host_name);
        // console.log('File Size:', recording.file_size);
        // console.log('Created At:', recording.created_at);
        // console.log('Status:', recording.status);
        // console.log('----------------------------------------');
      // });

      // Only show completed recordings
      const completedRecordings = data.filter(
        (rec) => rec.status === "completed"
      );
      // console.log(`\nTotal recordings: ${data.length}`);
      // console.log(`Completed recordings: ${completedRecordings.length}`);

      setRecordings(completedRecordings);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching recordings:", error);
      setError("Failed to fetch recordings");
      setLoading(false);
    }
  };

  const handleProcessRecordings = async () => {
    try {
      setError(null);
      const response = await fetch(
        "http://localhost:8001/api/recordings/process",
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to process recordings");
      }

      // Refresh the recordings list
      await fetchRecordings();
    } catch (error) {
      console.error("Error processing recordings:", error);
      setError("Failed to process recordings");
    }
  };

  const handlePlayVideo = async (recording) => {
    try {
      if (!recording.recording_id) {
        console.error("No recording_id available for this recording");
        setError("Cannot play video: Missing recording ID");
        return;
      }

      console.log("Fetching stream URL for recording:", recording.recording_id);
      const response = await fetch(
        `http://localhost:8001/api/recordings/get-stream-url/${recording.recording_id}`
      );

      if (!response.ok) {
        throw new Error("Failed to get video URL");
      }

      const data = await response.json();
      console.log("Received stream URL DATA:", data);
      console.log("Received stream URL:", data.url);
      console.log("Video type:", data.type);

      setSelectedRecording({
        ...recording,
        video_url: data.url,
        video_type: data.type,
        signed_urls: data.signed_urls
      });
      setOpenVideoDialog(true);
    } catch (error) {
      console.error("Error fetching video URL:", error);
      setError("Failed to load video");
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };


  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="200px"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Typography variant="h4">Recordings List</Typography>
        <ButtonGroup>
          <Button
            variant="contained"
            color="primary"
            onClick={handleProcessRecordings}
            startIcon={<RefreshIcon />}
          >
            Process Recordings
          </Button>
        </ButtonGroup>
      </Box>

      {error && (
        <Box mb={3}>
          <Alert severity="error">{error}</Alert>
        </Box>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Topic</TableCell>
              <TableCell>Host</TableCell>
              <TableCell>File Size</TableCell>
              <TableCell>Created At</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {recordings.map((recording) => (
              <TableRow key={recording.id}>
                <TableCell>{recording.topic}</TableCell>
                <TableCell>{recording.host_name || 'Unknown'}</TableCell>
                <TableCell>{(recording.file_size / (1024 * 1024)).toFixed(2)} MB</TableCell>
                <TableCell>{formatDate(recording.created_at)}</TableCell>
                <TableCell>{recording.status}</TableCell>
                <TableCell>
                  <Tooltip title="Play Recording">
                    <span>
                      <IconButton
                        onClick={() => handlePlayVideo(recording)}
                        disabled={recording.status !== "completed"}
                      >
                        <PlayCircleOutlineIcon />
                      </IconButton>
                    </span>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog
        open={openVideoDialog}
        onClose={() => setOpenVideoDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedRecording?.topic || "Video Recording"}
          <IconButton
            onClick={() => setOpenVideoDialog(false)}
            sx={{ position: "absolute", right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedRecording?.video_url && (
            <Box sx={{ width: "100%", mt: 2 }}>
              <VideoPlayer 
                videoUrl={selectedRecording.video_url} 
                signedUrls={selectedRecording.signed_urls}
              />
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Host: {selectedRecording.host_name || 'Unknown'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  File Size: {(selectedRecording.file_size / (1024 * 1024)).toFixed(2)} MB
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  File Type: {selectedRecording.video_type}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Recording Start: {formatDate(selectedRecording.recording_start)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Recording End: {formatDate(selectedRecording.recording_end)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  File Path: {selectedRecording.file_path}
                </Typography>
              </Box>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mt: 1, display: "block" }}
              >
                Note: Video URLs expire after 1 hour. Refresh the page to get a
                new URL if needed.
              </Typography>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default RecordingsList;
