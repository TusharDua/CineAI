import os
import ffmpeg
import logging
from typing import List, Dict
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class VideoService:
    """
    Service for handling video uploads and frame generation.
    """
    
    UPLOAD_DIR = "uploads"
    FRAMES_BASE_DIR = "video_frames"
    
    def __init__(self):
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.FRAMES_BASE_DIR, exist_ok=True)
    
    def get_video_path(self, video_id: str, extension: str = None) -> str:
        """
        Get the path to a video file. If extension is not provided, 
        searches for common video extensions.
        """
        if extension:
            # Add dot if not present
            if not extension.startswith('.'):
                extension = f".{extension}"
            return os.path.join(self.UPLOAD_DIR, f"{video_id}{extension}")
        
        # Try common extensions
        for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
            video_path = os.path.join(self.UPLOAD_DIR, f"{video_id}{ext}")
            if os.path.exists(video_path):
                return video_path
        
        raise FileNotFoundError(f"Video file not found for video_id: {video_id}")
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return filename.rsplit('.', 1)[-1].lower()
    
    def get_frames_dir(self, video_id: str) -> str:
        """Get the frames directory for a video."""
        return os.path.join(self.FRAMES_BASE_DIR, video_id)
    
    async def save_video(self, file: UploadFile, video_id: str) -> str:
        """
        Save uploaded video file.
        
        Args:
            file: Uploaded file
            video_id: Unique video identifier
            
        Returns:
            Path to saved video file
        """
        extension = self._get_file_extension(file.filename)
        video_path = self.get_video_path(video_id, extension)
        
        # Save file
        with open(video_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return video_path
    
    def video_exists(self, video_id: str) -> bool:
        """Check if a video exists (tries common extensions)."""
        extensions = ['mp4', 'avi', 'mov', 'mkv', 'webm']
        for ext in extensions:
            if os.path.exists(self.get_video_path(video_id, ext)):
                return True
        return False
    
    def generate_frames(self, video_id: str, fps: int = 1) -> str:
        """
        Generate frames from video (1 frame per second).
        
        Args:
            video_id: Unique video identifier
            fps: Frames per second (default: 1)
            
        Returns:
            Path to frames directory
        """
        logger.info(f"📹 [VIDEO-SERVICE] Starting frame generation for video_id: {video_id}")
        logger.info(f"📹 [VIDEO-SERVICE] FPS setting: {fps}")
        
        # Find video file with any extension
        extensions = ['mp4', 'avi', 'mov', 'mkv', 'webm']
        video_path = None
        logger.info(f"🔍 [VIDEO-SERVICE] Searching for video file with extensions: {extensions}")
        
        for ext in extensions:
            path = self.get_video_path(video_id, ext)
            logger.debug(f"🔍 [VIDEO-SERVICE] Checking path: {path}")
            if os.path.exists(path):
                video_path = path
                logger.info(f"✅ [VIDEO-SERVICE] Found video file: {video_path}")
                file_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
                logger.info(f"📊 [VIDEO-SERVICE] Video file size: {file_size:.2f} MB")
                break
        
        if not video_path:
            logger.error(f"❌ [VIDEO-SERVICE] Video not found for video_id: {video_id}")
            raise FileNotFoundError(f"Video not found for video_id: {video_id}")
        
        frames_dir = self.get_frames_dir(video_id)
        logger.info(f"📁 [VIDEO-SERVICE] Frames directory: {frames_dir}")
        
        os.makedirs(frames_dir, exist_ok=True)
        logger.info(f"📁 [VIDEO-SERVICE] Created frames directory (if needed)")
        
        try:
            logger.info(f"⚙️  [VIDEO-SERVICE] Running FFmpeg to extract frames...")
            logger.info(f"⚙️  [VIDEO-SERVICE] Input: {video_path}")
            logger.info(f"⚙️  [VIDEO-SERVICE] Output pattern: {os.path.join(frames_dir, 'frame_%05d.jpg')}")
            
            (
                ffmpeg
                .input(video_path)
                .filter("fps", fps=fps)
                .output(
                    os.path.join(frames_dir, "frame_%05d.jpg"),
                    start_number=0
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Count generated frames
            frame_files = [f for f in os.listdir(frames_dir) if f.endswith(".jpg")]
            logger.info(f"✅ [VIDEO-SERVICE] FFmpeg completed successfully!")
            logger.info(f"📊 [VIDEO-SERVICE] Total frames generated: {len(frame_files)}")
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"❌ [VIDEO-SERVICE] FFmpeg failed: {error_msg}")
            raise Exception(f"FFmpeg failed: {error_msg}")
        
        logger.info(f"✅ [VIDEO-SERVICE] Frame generation completed for video_id: {video_id}")
        return frames_dir
    
    def list_videos(self) -> List[Dict]:
        """List all uploaded videos."""
        videos = []
        if not os.path.exists(self.UPLOAD_DIR):
            return videos
        
        for filename in os.listdir(self.UPLOAD_DIR):
            if filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                video_id = filename.rsplit('.', 1)[0]
                video_path = os.path.join(self.UPLOAD_DIR, filename)
                size = os.path.getsize(video_path)
                videos.append({
                    "video_id": video_id,
                    "filename": filename,
                    "size": size
                })
        
        return videos
