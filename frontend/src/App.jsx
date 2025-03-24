import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom'
import { ThemeProvider, createTheme, AppBar, Toolbar, Typography, Button, Container } from '@mui/material'
import CssBaseline from '@mui/material/CssBaseline'
import Login from './components/Login'
import MentorDashboard from './components/MentorDashboard'
import Meeting from './components/Meeting'
import axios from 'axios'
import { validateToken, setupAxiosInterceptors } from './utils/auth'

// Create a theme instance
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

// Protected Route component for mentor only
const ProtectedRoute = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);

  useEffect(() => {
    const checkAuth = async () => {
      const isValid = await validateToken();
      setIsAuthenticated(isValid);
    };

    checkAuth();
  }, []);

  if (isAuthenticated === null) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return children;
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Setup axios interceptors
    setupAxiosInterceptors();

    const checkAuth = async () => {
      const isValid = await validateToken();
      setIsAuthenticated(isValid);
    };

    checkAuth();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    delete axios.defaults.headers.common['Authorization'];
    setIsAuthenticated(false);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <div className="App">
          <AppBar position="static">
            <Toolbar>
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                Mentor Dashboard
              </Typography>
              {isAuthenticated ? (
                <>
                  <Button color="inherit" component={Link} to="/mentor">
                    Dashboard
                  </Button>
                  <Button color="inherit" onClick={handleLogout}>
                    Logout
                  </Button>
                </>
              ) : (
                <Button color="inherit" component={Link} to="/login">
                  Login
                </Button>
              )}
            </Toolbar>
          </AppBar>
          <Container sx={{ mt: 4 }}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/meeting/:meetingId" element={<Meeting />} />
              <Route
                path="/mentor"
                element={
                  <ProtectedRoute>
                    <MentorDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/"
                element={
                  isAuthenticated ? (
                    <Navigate to="/mentor" />
                  ) : (
                    <Navigate to="/login" />
                  )
                }
              />
            </Routes>
          </Container>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App 