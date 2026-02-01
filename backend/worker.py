"""
Worker script for processing video analysis jobs.
This runs as a Cloud Run Job and handles the long-running video processing.
"""
import os
import sys
import json
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from services.video_service import VideoService
from services.analysis_service import AnalysisService
from services.vector_db_service import VectorDBService

def process_video(video_id: str):
    """
    Process a video: extract frames, analyze, build vector DB.
    This can take 20+ minutes.
    """
    try:
        logger.info(f"🚀 Starting video processing for video_id: {video_id}")
        
        video_service = VideoService()
        analysis_service = AnalysisService()
        vector_db_service = VectorDBService()
        
        # Update status
        analysis_service.update_status(video_id, "processing", "Starting video analysis...")
        
        # Step 1: Extract frames
        logger.info(f"📹 Extracting frames for video_id: {video_id}")
        analysis_service.update_status(video_id, "extracting_frames", "Extracting frames from video...")
        
        video_path = video_service.get_video_path(video_id)
        frames_dir = video_service.get_frames_dir(video_id)
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        video_service.extract_frames(video_id)
        logger.info(f"✅ Frames extracted to: {frames_dir}")
        
        # Step 2: Analyze frames
        logger.info(f"🤖 Analyzing frames for video_id: {video_id}")
        analysis_service.update_status(video_id, "analyzing_frames", "Analyzing frames with AI...")
        
        analysis_output = analysis_service.analyze_frames(video_id, frames_dir)
        logger.info(f"✅ Analysis completed. Total frames analyzed: {len(analysis_output.get('frames', []))}")
        
        # Step 3: Build vector database
        logger.info(f"💾 Building vector database for video_id: {video_id}")
        analysis_service.update_status(video_id, "building_vector_db", "Building vector database...")
        
        vector_db_service.build_vector_database(video_id, analysis_output, analysis_service)
        logger.info(f"✅ Vector database built successfully")
        
        # Update final status
        analysis_service.update_status(video_id, "completed", "Video analysis completed successfully!")
        logger.info(f"🎉 Video processing completed for video_id: {video_id}")
        
        return {
            "status": "success",
            "video_id": video_id,
            "frames_analyzed": len(analysis_output.get('frames', []))
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing video {video_id}: {str(e)}", exc_info=True)
        analysis_service.update_status(video_id, "failed", f"Error: {str(e)}")
        return {
            "status": "error",
            "video_id": video_id,
            "error": str(e)
        }

def main():
    """
    Main entry point for the worker.
    Expects VIDEO_ID environment variable.
    """
    video_id = os.getenv("VIDEO_ID")
    
    if not video_id:
        logger.error("❌ VIDEO_ID environment variable not set")
        sys.exit(1)
    
    logger.info(f"🔧 Worker started for video_id: {video_id}")
    
    result = process_video(video_id)
    
    if result["status"] == "error":
        logger.error(f"❌ Worker failed: {result['error']}")
        sys.exit(1)
    else:
        logger.info(f"✅ Worker completed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()
