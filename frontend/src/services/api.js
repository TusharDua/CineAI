import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Video API
export const videoAPI = {
  // Upload video
  uploadVideo: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post('/api/upload-video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Start video analysis
  analyzeVideo: async (videoId) => {
    const response = await api.post(`/api/analyze-video/${videoId}`)
    return response.data
  },

  // Get analysis status
  getStatus: async (videoId) => {
    const response = await api.get(`/api/status/${videoId}`)
    return response.data
  },

  // List all videos
  listVideos: async () => {
    const response = await api.get('/api/videos')
    return response.data
  },
}

// Chat API
export const chatAPI = {
  // Query video with role
  query: async (videoId, query, role = 'actor', topK = 5) => {
    const response = await api.post('/api/chat', {
      video_id: videoId,
      query,
      role,  // Add role parameter
      top_k: topK,
    })
    return response.data
  },
}

export default api
