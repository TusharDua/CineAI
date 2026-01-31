# Frontend Integration Guide

## Overview
The frontend has been fully integrated with the FastAPI backend. All demo/mock functionality has been replaced with real API calls.

## Changes Made

### 1. API Service (`src/services/api.js`)
- Created centralized API service using Axios
- Configured base URL (defaults to `http://localhost:8000`)
- Exported `videoAPI` and `chatAPI` modules

### 2. App Component (`src/App.jsx`)
**New Features:**
- Real video upload via `/upload-video` endpoint
- Automatic analysis triggering after upload
- Status polling every 2 seconds during analysis
- Error handling with user-friendly error banner
- Progress tracking with real-time updates

**State Management:**
- `analysisStatus` - Current analysis status from backend
- `error` - Error messages for user feedback
- Automatic cleanup of polling intervals

### 3. VideoUpload Component (`src/components/VideoUpload.jsx`)
**Updates:**
- Shows real analysis progress from backend
- Displays current stage (generating_frames, analyzing_frames, building_vector_db)
- Shows frame progress percentage when available
- Displays status messages from backend

### 4. ChatBox Component (`src/components/ChatBox.jsx`)
**Major Changes:**
- Removed all demo/mock responses
- Integrated with `/chat` endpoint
- Real semantic search using vector database
- Formats results with timestamps and descriptions
- Shows loading state during queries
- Displays message when video is still being analyzed
- Error handling for API failures

**Response Formatting:**
- Converts backend results to user-friendly messages
- Extracts timestamps from results
- Formats as clickable timestamp links

## API Integration Flow

### Video Upload & Analysis Flow:
1. User uploads video → `POST /upload-video`
2. Receives `video_id` from backend
3. Automatically triggers → `POST /analyze-video/{video_id}`
4. Polls → `GET /status/{video_id}` every 2 seconds
5. Updates UI with progress until `status === 'completed'`

### Chat Flow:
1. User enters query
2. Sends → `POST /chat` with `video_id`, `query`, `top_k`
3. Receives results with timestamps and descriptions
4. Formats and displays results
5. User clicks timestamp → video seeks to that time

## Environment Configuration

Create a `.env` file in the frontend directory:
```env
VITE_API_URL=http://localhost:8000
```

Or use the default (localhost:8000) if not specified.

## Features

✅ Real video upload with progress
✅ Live analysis status updates
✅ Progress percentage display
✅ Error handling and user feedback
✅ Semantic search with vector database
✅ Clickable timestamps for video navigation
✅ Loading states and animations
✅ Responsive design maintained

## Running the Application

1. **Start Backend:**
   ```bash
   cd backend
   python main.py
   # Or: uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm install  # If not already done
   npm run dev
   ```

3. **Access:**
   - Frontend: http://localhost:5173 (or Vite default port)
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Testing

1. Upload a video file (mp4, avi, mov, mkv, webm)
2. Wait for analysis to complete (progress shown in UI)
3. Once complete, ask questions like:
   - "Show me scenes with a person"
   - "What objects are in the video?"
   - "Describe the actions"
   - "Find moments with a sword"

## Error Handling

- Network errors are caught and displayed
- Invalid video files show error message
- Analysis failures are reported to user
- Chat errors show friendly error messages
- All errors can be dismissed by user

## Status Polling

The app automatically polls for analysis status every 2 seconds when:
- Video is uploaded
- Analysis is in progress
- Status is not 'completed' or 'failed'

Polling stops automatically when:
- Analysis completes
- Analysis fails
- Component unmounts
