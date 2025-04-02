import { useEffect, useState } from 'react';
import { Grid, Paper, Typography, Box, CircularProgress, Button } from '@mui/material';
import axios from 'axios';
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import StorageIcon from '@mui/icons-material/Storage';
import PersonIcon from '@mui/icons-material/Person';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';

function Dashboard() {
  const [stats, setStats] = useState({
    totalRecordings: 0,
   
    totalStorage: 0,
    totalHosts: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  const fetchStats = async () => {
    try {
      const response = await axios.get('http://localhost:8001/api/recordings/stats');
      setStats(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch statistics');
      console.error('Error fetching stats:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleUploadToS3 = async () => {
    setIsUploading(true);
    try {
      // First, trigger the download and S3 upload process
      const response = await axios.post('http://localhost:8001/api/recordings/process');
      console.log('Processing response:', response.data);
      
      // Show success message with details
      const message = `${response.data.message}\nProcessed: ${response.data.processed_recordings.length}\nSkipped: ${response.data.skipped_recordings.length}`;
      setSnackbar({
        open: true,
        message: message,
        severity: 'success'
      });
      
      // Refresh stats after successful upload
      await fetchStats();
      
      // Log the results
      console.log('Processed recordings:', response.data.processed_recordings);
      console.log('Skipped recordings:', response.data.skipped_recordings);
      
    } catch (err) {
      console.error('Error processing recordings:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to process recordings',
        severity: 'error'
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  

  const formatFileSize = (bytes) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Byte';
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<CloudUploadIcon />}
          onClick={handleUploadToS3}
          disabled={isUploading}
        >
          {isUploading ? 'Processing...' : 'Process Recordings'}
        </Button>
      </Box>

      {error && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: '#ffebee' }}>
          <Typography color="error">{error}</Typography>
        </Paper>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
            <VideoLibraryIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
            <Box>
              <Typography variant="h6">Total Recordings</Typography>
              <Typography variant="h4">{stats.totalRecordings}</Typography>
            </Box>
          </Paper>
        </Grid>
       
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
            <StorageIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
            <Box>
              <Typography variant="h6">Total Storage</Typography>
              <Typography variant="h4">{formatFileSize(stats.totalStorage)}</Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
            <PersonIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
            <Box>
              <Typography variant="h6">Total Hosts</Typography>
              <Typography variant="h4">{stats.totalHosts}</Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbar.severity}
          sx={{ whiteSpace: 'pre-line' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default Dashboard; 