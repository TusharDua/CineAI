# CINEAI Backend API Documentation

## Overview
FastAPI backend for video analysis with frame description generation and semantic search capabilities.

## Endpoints

### 1. Upload Video
**POST** `/upload-video`

Upload a video file to the system.

**Request:**
- Form data with `file` field (video file)

**Response:**
```json
{
  "video_id": "uuid-string",
  "filename": "video.mp4",
  "message": "Video uploaded successfully",
  "next_step": "Call /analyze-video/{video_id} to start analysis"
}
```

**Supported formats:** mp4, avi, mov, mkv, webm

---

### 2. Analyze Video
**POST** `/analyze-video/{video_id}`

Start video analysis process (runs in background):
1. Generate frames (1 frame per second)
2. Generate frame descriptions using Gemini 2.0
3. Generate embeddings
4. Build vector database

**Response:**
```json
{
  "video_id": "uuid-string",
  "status": "processing",
  "message": "Video analysis started. Use /status/{video_id} to check progress."
}
```

**Note:** This is an asynchronous operation. Use the status endpoint to check progress.

---

### 3. Get Analysis Status
**GET** `/status/{video_id}`

Get the current status of video analysis.

**Response:**
```json
{
  "video_id": "uuid-string",
  "status": "completed",
  "message": "Analysis completed successfully!",
  "progress": {
    "current": 100,
    "total": 100,
    "percentage": 100
  }
}
```

**Status values:**
- `not_started` - Analysis hasn't started
- `generating_frames` - Extracting frames from video
- `analyzing_frames` - Generating descriptions for frames
- `building_vector_db` - Creating embeddings and vector database
- `completed` - Analysis complete
- `failed` - Analysis failed

---

### 4. Chat/Query
**POST** `/chat`

Query the vector database to find relevant video frames.

**Request:**
```json
{
  "query": "show me scenes with a sword",
  "video_id": "uuid-string",
  "top_k": 5
}
```

**Response:**
```json
{
  "query": "show me scenes with a sword",
  "video_id": "uuid-string",
  "results": [
    {
      "second": 45,
      "timestamp": "00:45",
      "frame_path": "video_frames/{video_id}/frame_00045.jpg",
      "score": 0.892,
      "embedding_text": "Second: 45\nObjects: sword, person\n...",
      "llava_json": {
        "second": 45,
        "objects": [...],
        "actions": [...],
        "scene_summary": "..."
      }
    }
  ]
}
```

---

### 5. List Videos
**GET** `/videos`

List all uploaded videos.

**Response:**
```json
{
  "videos": [
    {
      "video_id": "uuid-string",
      "filename": "video.mp4",
      "size": 12345678
    }
  ]
}
```

---

## Usage Flow

1. **Upload video:**
   ```bash
   curl -X POST "http://localhost:8000/upload-video" \
     -F "file=@video.mp4"
   ```

2. **Start analysis:**
   ```bash
   curl -X POST "http://localhost:8000/analyze-video/{video_id}"
   ```

3. **Check status:**
   ```bash
   curl "http://localhost:8000/status/{video_id}"
   ```

4. **Query video:**
   ```bash
   curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "find scenes with a person sitting",
       "video_id": "{video_id}",
       "top_k": 5
     }'
   ```

## Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

Required in `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

## Directory Structure

```
backend/
├── main.py                 # FastAPI application
├── services/
│   ├── video_service.py    # Video upload and frame generation
│   ├── analysis_service.py # Frame description generation
│   ├── vector_db_service.py # Embedding and vector DB creation
│   └── retriever_service.py # Semantic search
├── uploads/                # Uploaded videos
├── video_frames/          # Generated frames (per video)
├── analysis_output/       # Analysis JSON files
├── analysis_status/       # Status tracking files
└── vector_databases/      # FAISS indexes and metadata
```
