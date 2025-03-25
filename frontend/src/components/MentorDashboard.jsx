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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormControlLabel,
  Switch,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import MeetingInterface from './MeetingInterface';
import { Add as AddIcon, VideoCall as VideoCallIcon } from '@mui/icons-material';

const MentorDashboard = () => {
  const location = useLocation();
  const [meetings, setMeetings] = useState([]);
  const [recordings, setRecordings] = useState([]);
  const [batches, setBatches] = useState([]);
  const [openModal, setOpenModal] = useState(false);
  const [activeMeeting, setActiveMeeting] = useState(null);
  const [meetingData, setMeetingData] = useState({
    topic: '',
    start_time: null,
    duration: 60,
    type: 2,
    batch_id: '',
    description: '',
    enable_recording: true,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [instantClassData, setInstantClassData] = useState({
    topic: '',
    duration: 60,
    description: '',
    enable_recording: true,
    batch_id: '',
  });

  useEffect(() => {
    fetchMeetings();
    fetchRecordings();
    fetchBatches();
    
    // Check if we should open the create meeting dialog
    if (location.state?.openCreateMeeting) {
      setMeetingData(prev => ({ ...prev, type: 2 })); // Default to scheduled meeting
    }
  }, [location]);

  const fetchMeetings = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('http://localhost:8000/api/meetings/list/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Filter out past meetings
      const currentTime = new Date();
      const upcomingMeetings = response.data.filter(meeting => 
        new Date(meeting.start_time) > currentTime
      );
      
      // Sort meetings by start time (earliest first)
      upcomingMeetings.sort((a, b) => 
        new Date(a.start_time) - new Date(b.start_time)
      );
      
      setMeetings(upcomingMeetings);
    } catch (error) {
      console.error('Error fetching meetings:', error);
      setError('Failed to fetch meetings');
    }
  };

  const fetchRecordings = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('http://localhost:8000/api/meetings/recordings/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setRecordings(response.data.recordings || []);
    } catch (error) {
      console.error('Error fetching recordings:', error);
      setError('Failed to fetch recordings');
    }
  };

  const fetchBatches = async () => {
    // Static batches for testing
    const staticBatches = [
      { id: 1, name: "Batch 2024 - Web Development" },
      { id: 2, name: "Batch 2024 - Data Science" },
      { id: 3, name: "Batch 2024 - Mobile Development" },
      { id: 4, name: "Batch 2024 - UI/UX Design" },
      { id: 5, name: "Batch 2024 - Cloud Computing" }
    ];
    setBatches(staticBatches);
  };

  const handleCreateMeeting = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.post('http://localhost:8000/api/meetings/create/', meetingData, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setMeetings([...meetings, response.data]);
      setSuccess('Meeting created successfully!');
      setMeetingData({
        topic: '',
        start_time: null,
        duration: 60,
        type: 2,
        batch_id: '',
        description: '',
        enable_recording: true,
      });
    } catch (error) {
      console.error('Error creating meeting:', error);
      setError('Failed to create meeting');
    }
  };

  const handleStartInstantMeeting = async () => {
    try {
      // Get user's email from localStorage
      const userEmail = localStorage.getItem('user_email');
      const token = localStorage.getItem('access_token');
      console.log('User email:', userEmail);

      // Create meeting with selected batch ID or default to 1
      const response = await axios.post("http://localhost:8000/api/meetings/create/", {
        topic: instantClassData.topic || "Instant Class",
        type: 2, // Instant meeting
        start_time: new Date().toISOString(),
        duration: instantClassData.duration || 60,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        host_email: userEmail,
        batch_id: instantClassData.batch_id || 1, // Use selected batch ID or default to 1
        description: instantClassData.description || "",
        enable_recording: instantClassData.enable_recording
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.data) {
        setMeetingData(response.data);
        setActiveMeeting(response.data);
        setOpenModal(false);
      }
    } catch (error) {
      console.error("Error starting instant meeting:", error);
      setError("Failed to start instant meeting");
    }
  };

  const handleCloseModal = () => {
    setOpenModal(false);
    setInstantClassData({
      topic: '',
      duration: 60,
      description: '',
      enable_recording: true,
      batch_id: '',
    });
  };

  const handleInputChange = (e) => {
    const { name, value, checked } = e.target;
    setInstantClassData(prev => ({
      ...prev,
      [name]: name === 'enable_recording' ? checked : value
    }));
  };

  const handleJoinMeeting = (meeting) => {
    setActiveMeeting(meeting);
  };

  if (activeMeeting) {
    return <MeetingInterface meetingData={activeMeeting} />;
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="h4">Mentor Dashboard</Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setOpenModal(true)}
          >
            Start Instant Class
          </Button>
        </Box>

        <Grid container spacing={3}>
          {/* Upcoming Classes Section */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3, mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                <Typography variant="h5">Upcoming Classes</Typography>
              </Box>

              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Topic</TableCell>
                      <TableCell>Batch</TableCell>
                      <TableCell>Start Time</TableCell>
                      <TableCell>Duration</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {meetings.length > 0 ? (
                      meetings.map((meeting) => (
                        <TableRow key={meeting.id}>
                          <TableCell>{meeting.topic}</TableCell>
                          <TableCell>{meeting.batch_name}</TableCell>
                          <TableCell>
                            {meeting.start_time
                              ? new Date(meeting.start_time).toLocaleString()
                              : 'N/A'}
                          </TableCell>
                          <TableCell>{meeting.duration} minutes</TableCell>
                          <TableCell>
                            <Button
                              variant="outlined"
                              color="primary"
                              onClick={() => handleJoinMeeting(meeting)}
                            >
                              Join Class
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          No upcoming classes scheduled
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>

          {/* Recorded Classes Section */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" sx={{ mb: 3 }}>
                Recorded Classes
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Topic</TableCell>
                      <TableCell>Batch</TableCell>
                      <TableCell>Date</TableCell>
                      <TableCell>Duration</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {recordings.map((recording) => (
                      <TableRow key={recording.id}>
                        <TableCell>{recording.topic}</TableCell>
                        <TableCell>{recording.batch_name}</TableCell>
                        <TableCell>
                          {new Date(recording.start_time).toLocaleString()}
                        </TableCell>
                        <TableCell>{recording.duration} minutes</TableCell>
                        <TableCell>
                          <Button
                            variant="outlined"
                            color="primary"
                            onClick={() => window.open(recording.play_url, '_blank')}
                          >
                            Watch Recording
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      </Box>

      <Dialog open={openModal} onClose={handleCloseModal} maxWidth="sm" fullWidth>
        <DialogTitle>Start Instant Class</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Class Topic"
              name="topic"
              value={instantClassData.topic}
              onChange={handleInputChange}
              fullWidth
              required
            />
            <TextField
              label="Duration (minutes)"
              name="duration"
              type="number"
              value={instantClassData.duration}
              onChange={handleInputChange}
              fullWidth
              required
            />
            <TextField
              label="Description"
              name="description"
              value={instantClassData.description}
              onChange={handleInputChange}
              multiline
              rows={3}
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel>Batch</InputLabel>
              <Select
                name="batch_id"
                value={instantClassData.batch_id}
                onChange={handleInputChange}
                label="Batch"
                required
              >
                {batches.map((batch) => (
                  <MenuItem key={batch.id} value={batch.id}>
                    {batch.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControlLabel
              control={
                <Switch
                  name="enable_recording"
                  checked={instantClassData.enable_recording}
                  onChange={handleInputChange}
                />
              }
              label="Enable Recording"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal}>Cancel</Button>
          <Button 
            onClick={handleStartInstantMeeting} 
            variant="contained" 
            color="primary"
            disabled={!instantClassData.batch_id}
          >
            Start Class
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default MentorDashboard; 