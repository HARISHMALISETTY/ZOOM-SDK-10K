import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Container,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import axios from 'axios';

const MeetingManager = () => {
  const [meetings, setMeetings] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [meetingType, setMeetingType] = useState(''); // 'instant' or 'scheduled'
  const [meetingData, setMeetingData] = useState({
    topic: '',
    start_time: null,
    duration: 60,
    type: 2, // 2 for scheduled meeting
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchMeetings();
  }, []);

  const fetchMeetings = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/meetings/');
      setMeetings(response.data);
    } catch (error) {
      console.error('Error fetching meetings:', error);
      setError('Failed to fetch meetings');
    }
  };

  const handleCreateMeeting = async () => {
    try {
      const response = await axios.post('http://localhost:8000/api/meetings/', meetingData);
      setMeetings([...meetings, response.data]);
      setSuccess('Meeting created successfully!');
      setOpenDialog(false);
      setMeetingData({
        topic: '',
        start_time: null,
        duration: 60,
        type: 2,
      });
    } catch (error) {
      console.error('Error creating meeting:', error);
      setError('Failed to create meeting');
    }
  };

  const handleStartInstantMeeting = async () => {
    try {
      const response = await axios.post('http://localhost:8000/api/meetings/', {
        topic: 'Instant Meeting',
        type: 1, // 1 for instant meeting
        duration: 60,
      });
      setMeetings([...meetings, response.data]);
      setSuccess('Instant meeting started!');
    } catch (error) {
      console.error('Error starting instant meeting:', error);
      setError('Failed to start instant meeting');
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
              <Typography variant="h4">Meeting Manager</Typography>
              <Box>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={() => {
                    setMeetingType('instant');
                    handleStartInstantMeeting();
                  }}
                  sx={{ mr: 2 }}
                >
                  Start Instant Meeting
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  onClick={() => {
                    setMeetingType('scheduled');
                    setOpenDialog(true);
                  }}
                >
                  Schedule Meeting
                </Button>
              </Box>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" sx={{ mb: 2 }}>
                {success}
              </Alert>
            )}

            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Topic</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Start Time</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Meeting ID</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {meetings.map((meeting) => (
                    <TableRow key={meeting.id}>
                      <TableCell>{meeting.topic}</TableCell>
                      <TableCell>{meeting.type === 1 ? 'Instant' : 'Scheduled'}</TableCell>
                      <TableCell>
                        {meeting.start_time
                          ? new Date(meeting.start_time).toLocaleString()
                          : 'N/A'}
                      </TableCell>
                      <TableCell>{meeting.duration} minutes</TableCell>
                      <TableCell>{meeting.meeting_id}</TableCell>
                      <TableCell>
                        <Button
                          variant="outlined"
                          color="primary"
                          onClick={() => window.open(meeting.join_url, '_blank')}
                        >
                          Join
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Grid>
        </Grid>
      </Box>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>Schedule New Meeting</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Meeting Topic"
              value={meetingData.topic}
              onChange={(e) =>
                setMeetingData({ ...meetingData, topic: e.target.value })
              }
              fullWidth
              required
            />
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DateTimePicker
                label="Start Time"
                value={meetingData.start_time}
                onChange={(newValue) =>
                  setMeetingData({ ...meetingData, start_time: newValue })
                }
                renderInput={(params) => <TextField {...params} fullWidth />}
              />
            </LocalizationProvider>
            <TextField
              label="Duration (minutes)"
              type="number"
              value={meetingData.duration}
              onChange={(e) =>
                setMeetingData({ ...meetingData, duration: parseInt(e.target.value) })
              }
              fullWidth
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateMeeting} variant="contained" color="primary">
            Create Meeting
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default MeetingManager; 