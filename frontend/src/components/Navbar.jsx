import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary';
import DashboardIcon from '@mui/icons-material/Dashboard';
import GroupsIcon from '@mui/icons-material/Groups';

function Navbar() {
  return (
    <AppBar position="static">
      <Toolbar>
        <VideoLibraryIcon sx={{ mr: 2 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Zoom Recordings
        </Typography>
        <Box>
          <Button
            color="inherit"
            component={RouterLink}
            to="/"
            startIcon={<DashboardIcon />}
          >
            Dashboard
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/recordings"
            startIcon={<VideoLibraryIcon />}
          >
            Recordings
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/schedule"
            startIcon={<GroupsIcon />}
          >
            Schedule Meeting
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Navbar; 