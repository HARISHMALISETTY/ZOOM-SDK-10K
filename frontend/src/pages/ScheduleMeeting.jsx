import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Container,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
} from "@mui/material";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import VideocamIcon from "@mui/icons-material/Videocam";
import EditIcon from "@mui/icons-material/Edit";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { format, isBefore, differenceInMinutes } from "date-fns";

const ScheduleMeeting = () => {
  const [DIALOG_OPEN, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [formData, setFormData] = useState({
    topic: "",
    start_time: new Date(),
    duration: 60,
    timezone: "UTC",
    settings: {
      host_video: true,
      participant_video: true,
      join_before_host: false,
      mute_upon_entry: true,
      waiting_room: true,
      meeting_authentication: true,
    },
  });
  const [scheduledMeetings, setScheduledMeetings] = useState([]);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [meetingStatuses, setMeetingStatuses] = useState({});

  // Function to sync meetings from Zoom
  const syncMeetingsFromZoom = async () => {
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      const response = await fetch(`${backendUrl}/api/meetings/sync`);
      if (!response.ok) {
        throw new Error("Failed to sync meetings from Zoom");
      }
      const data = await response.json();
      console.log("Meetings synced from Zoom successfully", data);
    } catch (err) {
      console.error("Error syncing meetings from Zoom:", err);
      setError("Failed to sync meetings from Zoom: " + err.message);
    }
  };

  // Function to fetch meetings from database
  const fetchMeetingsFromDB = async () => {
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      const response = await fetch(`${backendUrl}/api/meetings`);
      if (!response.ok) {
        throw new Error("Failed to fetch meetings from database");
      }
      const data = await response.json();
      console.log("Fetched meetings from database:", data);
      setScheduledMeetings(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Error fetching meetings from database:", err);
      setError("Failed to fetch meetings: " + err.message);
      setScheduledMeetings([]);
    }
  };

  // Fetch meetings when component mounts
  useEffect(() => {
    const initializeMeetings = async () => {
      try {
        // First sync meetings from Zoom
        await syncMeetingsFromZoom();
        // Then fetch meetings from database
        await fetchMeetingsFromDB();
      } catch (error) {
        console.error("Error initializing meetings:", error);
        setError("Failed to initialize meetings: " + error.message);
      }
    };

    initializeMeetings();
  }, []); // Empty dependency array means this runs once when component mounts

  // Separate effect for reminders and status updates
  useEffect(() => {
    const interval = setInterval(() => {
      checkReminders();
      updateMeetingStatuses();
    }, 60000); // Check every minute
    return () => clearInterval(interval);
  }, [scheduledMeetings]); // This effect depends on scheduledMeetings

  const handleStartMeeting = async (meeting) => {
    try {
      // Get the join URL from the backend
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      const response = await fetch(
        `${backendUrl}/api/meetings/${meeting.meeting_id}/join-url`
      );
      if (!response.ok) {
        throw new Error("Failed to get meeting URL");
      }
      const data = await response.json();

      // Create the zoommtg:// URL
      const zoomUrl = `zoommtg://zoom.us/start?confno=${meeting.meeting_id}&pwd=${data.password}`;

      // Try to open in Zoom app
      window.location.href = zoomUrl;

      // Fallback to web client if app doesn't open after a short delay
      setTimeout(() => {
        window.open(data.join_url, "_blank");
      }, 1000);
    } catch (error) {
      console.error("Error starting meeting:", error);
      setError("Failed to start meeting: " + error.message);
    }
  };

  const updateMeetingStatuses = async () => {
    const statuses = {};
    for (const meeting of scheduledMeetings) {
      try {
        const response = await fetch(
          `http://localhost:8001/api/meetings/${meeting.meeting_id}/status`
        );
        if (response.ok) {
          const data = await response.json();
          statuses[meeting.meeting_id] = data;
        }
      } catch (err) {
        console.error(
          `Error fetching status for meeting ${meeting.meeting_id}:`,
          err
        );
      }
    }
    setMeetingStatuses(statuses);
  };

  const checkReminders = () => {
    const now = new Date();
    const newReminders = scheduledMeetings
      .filter((meeting) => {
        const meetingTime = new Date(meeting.start_time);
        const minutesUntilMeeting = differenceInMinutes(meetingTime, now);
        return minutesUntilMeeting > 0 && minutesUntilMeeting <= 5;
      })
      .map((meeting) => ({
        ...meeting,
        minutesUntil: differenceInMinutes(new Date(meeting.start_time), now),
      }));
    setReminders(newReminders);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      const response = await fetch(`${backendUrl}/api/meetings/schedule`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to schedule meeting");
      }

      await response.json();
      setSuccess("Meeting scheduled successfully!");
      setOpen(false);
      setFormData({
        topic: "",
        start_time: new Date(),
        duration: 60,
        timezone: "UTC",
        settings: {
          host_video: true,
          participant_video: true,
          join_before_host: false,
          mute_upon_entry: true,
          waiting_room: true,
          meeting_authentication: true,
        },
      });
    } catch (error) {
      console.error("Error scheduling meeting:", error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditMeeting = (meeting) => {
    setSelectedMeeting(meeting);
    setFormData({
      topic: meeting.topic,
      start_time: new Date(meeting.start_time),
      timezone: meeting.timezone || "Asia/Kolkata",
    });
    setEditDialogOpen(true);
  };

  const handleUpdateMeeting = async () => {
    try {
      const response = await fetch(
        `http://localhost:8001/api/meetings/${selectedMeeting.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...formData,
            start_time: formData.start_time.toISOString(),
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to update meeting");
      }

      setEditDialogOpen(false);
      setSuccess("Meeting updated successfully!");
      fetchMeetingsFromDB();
    } catch (err) {
      setError(err.message);
    }
  };

  const isMeetingStarted = (startTime) => {
    return isBefore(new Date(startTime), new Date());
  };

  const getMeetingStatus = (meeting) => {
    const status = meetingStatuses[meeting.meeting_id];
    if (!status) {
      return { label: "Loading...", color: "default" };
    }

    if (status.is_active) {
      return {
        label: `In Progress (${status.participant_count} participants)`,
        color: "success",
      };
    }

    const now = new Date();
    const meetingTime = new Date(meeting.start_time);
    const minutesUntilMeeting = differenceInMinutes(meetingTime, now);

    if (isMeetingStarted(meeting.start_time)) {
      return { label: "Waiting for Host", color: "warning" };
    } else if (minutesUntilMeeting <= 5) {
      return {
        label: `Starting in ${minutesUntilMeeting} min`,
        color: "warning",
      };
    } else {
      return { label: "Upcoming", color: "primary" };
    }
  };

  return (
    <Container maxWidth="lg">
      {/* Reminders */}
      {reminders.length > 0 && (
        <Paper elevation={3} sx={{ p: 2, mt: 4, bgcolor: "#fff3e0" }}>
          <Typography variant="h6" gutterBottom>
            Meeting Reminders
          </Typography>
          {reminders.map((meeting) => (
            <Typography key={meeting.id}>
              {meeting.topic} starts in {meeting.minutesUntil} minutes
            </Typography>
          ))}
        </Paper>
      )}

      <Paper elevation={3} sx={{ p: 4, mt: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Schedule Zoom Meeting
        </Typography>

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

        <Box component="form" onSubmit={handleSubmit}>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Meeting Topic"
                value={formData.topic}
                onChange={(e) =>
                  setFormData({ ...formData, topic: e.target.value })
                }
                required
              />
            </Grid>
            <Grid item xs={12}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DateTimePicker
                  label="Start Time"
                  value={formData.start_time}
                  onChange={(newValue) =>
                    setFormData({ ...formData, start_time: newValue })
                  }
                  renderInput={(params) => (
                    <TextField {...params} fullWidth required />
                  )}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                type="number"
                label="Duration (minutes)"
                value={formData.duration}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    duration: parseInt(e.target.value),
                  })
                }
                required
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Timezone</InputLabel>
                <Select
                  value={formData.timezone}
                  onChange={(e) =>
                    setFormData({ ...formData, timezone: e.target.value })
                  }
                  label="Timezone"
                >
                  <MenuItem value="UTC">UTC</MenuItem>
                  <MenuItem value="America/New_York">Eastern Time</MenuItem>
                  <MenuItem value="America/Chicago">Central Time</MenuItem>
                  <MenuItem value="America/Denver">Mountain Time</MenuItem>
                  <MenuItem value="America/Los_Angeles">Pacific Time</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                fullWidth
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : "Schedule Meeting"}
              </Button>
            </Grid>
          </Grid>
        </Box>
      </Paper>

      {/* Scheduled Meetings Table */}
      <Paper elevation={3} sx={{ p: 4, mt: 4 }}>
        <Typography variant="h5" component="h2" gutterBottom>
          Scheduled Meetings
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Topic</TableCell>
                <TableCell>Start Time</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Array.isArray(scheduledMeetings) &&
                scheduledMeetings.map((meeting) => {
                  const status = getMeetingStatus(meeting);
                  return (
                    <TableRow key={meeting.id}>
                      <TableCell>{meeting.topic}</TableCell>
                      <TableCell>
                        {format(new Date(meeting.start_time), "PPpp")}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={status.label}
                          color={status.color}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", gap: 1 }}>
                          {!isMeetingStarted(meeting.start_time) ? (
                            <Tooltip title="Start Meeting">
                              <IconButton
                                color="primary"
                                onClick={() => handleStartMeeting(meeting)}
                              >
                                <VideocamIcon />
                              </IconButton>
                            </Tooltip>
                          ) : (
                            <Tooltip title="Join Meeting">
                              <IconButton
                                color="primary"
                                onClick={() => handleStartMeeting(meeting)}
                              >
                                <PlayArrowIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                          <Tooltip title="Edit Meeting">
                            <IconButton
                              color="primary"
                              onClick={() => handleEditMeeting(meeting)}
                            >
                              <EditIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  );
                })}
              {(!Array.isArray(scheduledMeetings) ||
                scheduledMeetings.length === 0) && (
                <TableRow>
                  <TableCell colSpan={4} align="center">
                    No scheduled meetings found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Edit Meeting Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}>
        <DialogTitle>Edit Meeting</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <TextField
              fullWidth
              label="Meeting Topic"
              name="topic"
              value={formData.topic}
              onChange={(e) =>
                setFormData({ ...formData, topic: e.target.value })
              }
              margin="normal"
              required
            />

            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DateTimePicker
                label="Start Time"
                value={formData.start_time}
                onChange={(newValue) =>
                  setFormData({ ...formData, start_time: newValue })
                }
                renderInput={(params) => (
                  <TextField {...params} fullWidth margin="normal" required />
                )}
              />
            </LocalizationProvider>

            <FormControl fullWidth margin="normal">
              <InputLabel>Timezone</InputLabel>
              <Select
                name="timezone"
                value={formData.timezone}
                onChange={(e) =>
                  setFormData({ ...formData, timezone: e.target.value })
                }
                label="Timezone"
              >
                <MenuItem value="UTC">UTC</MenuItem>
                <MenuItem value="America/New_York">Eastern Time</MenuItem>
                <MenuItem value="America/Chicago">Central Time</MenuItem>
                <MenuItem value="America/Denver">Mountain Time</MenuItem>
                <MenuItem value="America/Los_Angeles">Pacific Time</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpdateMeeting}
            variant="contained"
            color="primary"
          >
            Update Meeting
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ScheduleMeeting;
