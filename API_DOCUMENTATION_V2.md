# CINEAI API Documentation - Role-Based Retrieval

## Overview

The CINEAI backend provides role-based video analysis and retrieval. Users can query videos as either an **Actor** (focusing on content/performance) or a **Director** (focusing on cinematography/technical aspects).

---

## Base URL

```
http://localhost:8000
```

---

## Endpoints

### 1. Upload Video

Upload a video file for analysis.

**Endpoint:** `POST /upload-video`

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (video file)

**Supported Formats:** mp4, avi, mov, mkv, webm

**Response:**
```json
{
  "video_id": "uuid-string",
  "filename": "video.mp4",
  "message": "Video uploaded successfully",
  "next_step": "Call /analyze-video/{video_id} to start analysis"
}
```

---

### 2. Analyze Video

Start video analysis process (runs in background).

**Endpoint:** `POST /analyze-video/{video_id}`

**Process:**
1. Scene detection using PySceneDetect
2. Frame extraction (1 frame per second)
3. AI analysis with Gemini (technical + content)
4. Dual embedding generation
5. Build dual vector databases (technical + content)

**Response:**
```json
{
  "video_id": "uuid-string",
  "status": "processing",
  "message": "Video analysis started. Use /status/{video_id} to check progress."
}
```

---

### 3. Check Analysis Status

Get current analysis progress.

**Endpoint:** `GET /status/{video_id}`

**Response:**
```json
{
  "video_id": "uuid-string",
  "status": "analyzing_frames",
  "message": "Processing frame 15/60",
  "progress": {
    "current": 15,
    "total": 60,
    "percentage": 25,
    "stage": "analyzing_frames"
  },
  "overall_progress": {
    "percentage": 55,
    "stage": "analyzing_frames",
    "stage_progress": 0.25
  }
}
```

**Status Values:**
- `generating_frames` - Extracting frames from video
- `analyzing_frames` - Analyzing frames with Gemini AI
- `building_vector_db` - Creating dual vector databases
- `completed` - Analysis complete, ready for queries
- `failed` - Analysis failed

---

### 4. Query Video (Role-Based)

Search for relevant moments in the video based on role.

**Endpoint:** `POST /chat`

**Request Body:**
```json
{
  "query": "show me wide angle shots",
  "video_id": "uuid-string",
  "role": "director",  // "actor" or "director"
  "top_k": 5           // Number of results (optional, default: 5)
}
```

**Role Types:**
- `actor` - Content-focused search (objects, actions, emotions, characters)
- `director` - Technical-focused search (shot types, angles, lighting, composition)

**Response:**
```json
{
  "query": "show me wide angle shots",
  "video_id": "uuid-string",
  "role": "director",
  "results": [
    {
      "second": 45,
      "timestamp": "00:45",
      "frame_path": "video_frames/{video_id}/frame_00045.jpg",
      "score": 0.892,
      "scene_id": "scene_003",
      "technical_info": {
        "shot_type": "wide shot",
        "camera_angle": "eye level",
        "lighting": "natural",
        "scene_type": "outdoor"
      },
      "scene_summary": "Person walking through forest path",
      "embedding_text": "Second: 45\nShot Type: wide shot..."
    }
  ]
}
```

**Director Role Response Fields:**
- `technical_info` - Shot type, camera angle, lighting, scene type
- `scene_summary` - Brief scene description
- `embedding_text` - Technical embedding text

**Actor Role Response Fields:**
```json
{
  "second": 23,
  "timestamp": "00:23",
  "frame_path": "...",
  "score": 0.876,
  "scene_id": "scene_002",
  "content_info": {
    "objects": [{"type": "person"}, {"type": "chair"}],
    "actions": [{"type": "sitting"}],
    "emotions": [{"type": "sad", "intensity": "high"}],
    "character_count": 1
  },
  "scene_summary": "Character sitting alone, looking sad",
  "embedding_text": "Second: 23\nObjects: person, chair..."
}
```

---

### 5. List Videos

Get list of all uploaded videos.

**Endpoint:** `GET /videos`

**Response:**
```json
{
  "videos": [
    {
      "video_id": "uuid-1",
      "filename": "video1.mp4",
      "upload_time": "2024-01-15T10:30:00"
    },
    {
      "video_id": "uuid-2",
      "filename": "video2.mp4",
      "upload_time": "2024-01-15T11:45:00"
    }
  ]
}
```

---

## Example Queries

### Director Role Queries

Technical/cinematography-focused queries:

```json
{"query": "Show me all wide angle shots", "role": "director"}
{"query": "Find scenes with low lighting", "role": "director"}
{"query": "Where are the close-up shots?", "role": "director"}
{"query": "Show high angle camera scenes", "role": "director"}
{"query": "Find outdoor scenes", "role": "director"}
{"query": "Show me natural lighting", "role": "director"}
{"query": "Where is backlit lighting used?", "role": "director"}
```

### Actor Role Queries

Content/performance-focused queries:

```json
{"query": "Show emotional scenes", "role": "actor"}
{"query": "Find dialogue moments", "role": "actor"}
{"query": "Where is the character angry?", "role": "actor"}
{"query": "Show action sequences", "role": "actor"}
{"query": "Find group scenes", "role": "actor"}
{"query": "Show happy moments", "role": "actor"}
{"query": "Where are characters interacting?", "role": "actor"}
```

---

