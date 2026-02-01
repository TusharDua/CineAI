import { useState, useRef, useEffect } from 'react'
import './App.css'
import VideoUpload from './components/VideoUpload'
import ChatBox from './components/ChatBox'
import { videoAPI } from './services/api'

function App() {
  const [videoFile, setVideoFile] = useState(null)
  const [videoUrl, setVideoUrl] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [videoId, setVideoId] = useState(null)
  const [analysisStatus, setAnalysisStatus] = useState(null)
  const [error, setError] = useState(null)
  const [userRole, setUserRole] = useState('actor')
  const [availableVideos, setAvailableVideos] = useState([])
  const [showVideoSelector, setShowVideoSelector] = useState(false)
  const videoRef = useRef(null)
  const statusPollInterval = useRef(null)

  // Load available videos on mount
  useEffect(() => {
    loadAvailableVideos()
  }, [])

  const loadAvailableVideos = async () => {
    try {
      const response = await videoAPI.listVideos()
      const readyVideos = response.videos.filter(v => v.can_query)
      setAvailableVideos(readyVideos)
    } catch (err) {
      console.error('Error loading videos:', err)
    }
  }

  // Poll for analysis status
  useEffect(() => {
    if (videoId && isAnalyzing) {
      statusPollInterval.current = setInterval(async () => {
        try {
          const status = await videoAPI.getStatus(videoId)
          setAnalysisStatus(status)
          
          if (status.status === 'completed') {
            setIsAnalyzing(false)
            setIsProcessing(false)
            if (statusPollInterval.current) {
              clearInterval(statusPollInterval.current)
            }
          } else if (status.status === 'failed') {
            setIsAnalyzing(false)
            setIsProcessing(false)
            setError(status.message || 'Analysis failed')
            if (statusPollInterval.current) {
              clearInterval(statusPollInterval.current)
            }
          }
        } catch (err) {
          console.error('Error checking status:', err)
        }
      }, 2000) // Poll every 2 seconds
    }

    return () => {
      if (statusPollInterval.current) {
        clearInterval(statusPollInterval.current)
      }
    }
  }, [videoId, isAnalyzing])

  const handleVideoUpload = async (file) => {
    try {
      setError(null)
      setVideoFile(file)
      setVideoUrl(URL.createObjectURL(file))
      setIsProcessing(true)

      // Upload video
      const uploadResponse = await videoAPI.uploadVideo(file)
      const newVideoId = uploadResponse.video_id
      setVideoId(newVideoId)

      // Start analysis
      setIsAnalyzing(true)
      await videoAPI.analyzeVideo(newVideoId)
      
      // Status polling will handle the rest
    } catch (err) {
      console.error('Upload error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to upload video')
      setIsProcessing(false)
      setIsAnalyzing(false)
    }
  }

  const handleSelectExistingVideo = (selectedVideo) => {
    setVideoId(selectedVideo.video_id)
    setVideoUrl(`http://localhost:8000/uploads/${selectedVideo.video_id}.${selectedVideo.filename.split('.').pop()}`)
    setShowVideoSelector(false)
    setIsAnalyzing(false)
    setIsProcessing(false)
  }

  const handleSeekToTime = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds
      videoRef.current.play()
    }
  }

  return (
    <div className="app">
      <div className="app-container">
        <header className="app-header">
          <div className="header-content">
            <h1>CINEAI</h1>
            <p>Role-Based Intelligent Video Retrieval for Filmmakers</p>
          </div>
          <button 
            className="select-video-btn"
            onClick={() => setShowVideoSelector(true)}
          >
            📁 Select Previous Video {availableVideos.length > 0 && `(${availableVideos.length})`}
          </button>
        </header>
        
        {error && (
          <div className="error-banner">
            <p>⚠️ {error}</p>
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {showVideoSelector && (
          <div className="video-selector-modal">
            <div className="modal-content">
              <div className="modal-header">
                <h2>Select a Previously Analyzed Video</h2>
                <button onClick={() => setShowVideoSelector(false)}>✕</button>
              </div>
              <div className="video-list">
                {availableVideos.length === 0 ? (
                  <div className="no-videos-message">
                    <p>📹 No analyzed videos yet</p>
                    <p className="subtext">Upload and analyze a video first, then you can select it from here next time.</p>
                  </div>
                ) : (
                  availableVideos.map((video) => (
                    <div 
                      key={video.video_id} 
                      className="video-item"
                      onClick={() => handleSelectExistingVideo(video)}
                    >
                      <div className="video-info">
                        <h3>{video.filename}</h3>
                        <p>Uploaded: {new Date(video.upload_time * 1000).toLocaleString()}</p>
                        <p className="status-badge">✓ Ready to Query</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
        
        <div className="main-content">
          <div className="upload-section">
            <VideoUpload 
              onVideoUpload={handleVideoUpload}
              videoUrl={videoUrl}
              isProcessing={isProcessing}
              isAnalyzing={isAnalyzing}
              analysisStatus={analysisStatus}
              videoRef={videoRef}
            />
          </div>
          
          <div className="chat-section">
            <ChatBox 
              videoId={videoId} 
              onSeekToTime={handleSeekToTime}
              isAnalyzing={isAnalyzing}
              userRole={userRole}
              onRoleChange={setUserRole}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
