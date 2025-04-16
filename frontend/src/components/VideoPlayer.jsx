import React, { useRef, useState, useEffect } from 'react';
import Hls from 'hls.js';
import { Box, IconButton, Slider, Typography, Menu, MenuItem } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import VolumeOffIcon from '@mui/icons-material/VolumeOff';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import SettingsIcon from '@mui/icons-material/Settings';

const VideoPlayer = ({ videoUrl, signedUrls }) => {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [qualityLevels, setQualityLevels] = useState([]);
  const [currentQuality, setCurrentQuality] = useState('auto');
  const [anchorEl, setAnchorEl] = useState(null);

  const initializeHls = () => {
    if (hlsRef.current) {
      hlsRef.current.destroy();
    }

    const hls = new Hls({
        debug: true,
        enableWorker: true,
      lowLatencyMode: false,
      backBufferLength: 90,
      maxBufferLength: 30,
      maxMaxBufferLength: 600,
      maxBufferSize: 60 * 1000 * 1000,
      maxBufferHole: 0.5,
      autoStartLoad: false,
      startLevel: 0,
      capLevelToPlayerSize: false,
      abrEwmaDefaultEstimate: 500000,
      abrEnabled: false,
      abrBandWidthFactor: 0.95,
      abrBandWidthUpFactor: 0.7,
      abrMaxWithRealBitrate: true,
      testBandwidth: false,
      progressive: true,
      loader: class CustomLoader extends Hls.DefaultConfig.loader {
        constructor(config) {
          super(config);
          const load = this.load.bind(this);
          this.load = (context, config, callbacks) => {
            if (context.type === 'manifest' || context.type === 'level') {
              // Extract quality from the URL path
              const urlParts = context.url.split('/');
              const fileName = urlParts[urlParts.length - 1];
              const qualityMatch = fileName.match(/_(\d+p)\.m3u8$/);
              
              if (qualityMatch && signedUrls?.[qualityMatch[1]]) {
                console.log(`Replacing URL for quality ${qualityMatch[1]}:`, context.url);
                context.url = signedUrls[qualityMatch[1]];
              } else if (fileName.endsWith('.m3u8') && signedUrls?.master) {
                console.log('Replacing master manifest URL:', context.url);
                context.url = signedUrls.master;
              }
            } else if (context.type === 'frag' && context.url.endsWith('.ts')) {
              // Handle segment files
              const urlParts = context.url.split('/');
              const segmentName = urlParts[urlParts.length - 1];
              const qualityMatch = segmentName.match(/_(\d+p)_/);
              
              if (qualityMatch && signedUrls?.[`segment_${qualityMatch[1]}`]) {
                const baseUrl = signedUrls[`segment_${qualityMatch[1]}`];
                const urlObj = new URL(baseUrl);
                const pathParts = urlObj.pathname.split('/');
                const segmentNumber = segmentName.split('_').pop();
                pathParts[pathParts.length - 1] = pathParts[pathParts.length - 1].replace('00001.ts', segmentNumber);
                urlObj.pathname = pathParts.join('/');
                
                console.log('Replacing segment URL:', context.url, 'with:', urlObj.toString());
                context.url = urlObj.toString();
              }
            }
            load(context, config, callbacks);
          };
        }
      }
    });

    hlsRef.current = hls;

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
      console.log('Manifest parsed, levels:', hls.levels);
      
      // Find 320p quality level
      const level320Index = hls.levels.findIndex(level => level.height === 320);
      
      if (level320Index !== -1) {
        console.log('Found 320p quality at index:', level320Index);
        // Force 320p before starting load
        hls.currentLevel = level320Index;
        hls.loadLevel = level320Index;
        hls.nextLevel = level320Index;
        hls.startLevel = level320Index;
        setCurrentQuality(level320Index);
      } else {
        // Find closest lower quality
        const closestLevel = hls.levels.reduce((prev, curr) => {
          if (curr.height <= 320 && (!prev || curr.height > prev.height)) {
            return curr;
          }
          return prev;
        }, null);
        
        if (closestLevel) {
          const index = hls.levels.indexOf(closestLevel);
          console.log(`Using closest quality: ${closestLevel.height}p at index:`, index);
          hls.currentLevel = index;
          hls.loadLevel = index;
          hls.nextLevel = index;
          hls.startLevel = index;
          setCurrentQuality(index);
        }
      }
      
      // Start loading only after setting quality
      console.log('Starting load with forced quality level');
      hls.startLoad();
      
      // Update quality options in UI
      const qualityOptions = hls.levels.map((level, index) => ({
        id: index,
        height: level.height,
        width: level.width,
        bitrate: level.bitrate,
        name: `${level.height}p (${Math.round(level.bitrate / 1000)}kbps)`
      }));
      setQualityLevels(qualityOptions);
    });

    hls.on(Hls.Events.LEVEL_LOADED, (event, data) => {
      console.log('Level loaded:', data);
      const levels = hls.levels;
      if (levels && levels.length > 0) {
        const qualityOptions = levels.map((level, index) => ({
          id: index,
          height: level.height,
          width: level.width,
          bitrate: level.bitrate,
          name: `${level.height}p (${Math.round(level.bitrate / 1000)}kbps)`
        }));
        console.log('Updated quality options:', qualityOptions);
        setQualityLevels(qualityOptions);
      }
    });

    hls.on(Hls.Events.LEVEL_SWITCHED, (event, data) => {
      console.log('Level switched:', data);
      setCurrentQuality(data.level);
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
      console.error('HLS Error:', data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
            console.log('Network error, attempting to recover...');
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
            console.log('Media error, attempting to recover...');
              hls.recoverMediaError();
              break;
            default:
            console.log('Fatal error, destroying HLS instance...');
              hls.destroy();
              break;
          }
        }
    });

    return hls;
  };

  useEffect(() => {
    if (!videoUrl) return;

    const video = videoRef.current;
    if (!video) return;

    if (videoUrl.includes('.m3u8')) {
      if (Hls.isSupported()) {
        console.log('HLS is supported, initializing player...');
        console.log('Video URL:', videoUrl);
        
        const hls = initializeHls();
        console.log('HLS instance created:', hls);
        
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          console.log('Manifest parsed, levels:', hls.levels);
          
          // Find 320p quality level
          const level320Index = hls.levels.findIndex(level => level.height === 320);
          
          if (level320Index !== -1) {
            console.log('Found 320p quality at index:', level320Index);
            // Force 320p before starting load
            hls.currentLevel = level320Index;
            hls.loadLevel = level320Index;
            hls.nextLevel = level320Index;
            hls.startLevel = level320Index;
            setCurrentQuality(level320Index);
          } else {
            // Find closest lower quality
            const closestLevel = hls.levels.reduce((prev, curr) => {
              if (curr.height <= 320 && (!prev || curr.height > prev.height)) {
                return curr;
              }
              return prev;
            }, null);
            
            if (closestLevel) {
              const index = hls.levels.indexOf(closestLevel);
              console.log(`Using closest quality: ${closestLevel.height}p at index:`, index);
              hls.currentLevel = index;
              hls.loadLevel = index;
              hls.nextLevel = index;
              hls.startLevel = index;
              setCurrentQuality(index);
            }
          }
          
          // Start loading only after setting quality
          console.log('Starting load with forced quality level');
          hls.startLoad();
          
          // Update quality options in UI
          const qualityOptions = hls.levels.map((level, index) => ({
            id: index,
            height: level.height,
            width: level.width,
            bitrate: level.bitrate,
            name: `${level.height}p (${Math.round(level.bitrate / 1000)}kbps)`
          }));
          setQualityLevels(qualityOptions);
        });
        
        hls.loadSource(videoUrl);
        hls.attachMedia(video);
        
        video.play().catch(error => {
          console.error('Error playing video:', error);
      });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        console.log('Using native HLS support');
        video.src = videoUrl;
        video.addEventListener('loadedmetadata', () => {
          video.play().catch(error => {
            console.error('Error playing video:', error);
          });
        });
      } else {
        console.error('HLS is not supported in this browser');
      }
    } else {
      console.log('Non-HLS video source detected');
      video.src = videoUrl;
      video.addEventListener('loadedmetadata', () => {
        video.play().catch(error => {
          console.error('Error playing video:', error);
        });
      });
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      video.src = '';
    };
  }, [videoUrl]);

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (event, newValue) => {
    if (videoRef.current) {
      videoRef.current.currentTime = newValue;
      setCurrentTime(newValue);
    }
  };

  const handleVolumeChange = (event, newValue) => {
    if (videoRef.current) {
      videoRef.current.volume = newValue;
      setVolume(newValue);
      setIsMuted(newValue === 0);
    }
  };

  const handleMuteToggle = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleFullscreenToggle = () => {
    if (!document.fullscreenElement) {
      videoRef.current.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleQualityClick = (event) => {
    console.log(qualityLevels)
    setAnchorEl(event.currentTarget);
  };

  const handleQualityClose = () => {
    setAnchorEl(null);
  };

  const handleQualityChange = (levelId) => {
    if (hlsRef.current) {
      console.log('Changing quality to:', levelId);
      if (levelId === 'auto') {
        hlsRef.current.currentLevel = -1;
        hlsRef.current.loadLevel = -1;  // Force auto quality
        console.log('Switched to auto quality mode');
      } else {
        hlsRef.current.nextLevel = levelId;  // Switch at next segment boundary
        hlsRef.current.loadLevel = levelId;  // Start loading the new quality
        console.log(`Switching to quality level ${levelId}`);
      }
      setCurrentQuality(levelId);
    }
    handleQualityClose();
  };

  // Add quality switch monitoring
  useEffect(() => {
    if (hlsRef.current) {
      hlsRef.current.on(Hls.Events.LEVEL_SWITCHING, (event, data) => {
        console.log('Quality switching in progress:', data);
      });

      hlsRef.current.on(Hls.Events.LEVEL_SWITCHED, (event, data) => {
        console.log('Quality switch completed:', data);
        const newLevel = hlsRef.current.levels[data.level];
        console.log(`Now playing at ${newLevel.height}p (${Math.round(newLevel.bitrate / 1000)}kbps)`);
      });
    }
  }, []);

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <Box sx={{ position: 'relative', width: '100%', maxWidth: '1000px', margin: '0 auto' }}>
      <video
        ref={videoRef}
        style={{ width: '100%', height: 'auto' }}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleTimeUpdate}
      />
      <Box
        sx={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          background: 'linear-gradient(transparent, rgba(0,0,0,0.7))',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}
      >
        <Slider
          value={currentTime}
          max={duration}
          onChange={handleSeek}
          sx={{
            color: 'white',
            '& .MuiSlider-thumb': {
              width: 12,
              height: 12,
            },
          }}
        />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <IconButton onClick={handlePlayPause} sx={{ color: 'white' }}>
              {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
            </IconButton>
            <IconButton onClick={handleMuteToggle} sx={{ color: 'white' }}>
              {isMuted ? <VolumeOffIcon /> : <VolumeUpIcon />}
            </IconButton>
            <Slider
              value={volume}
              min={0}
              max={1}
              step={0.1}
              onChange={handleVolumeChange}
              sx={{
                width: '100px',
                color: 'white',
                '& .MuiSlider-thumb': {
                  width: 12,
                  height: 12,
                },
              }}
            />
            <Typography variant="body2" sx={{ color: 'white' }}>
              {formatTime(currentTime)} / {formatTime(duration)}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <IconButton 
              onClick={handleQualityClick} 
              sx={{ 
                color: 'white',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)'
                }
              }}
            >
              <SettingsIcon />
            </IconButton>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleQualityClose}
              PaperProps={{
                sx: {
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  color: 'white',
                  '& .MuiMenuItem-root': {
                    color: 'white',
                    '&:hover': {
                      backgroundColor: 'rgba(255, 255, 255, 0.1)'
                    },
                    '&.Mui-selected': {
                      backgroundColor: 'rgba(255, 255, 255, 0.2)'
                    }
                  }
                }
              }}
            >
              <MenuItem onClick={() => handleQualityChange('auto')} selected={currentQuality === 'auto'}>
                Auto
              </MenuItem>
              {qualityLevels.map((level) => (
                <MenuItem
                  key={level.id}
                  onClick={() => handleQualityChange(level.id)}
                  selected={currentQuality === level.id}
                >
                  {level.name}
            </MenuItem>
          ))}
            </Menu>
            <IconButton onClick={handleFullscreenToggle} sx={{ color: 'white' }}>
              {isFullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
            </IconButton>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default VideoPlayer; 