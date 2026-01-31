import { useRef, useState } from 'react'
import './VideoUpload.css'

function VideoUpload({ onVideoUpload, videoUrl, isProcessing, isAnalyzing, analysisStatus, videoRef }) {
  const fileInputRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('video/')) {
      onVideoUpload(file)
    }
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('video/')) {
      onVideoUpload(file)
    }
  }

  return (
    <div className="video-upload">
      <h2>Upload Video</h2>
      
      {!videoUrl ? (
        <div
          className={`upload-area ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="upload-content">
            <svg
              width="64"
              height="64"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p className="upload-text">Drag and drop your video here</p>
            <p className="upload-subtext">or</p>
            <button
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isProcessing}
            >
              Browse Files
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
          </div>
        </div>
      ) : (
        <div className="video-preview">
          <video
            ref={videoRef}
            src={videoUrl}
            controls
            className="preview-video"
          />
          {isAnalyzing && (
            <div className="processing-overlay">
              <div className="spinner"></div>
              
              {/* Overall Progress */}
              <div className="progress-section">
                <div className="progress-header">
                  <h3>Video Analysis Progress</h3>
                  <span className="progress-percentage">
                    {analysisStatus?.overall_progress?.percentage || 0}%
                  </span>
                </div>
                
                {/* Overall Progress Bar */}
                <div className="progress-bar-container">
                  <div 
                    className="progress-bar-fill"
                    style={{ 
                      width: `${analysisStatus?.overall_progress?.percentage || 0}%`,
                      transition: 'width 0.3s ease'
                    }}
                  ></div>
                </div>
                
                {/* Current Stage */}
                <p className="current-stage">
                  {analysisStatus?.status === 'generating_frames' && '📹 Generating frames from video...'}
                  {analysisStatus?.status === 'analyzing_frames' && '🤖 Analyzing frames with AI (this may take a while)...'}
                  {analysisStatus?.status === 'building_vector_db' && '💾 Building searchable database...'}
                  {!analysisStatus?.status && '🚀 Starting analysis...'}
                </p>
                
                {/* Stage-specific Progress */}
                {analysisStatus?.progress && (
                  <div className="stage-progress">
                    <div className="stage-progress-info">
                      <span>Frame {analysisStatus.progress.current} of {analysisStatus.progress.total}</span>
                      <span>{analysisStatus.progress.percentage}%</span>
                    </div>
                    <div className="stage-progress-bar">
                      <div 
                        className="stage-progress-fill"
                        style={{ 
                          width: `${analysisStatus.progress.percentage}%`,
                          transition: 'width 0.3s ease'
                        }}
                      ></div>
                    </div>
                  </div>
                )}
                
                {/* Estimated Time (if available) */}
                {analysisStatus?.overall_progress?.percentage > 0 && analysisStatus?.overall_progress?.percentage < 100 && (
                  <p className="progress-note">
                    Processing... Please wait. This may take several minutes depending on video length.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default VideoUpload
