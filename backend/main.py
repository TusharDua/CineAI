from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv

from services.video_service import VideoService
from services.analysis_service import AnalysisService
from services.vector_db_service import VectorDBService
from services.retriever_service import RetrieverService
from services.scene_detection_service import SceneDetectionService

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CINEAI Video Analysis API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API router (prefix /api for same-origin frontend)
api = APIRouter()

# Mount uploads directory for serving video files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Initialize services
video_service = VideoService()
analysis_service = AnalysisService()
vector_db_service = VectorDBService()
retriever_service = RetrieverService()
scene_detection_service = SceneDetectionService()


# Request/Response models
class ChatRequest(BaseModel):
    query: str
    video_id: str
    role: Optional[str] = "actor"  # "actor", "director", or "producer"
    top_k: Optional[int] = 5


class ChatResponse(BaseModel):
    results: List[Dict[str, Any]]
    query: str
    video_id: str
    role: str
    answer: Optional[str] = None  # Natural language answer from LLM
    found_count: Optional[int] = None  # Number of truly relevant moments


class AnalysisStatusResponse(BaseModel):
    video_id: str
    status: str
    message: str
    progress: Optional[Dict[str, Any]] = None
    overall_progress: Optional[Dict[str, Any]] = None


# Endpoints (under /api)
@api.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file and get a video_id for processing.
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Supported formats: mp4, avi, mov, mkv, webm"
            )
        
        # Generate unique video ID
        video_id = str(uuid.uuid4())
        
        # Save uploaded video
        video_path = await video_service.save_video(file, video_id)
        
        return {
            "video_id": video_id,
            "filename": file.filename,
            "message": "Video uploaded successfully",
            "next_step": f"Call /analyze-video/{video_id} to start analysis"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/analyze-video/{video_id}")
async def analyze_video(video_id: str, background_tasks: BackgroundTasks):
    """
    Analyze video: generate frames, descriptions, embeddings, and build vector DB.
    This runs as a background task.
    """
    logger.info(f"🔍 [ANALYZE-VIDEO] Received request for video_id: {video_id}")
    try:
        # Check if video exists
        logger.info(f"📹 [ANALYZE-VIDEO] Checking if video exists: {video_id}")
        if not video_service.video_exists(video_id):
            logger.error(f"❌ [ANALYZE-VIDEO] Video not found: {video_id}")
            raise HTTPException(status_code=404, detail="Video not found")
        logger.info(f"✅ [ANALYZE-VIDEO] Video found: {video_id}")
        
        # Check if already analyzed
        logger.info(f"🔍 [ANALYZE-VIDEO] Checking if video already analyzed: {video_id}")
        if analysis_service.is_analyzed(video_id):
            logger.info(f"ℹ️  [ANALYZE-VIDEO] Video already analyzed: {video_id}")
            return {
                "video_id": video_id,
                "status": "completed",
                "message": "Video already analyzed",
                "vector_db_ready": vector_db_service.vector_db_exists(video_id)
            }
        
        # Start analysis in background
        logger.info(f"🚀 [ANALYZE-VIDEO] Starting background analysis task for: {video_id}")
        background_tasks.add_task(
            process_video_analysis,
            video_id
        )
        logger.info(f"✅ [ANALYZE-VIDEO] Background task scheduled for: {video_id}")
        
        return {
            "video_id": video_id,
            "status": "processing",
            "message": "Video analysis started. Use /status/{video_id} to check progress."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [ANALYZE-VIDEO] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/status/{video_id}")
async def get_analysis_status(video_id: str):
    """
    Get the analysis status for a video.
    """
    try:
        if not video_service.video_exists(video_id):
            raise HTTPException(status_code=404, detail="Video not found")
        
        status_info = analysis_service.get_status(video_id)
        
        return AnalysisStatusResponse(
            video_id=video_id,
            status=status_info["status"],
            message=status_info["message"],
            progress=status_info.get("progress"),
            overall_progress=status_info.get("overall_progress")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Query the vector database for a specific video based on role with intelligent LLM-generated answers.
    Role: "actor" for content search, "director" for technical/cinematography search, "producer" for production/commercial search.
    """
    try:
        # Validate role
        if request.role not in ["actor", "director", "producer"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid role. Must be 'actor', 'director', or 'producer'"
            )
        
        # Set default top_k based on role
        top_k = request.top_k
        if request.role == "producer" and request.top_k == 5:
            top_k = 15  # Producer mode shows more results by default
        
        # Validate video_id
        if not video_service.video_exists(request.video_id):
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check if vector DB exists
        if not vector_db_service.vector_db_exists(request.video_id):
            raise HTTPException(
                status_code=400,
                detail="Vector database not found. Please analyze the video first."
            )
        
        # Perform search with intelligent answer generation
        answer_data = retriever_service.search_with_answer(
            video_id=request.video_id,
            query=request.query,
            role=request.role,
            top_k=top_k
        )
        
        return ChatResponse(
            query=request.query,
            video_id=request.video_id,
            role=request.role,
            results=answer_data["relevant_moments"],
            answer=answer_data["answer"],
            found_count=answer_data["found_count"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/videos")
async def list_videos():
    """
    List all uploaded videos with their analysis status.
    """
    try:
        videos = video_service.list_videos()
        
        # Enhance with analysis status
        enhanced_videos = []
        for video in videos:
            video_id = video["video_id"]
            
            # Check analysis status
            is_analyzed = analysis_service.is_analyzed(video_id)
            vector_db_exists = vector_db_service.vector_db_exists(video_id)
            
            # Get detailed status if available
            status_info = analysis_service.get_status(video_id)
            
            enhanced_videos.append({
                **video,
                "is_analyzed": is_analyzed,
                "vector_db_ready": vector_db_exists,
                "status": status_info.get("status", "not_started"),
                "can_query": vector_db_exists  # Can query if vector DB exists
            })
        
        return {"videos": enhanced_videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mount API under /api
app.include_router(api, prefix="/api")

# Serve UI at root: use backend/dist (Docker) or frontend/dist (local dev)
_BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(_BASE, "dist")
if not os.path.isdir(DIST):
    DIST = os.path.join(os.path.dirname(_BASE), "frontend", "dist")

if os.path.isdir(DIST):
    assets_dir = os.path.join(DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(DIST, "index.html"))

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("uploads/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(os.path.join(DIST, "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "CINEAI API", "docs": "/docs", "api": "/api"}


# Background task function
async def process_video_analysis(video_id: str):
    """
    Complete video analysis pipeline:
    0. Detect scenes
    1. Generate frames
    2. Generate frame descriptions
    3. Generate embeddings
    4. Build vector database
    """
    start_time = datetime.now()
    logger.info(f"🎬 [PROCESS-VIDEO] ========================================")
    logger.info(f"🎬 [PROCESS-VIDEO] Starting analysis for video_id: {video_id}")
    logger.info(f"🎬 [PROCESS-VIDEO] Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🎬 [PROCESS-VIDEO] ========================================")
    
    try:
        # Step 0: Detect scenes
        logger.info(f"🎬 [STEP-0] Detecting scenes in video: {video_id}")
        video_path = video_service.get_video_path(video_id)
        scenes = scene_detection_service.detect_scenes(video_path)
        logger.info(f"✅ [STEP-0] Scene detection completed! Detected {len(scenes)} scenes")
        
        # Step 1: Generate frames
        logger.info(f"📹 [STEP-1] Generating frames from video: {video_id}")
        analysis_service.update_status(video_id, "generating_frames", "Generating video frames...")
        analysis_service.update_overall_progress(video_id, "generating_frames", 0.0)
        
        logger.info(f"📹 [STEP-1] Calling video_service.generate_frames()...")
        frames_dir = video_service.generate_frames(video_id)
        logger.info(f"✅ [STEP-1] Frames generated successfully!")
        logger.info(f"📁 [STEP-1] Frames directory: {frames_dir}")
        
        # Count generated frames
        frame_count = len([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])
        logger.info(f"📊 [STEP-1] Total frames generated: {frame_count}")
        
        analysis_service.update_overall_progress(video_id, "generating_frames", 1.0)
        logger.info(f"✅ [STEP-1] Frame generation completed!")
        
        # Step 2: Generate frame descriptions
        logger.info(f"🤖 [STEP-2] Starting frame analysis with Gemini AI...")
        logger.info(f"🤖 [STEP-2] Total frames to analyze: {frame_count}")
        analysis_service.update_status(video_id, "analyzing_frames", "Analyzing frames with Gemini...")
        analysis_service.update_overall_progress(video_id, "analyzing_frames", 0.0)
        
        logger.info(f"🤖 [STEP-2] Calling analysis_service.analyze_frames()...")
        analysis_output = analysis_service.analyze_frames(video_id, frames_dir)
        logger.info(f"✅ [STEP-2] Frame analysis completed!")
        logger.info(f"📊 [STEP-2] Frames analyzed: {len(analysis_output.get('frames', []))}")
        
        # Step 2.5: Assign scenes to frames
        logger.info(f"🔗 [STEP-2.5] Assigning scenes to frames...")
        frames = analysis_output.get("frames", [])
        frames_with_scenes = scene_detection_service.assign_frames_to_scenes(frames, scenes)
        analysis_output["frames"] = frames_with_scenes
        logger.info(f"✅ [STEP-2.5] Scenes assigned to frames!")
        
        analysis_service.update_overall_progress(video_id, "analyzing_frames", 1.0)
        logger.info(f"✅ [STEP-2] Frame analysis stage completed!")
        
        # Step 3: Generate embeddings and build vector DB
        logger.info(f"💾 [STEP-3] Starting vector database construction...")
        logger.info(f"💾 [STEP-3] Frames to process: {len(analysis_output.get('frames', []))}")
        analysis_service.update_status(video_id, "building_vector_db", "Building vector database...")
        analysis_service.update_overall_progress(video_id, "building_vector_db", 0.0)
        
        logger.info(f"💾 [STEP-3] Calling vector_db_service.build_vector_database()...")
        vector_db_service.build_vector_database(video_id, analysis_output, analysis_service)
        logger.info(f"✅ [STEP-3] Vector database built successfully!")
        
        analysis_service.update_overall_progress(video_id, "building_vector_db", 1.0)
        logger.info(f"✅ [STEP-3] Vector database stage completed!")
        
        # Mark as completed
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"🎉 [PROCESS-VIDEO] ========================================")
        logger.info(f"🎉 [PROCESS-VIDEO] Analysis completed successfully!")
        logger.info(f"🎉 [PROCESS-VIDEO] Video ID: {video_id}")
        logger.info(f"🎉 [PROCESS-VIDEO] Total duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        logger.info(f"🎉 [PROCESS-VIDEO] End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🎉 [PROCESS-VIDEO] ========================================")
        
        analysis_service.update_status(video_id, "completed", "Analysis completed successfully!")
        analysis_service.update_overall_progress(video_id, "completed", 1.0)
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.error(f"❌ [PROCESS-VIDEO] ========================================")
        logger.error(f"❌ [PROCESS-VIDEO] Analysis FAILED for video_id: {video_id}")
        logger.error(f"❌ [PROCESS-VIDEO] Error: {str(e)}")
        logger.error(f"❌ [PROCESS-VIDEO] Duration before failure: {duration:.2f} seconds")
        logger.error(f"❌ [PROCESS-VIDEO] ========================================", exc_info=True)
        
        analysis_service.update_status(
            video_id,
            "failed",
            f"Analysis failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
