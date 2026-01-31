import { useState, useRef, useEffect } from 'react'
import './ChatBox.css'
import { chatAPI } from '../services/api'

function ChatBox({ videoId, onSeekToTime, isAnalyzing, userRole, onRoleChange }) {
  const [messages, setMessages] = useState({
    actor: [],
    director: []
  })
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, userRole])

  const handleRoleChange = (newRole) => {
    setIsTransitioning(true)
    setTimeout(() => {
      onRoleChange(newRole)
      setIsTransitioning(false)
    }, 150)
  }

  // Get current role's messages
  const currentMessages = messages[userRole] || []

  const formatTimestamp = (seconds) => {
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  const formatResultsToMessage = (results, role, answer, foundCount) => {
    // If we have an LLM answer, show it prominently
    if (answer) {
      if (!results || results.length === 0) {
        return {
          content: answer,
          timestamps: []
        }
      }

      const timestamps = results.map(r => r.second)
      const parts = []
      
      // Show LLM answer first
      parts.push(`${answer}\n\n`)
      
      if (results.length > 0) {
        parts.push(`**Relevant Moment${results.length > 1 ? 's' : ''}:**\n\n`)
        
    results.forEach((result, index) => {
      const timestamp = formatTimestamp(result.second)
      let description = ''
      
      if (role === 'director') {
        // Show technical information for director
        const tech = result.technical_info || {}
        description = `${tech.shot_type || 'unknown shot'}, ${tech.camera_angle || 'unknown angle'}, ${tech.lighting || 'unknown lighting'}`
      } else {
        // Show content information for actor
        const content = result.content_info || {}
        
        // Handle new emotion format (object) vs old format (array)
        let emotions_str = 'none'
        if (content.emotions) {
          if (typeof content.emotions === 'object' && !Array.isArray(content.emotions)) {
            // New format: { primary: "romantic", secondary: [...], intensity: "high" }
            emotions_str = content.emotions.primary || 'neutral'
            if (content.emotions.secondary && content.emotions.secondary.length > 0) {
              emotions_str += `, ${content.emotions.secondary.join(', ')}`
            }
          } else if (Array.isArray(content.emotions)) {
            // Old format: [{ type: "happy" }, ...]
            emotions_str = content.emotions.map(e => e.type || e).join(', ') || 'none'
          }
        }
        
        description = `${content.character_count || 0} character(s), emotions: ${emotions_str}`
      }
      
      const summary = result.scene_summary || 'No description'
      parts.push(`${index + 1}. [${timestamp}](${result.second}) - ${summary}\n   ${description}\n`)
    })
        
        parts.push('\nClick any timestamp to jump to that moment!')
      }
      
      return {
        content: parts.join(''),
        timestamps
      }
    }
    
    // Fallback for no answer (shouldn't happen with new API)
    if (!results || results.length === 0) {
      return {
        content: 'No results found for your query. Try rephrasing your question.',
        timestamps: []
      }
    }

    const timestamps = results.map(r => r.second)
    const parts = []
    
    parts.push(`Found ${results.length} relevant moment${results.length > 1 ? 's' : ''}:\n\n`)
    
    results.forEach((result, index) => {
      const timestamp = formatTimestamp(result.second)
      let description = ''
      
      if (role === 'director') {
        // Show technical information for director
        const tech = result.technical_info || {}
        description = `${tech.shot_type || 'unknown shot'}, ${tech.camera_angle || 'unknown angle'}, ${tech.lighting || 'unknown lighting'}`
      } else {
        // Show content information for actor
        const content = result.content_info || {}
        
        // Handle new emotion format (object) vs old format (array)
        let emotions_str = 'none'
        if (content.emotions) {
          if (typeof content.emotions === 'object' && !Array.isArray(content.emotions)) {
            // New format: { primary: "romantic", secondary: [...], intensity: "high" }
            emotions_str = content.emotions.primary || 'neutral'
            if (content.emotions.secondary && content.emotions.secondary.length > 0) {
              emotions_str += `, ${content.emotions.secondary.join(', ')}`
            }
          } else if (Array.isArray(content.emotions)) {
            // Old format: [{ type: "happy" }, ...]
            emotions_str = content.emotions.map(e => e.type || e).join(', ') || 'none'
          }
        }
        
        description = `${content.character_count || 0} character(s), emotions: ${emotions_str}`
      }
      
      const summary = result.scene_summary || 'No description'
      parts.push(`${index + 1}. [${timestamp}](${result.second}) - ${summary}\n   ${description}\n`)
    })
    
    parts.push('\nClick any timestamp to jump to that moment!')
    
    return {
      content: parts.join(''),
      timestamps
    }
  }

  const handleSend = async () => {
    if (!inputValue.trim() || !videoId || isLoading) return

    const userMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    }

    // Add to current role's messages
    setMessages(prev => ({
      ...prev,
      [userRole]: [...(prev[userRole] || []), userMessage]
    }))
    
    const question = inputValue.trim()
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await chatAPI.query(videoId, question, userRole, 5)
      const formatted = formatResultsToMessage(
        response.results, 
        userRole, 
        response.answer,  // LLM answer
        response.found_count  // Number of relevant moments
      )
      
      const assistantMessage = {
        role: 'assistant',
        content: formatted.content,
        timestamps: formatted.timestamps,
        timestamp: new Date()
      }
      
      // Add to current role's messages
      setMessages(prev => ({
        ...prev,
        [userRole]: [...(prev[userRole] || []), assistantMessage]
      }))
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.response?.data?.detail || error.message || 'Unknown error'}. Please try again.`,
        timestamps: [],
        timestamp: new Date()
      }
      setMessages(prev => ({
        ...prev,
        [userRole]: [...(prev[userRole] || []), errorMessage]
      }))
    } finally {
      setIsLoading(false)
    }
  }

  const handleTimestampClick = (seconds) => {
    if (onSeekToTime) {
      onSeekToTime(seconds)
    }
  }

  const formatMessage = (content, timestamps = []) => {
    // Replace [MM:SS](seconds) with clickable timestamps
    const parts = []
    const regex = /\[(\d+):(\d+)\]\((\d+)\)/g
    let lastIndex = 0
    let match

    while ((match = regex.exec(content)) !== null) {
      // Add text before the timestamp
      if (match.index > lastIndex) {
        parts.push({ type: 'text', content: content.substring(lastIndex, match.index) })
      }
      
      // Add clickable timestamp
      const minutes = match[1]
      const seconds = match[2]
      const totalSeconds = parseInt(match[3])
      parts.push({
        type: 'timestamp',
        content: `${minutes}:${seconds}`,
        seconds: totalSeconds
      })
      
      lastIndex = regex.lastIndex
    }
    
    // Add remaining text
    if (lastIndex < content.length) {
      parts.push({ type: 'text', content: content.substring(lastIndex) })
    }
    
    return parts.length > 0 ? parts : [{ type: 'text', content }]
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-box">
      <div className="chat-header">
        <h2>Ask Questions</h2>
        {videoId && !isAnalyzing && (
          <div className="role-selector">
            <label>I am a:</label>
            <div className="role-buttons">
              <button
                className={`role-button ${userRole === 'actor' ? 'active' : ''}`}
                onClick={() => handleRoleChange('actor')}
              >
                🎭 Actor
              </button>
              <button
                className={`role-button ${userRole === 'director' ? 'active' : ''}`}
                onClick={() => handleRoleChange('director')}
              >
                🎬 Director
              </button>
            </div>
          </div>
        )}
      </div>
      
      {!videoId ? (
        <div className="chat-placeholder">
          <p>Upload a video to start asking questions</p>
          <div className="demo-suggestions">
            <p className="suggestions-title">Example questions:</p>
            <div className="role-examples">
              <div className="role-example-box">
                <h4>🎭 Actor:</h4>
                <ul>
                  <li>"Show emotional scenes"</li>
                  <li>"Where is the character angry?"</li>
                  <li>"Find dialogue moments"</li>
                </ul>
              </div>
              <div className="role-example-box">
                <h4>🎬 Director:</h4>
                <ul>
                  <li>"Show wide angle shots"</li>
                  <li>"Find low lighting scenes"</li>
                  <li>"Where are close-ups?"</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      ) : isAnalyzing ? (
        <div className="chat-placeholder">
          <div className="spinner"></div>
          <p>Video is being analyzed...</p>
          <p className="analyzing-subtext">Please wait for analysis to complete before asking questions</p>
        </div>
      ) : (
        <>
          <div className={`messages-container ${isTransitioning ? 'transitioning' : ''}`}>
            {currentMessages.length === 0 ? (
              <div className="empty-state">
                <p>Ask me anything about the video!</p>
                <div className="demo-suggestions-inline">
                  <p className="suggestions-title">Example questions for {userRole === 'actor' ? 'Actor' : 'Director'}:</p>
                  {userRole === 'actor' ? (
                    <ul>
                      <li>"Show emotional scenes"</li>
                      <li>"Where are the characters?"</li>
                      <li>"Find action sequences"</li>
                      <li>"What emotions are shown?"</li>
                    </ul>
                  ) : (
                    <ul>
                      <li>"Show wide angle shots"</li>
                      <li>"Find low lighting scenes"</li>
                      <li>"Where are close-ups?"</li>
                      <li>"Show outdoor scenes"</li>
                    </ul>
                  )}
                </div>
              </div>
            ) : (
              currentMessages.map((message, index) => {
                const formattedParts = message.role === 'assistant' 
                  ? formatMessage(message.content, message.timestamps)
                  : [{ type: 'text', content: message.content }]
                
                return (
                  <div
                    key={index}
                    className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
                  >
                    <div className="message-content">
                      {formattedParts.map((part, partIndex) => {
                        if (part.type === 'timestamp') {
                          return (
                            <span
                              key={partIndex}
                              className="timestamp-link"
                              onClick={() => handleTimestampClick(part.seconds)}
                            >
                              {part.content}
                            </span>
                          )
                        }
                        return <span key={partIndex}>{part.content}</span>
                      })}
                    </div>
                  </div>
                )
              })
            )}
            {isLoading && (
              <div className="message assistant-message">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-container">
            <textarea
              className="chat-input"
              placeholder={`Ask a ${userRole} question about the video...`}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              rows={2}
              disabled={isLoading}
            />
            <button
              className="send-button"
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default ChatBox
