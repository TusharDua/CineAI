# CINEAI - Role-Based Intelligent Video Retrieval

**Semantic video search powered by AI for filmmakers, actors, and production teams**

CINEAI is an advanced video analysis and retrieval system that uses AI to understand video content from multiple perspectives. Ask questions in natural language and get precise timestamps to relevant moments, tailored to your role.

---

## 🌟 Key Features

### 🎭 **Role-Based Search**
Search the same video from three different perspectives:
- **Actor Mode**: Find emotional moments, character interactions, dialogue scenes
- **Director Mode**: Search for cinematography techniques, shot types, lighting, camera angles
- **Producer Mode**: Locate props, production elements, locations, and set details

### 🤖 **AI-Powered Analysis**
- **Google Gemini Vision API** for intelligent frame analysis
- **Dual Embedding System** with separate FAISS indices for each role
- **Scene Detection** using PySceneDetect for smart content grouping
- **LLM Answer Generation** for natural, conversational responses

### ⚡ **Smart Retrieval**
- Semantic search understands meaning, not just keywords
- Get ranked results with relevance scores
- Clickable timestamps to jump directly to moments
- Context-aware answers with supporting evidence

---

## 📋 Sample Questions

### 🎭 Actor Mode
```
"When did the character get angry?"
"Order the anger scenes by the intensity of the emotion"
"Show me confrontational moments between characters"
"Find all romantic scenes"
```

### 🎬 Director Mode
```
"Show me the scene where light suddenly transitions"
"What are the wide angle shots?"
"Which timestamp has the closeup shot?"
"Find low lighting scenes"
```

### 💼 Producer Mode
```
"When did this object first appear in the video?"
"Tell me the frames with weapons/tools?"
"Sequence the objects with timestamps"
"Show high-budget scenes"
```

---

## 🏗️ Architecture

```
Video Upload
    ↓
Scene Detection (PySceneDetect)
    ↓
Frame Extraction (1 fps)
    ↓
Gemini AI Analysis (Technical + Content + Production)
    ↓
Triple Embedding Generation
    ↓
Build Three FAISS Indices:
    - Technical Index (Director)
    - Content Index (Actor)
    - Production Index (Producer)
    ↓
Ready for Role-Based Queries!
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google Gemini API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GEMINI_API_KEY=your_api_key_here" > .env

# Run server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Visit **http://localhost:3000** to use the application!

---

## 📁 Project Structure

```
CINEAI/
├── backend/
│   ├── main.py                          # FastAPI server
│   ├── services/
│   │   ├── analysis_service.py          # AI frame analysis
│   │   ├── scene_detection_service.py   # Scene grouping
│   │   ├── vector_db_service.py         # FAISS index management
│   │   └── retriever_service.py         # Role-based search
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── VideoUpload.jsx
│   │   │   └── ChatBox.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
└── deployment/                          # GCP deployment guides
```

---

## 🔧 API Endpoints

### Upload & Analysis
```
POST /upload-video          # Upload video file
POST /analyze-video/{id}    # Start AI analysis
GET  /status/{id}           # Check analysis progress
GET  /videos                # List all videos
```

### Query
```
POST /chat
{
  "video_id": "uuid",
  "query": "Show romantic scenes",
  "role": "actor",      // "actor", "director", or "producer"
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "I found 3 romantic moments in the video...",
  "results": [
    {
      "second": 45,
      "timestamp": "00:45",
      "score": 0.892,
      "scene_summary": "Two characters holding hands",
      "content_info": {
        "emotions": {"primary": "romantic", "intensity": "high"},
        "character_count": 2
      }
    }
  ]
}
```

---

## 🎯 How It Works

### 1. **Video Analysis** (~10 min for 1-min video)
- Extract frames at 1 fps
- Detect scene boundaries
- Analyze each frame with Gemini Vision API
- Generate three types of embeddings:
  - **Technical** (shot type, angle, lighting)
  - **Content** (emotions, actions, characters)
  - **Production** (props, locations, budget indicators)

### 2. **Dual Vector Database**
- Three separate FAISS indices for optimal accuracy
- L2-normalized embeddings for cosine similarity
- Role-based index selection for targeted results

### 3. **Intelligent Retrieval**
- Embed user query based on selected role
- Search appropriate FAISS index
- Generate natural language answer with LLM
- Return ranked results with timestamps

---

## 💡 Technical Details

### AI Models
- **Vision**: Gemini 2.0 Flash Experimental
- **Embeddings**: `models/gemini-embedding-001` (768 dimensions)
- **Answer Generation**: Gemini Flash with prompt engineering

### Performance
- **Analysis**: ~7 seconds per frame
- **Query**: <500ms after index load
- **Storage**: ~13.5MB per minute of video

### Rate Limiting
- Conservative 8 requests/min to Gemini API
- Sliding window rate limiter
- Automatic retry with exponential backoff

### Technologies Used
- Python
- gemini 
- Faiss 
- React
- GCP for hosting

---

## 🎨 Features

### Real-Time Progress Tracking
- Overall progress percentage
- Stage-specific progress (frames, analysis, DB building)
- Visual progress bars
- Estimated time remaining

### Role Switching
- Switch between Actor/Director/Producer modes
- Separate conversation history per role
- Role-specific query suggestions
- Smooth transitions

### Video Selector
- Browse previously analyzed videos
- See upload time and ready status
- Quick selection without re-analysis

---

## 📊 Example Workflow

1. **Upload Video**: Drag & drop or browse for video file
2. **Wait for Analysis**: ~10 min for 1-min video (watch progress bar)
3. **Select Role**: Choose Actor, Director, or Producer
4. **Ask Questions**: Type natural language queries
5. **Get Results**: View AI-generated answers with timestamps
6. **Navigate Video**: Click timestamps to jump to moments

---

## 🐛 Troubleshooting

### Backend Issues
```bash
# Check logs
sudo journalctl -u cineai-api -f

# Restart service
sudo systemctl restart cineai-api
```

### Frontend Issues
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Analysis Stuck
- Check Gemini API key is valid
- Verify rate limiting isn't blocking requests
- Review backend logs for errors

---

## 📚 Documentation

- **[API Documentation](API_DOCUMENTATION_V2.md)**: Complete API reference
- **[User Guide](USER_GUIDE_ROLE_BASED.md)**: Detailed usage instructions
- **[Implementation Guide](ROLE_BASED_IMPLEMENTATION.md)**: Technical deep dive
- **[Deployment Guides](deployment/)**: Step-by-step deployment instructions

---

## 🎓 Use Cases

### **Film Students**
Study cinematography techniques, analyze performances, learn from examples

### **Content Creators**
Find B-roll footage quickly, locate specific shots, review technical quality

### **Actors**
Review performance moments, find emotional scenes, track character arc

### **Directors**
Analyze shot composition, review camera work, study lighting setups

### **Video Editors**
Find specific footage fast, locate matching shots, build timelines efficiently

---

## 🎉 Get Started

```bash
# Clone repository
git clone https://github.com/yourusername/CINEAI.git
cd CINEAI

# Start backend
cd backend && pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key" > .env
uvicorn main:app --reload

# Start frontend (new terminal)
cd frontend && npm install && npm run dev

# Visit http://localhost:3000 and start analyzing! 🎬
```

---

**Built with ❤️ for filmmakers**