## Data Structures

### Frame Analysis Structure

```json
{
  "second": 0,
  "scene_id": "scene_001",
  "technical_info": {
    "shot_type": "wide shot | medium shot | close-up | extreme close-up",
    "camera_angle": "eye level | high angle | low angle | bird's eye",
    "lighting": "natural | artificial | high key | low key | backlit",
    "scene_type": "indoor | outdoor"
  },
  "content_info": {
    "objects": [{"type": "object_name"}],
    "actions": [{"type": "action_name"}],
    "emotions": [{"type": "emotion", "intensity": "low|medium|high"}],
    "character_count": 0,
    "scene_summary": "Description of what's happening"
  },
  "embedding_text_technical": "Technical embedding for director searches",
  "embedding_text_content": "Content embedding for actor searches"
}
```

### Scene Structure

```json
{
  "scene_id": "scene_001",
  "start_second": 0,
  "end_second": 15,
  "start_frame": 0,
  "end_frame": 15
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid role. Must be 'actor' or 'director'"
}
```

### 404 Not Found
```json
{
  "detail": "Video not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limiting

The backend uses Gemini API which has rate limits:
- **Vision API**: ~10 requests per minute
- **Embedding API**: Built-in rate limiting

The system automatically handles rate limiting with:
- 7-second delay between frame analyses
- Exponential backoff on 429 errors
- Automatic retries (up to 5 attempts)

---

## Storage Structure

```
backend/
├── uploads/                          # Uploaded videos
│   └── {video_id}.mp4
├── video_frames/                     # Extracted frames
│   └── {video_id}/
│       ├── frame_00000.jpg
│       ├── frame_00001.jpg
│       └── ...
├── analysis_output/                  # Analysis results
│   └── {video_id}_analysis.json
├── analysis_status/                  # Status tracking
│   └── {video_id}_status.json
└── vector_databases/                 # FAISS indices
    ├── {video_id}_technical.index    # Director searches
    ├── {video_id}_content.index      # Actor searches
    └── {video_id}_metadata.json      # Shared metadata
```

---

## Environment Variables

Required in `.env` file:

```bash
GEMINI_API_KEY=your_api_key_here
```

---

## Technical Implementation

### Scene Detection
- **Library**: PySceneDetect with ContentDetector
- **Threshold**: 27.0 (default, balanced)
- **Output**: List of scenes with timestamps

### AI Analysis
- **Model**: Gemini 2.0 Flash Experimental
- **Input**: Frame image + structured prompt
- **Output**: JSON with technical + content details
- **Rate**: ~7 seconds per frame

### Embeddings
- **Model**: Gemini Embedding (`models/gemini-embedding-001`)
- **Dimension**: 768
- **Types**: 
  - Technical (for director): Shot type, angle, lighting
  - Content (for actor): Objects, actions, emotions

### Vector Database
- **Library**: FAISS
- **Index Type**: IndexFlatIP (Inner Product / Cosine Similarity)
- **Indices**: 2 separate indices per video (technical + content)
- **Search**: Role-based index selection

---

## Performance

### Analysis Time (60-second video)
- Scene detection: ~15 seconds
- Frame extraction: ~5 seconds
- AI analysis: ~7 minutes (60 frames × 7s)
- Embedding generation: ~2 minutes (dual embeddings)
- Vector DB build: ~10 seconds
- **Total**: ~10 minutes

### Query Performance
- Index load: <100ms (cached after first load)
- Embedding generation: ~200ms
- FAISS search: <10ms
- **Total query time**: <500ms

---

## Migration from Old System

⚠️ **Important**: Videos analyzed with the old system are not compatible.

**Migration Steps:**
1. Install new dependencies: `pip install -r requirements.txt`
2. Re-upload videos
3. Re-analyze videos with new system
4. Old vector databases will be ignored

**Why re-analysis is needed:**
- New dual embedding structure
- Enhanced frame analysis (technical + content)
- Scene detection integration
- Dual vector database indices

---

## Best Practices

### Query Tips

**For Directors:**
- Be specific about cinematography: "wide shots", "low angle"
- Mention lighting: "natural", "backlit", "low key"
- Specify location: "outdoor scenes", "indoor shots"

**For Actors:**
- Focus on emotions: "angry", "happy", "sad"
- Mention actions: "running", "dialogue", "fighting"
- Describe interactions: "group scenes", "solo moments"

### Performance Tips

1. **Batch operations**: Upload and analyze multiple videos together
2. **Cache results**: Results are cached per video_id
3. **Adjust top_k**: Request only needed results (default: 5)
4. **Monitor status**: Poll `/status` endpoint during analysis

---

## Troubleshooting

### Issue: Analysis Stuck
**Check:** `/status/{video_id}` endpoint for current stage
**Solution:** Check backend logs for Gemini API errors

### Issue: Poor Search Results
**Check:** Role matches query intent (actor vs director)
**Solution:** Rephrase query or switch role

### Issue: Rate Limit Errors
**Check:** Backend logs for 429 errors
**Solution:** System auto-handles, but may need longer analysis time

---

## Support

For issues or questions:
1. Check backend logs for detailed error messages
2. Verify Gemini API key is valid
3. Ensure video format is supported
4. Confirm role parameter is correct ("actor" or "director")

---

## Version

**API Version**: 2.0.0 (Role-Based Retrieval)
**Last Updated**: January 2025
