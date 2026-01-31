import os
import logging
from typing import List, Dict
from scenedetect import detect, ContentDetector

logger = logging.getLogger(__name__)


class SceneDetectionService:
    """
    Service for detecting scene boundaries in videos.
    Groups similar consecutive frames into scenes.
    """
    
    def detect_scenes(self, video_path: str, threshold: float = 27.0) -> List[Dict]:
        """
        Detect scene boundaries in a video.
        
        Args:
            video_path: Path to video file
            threshold: Scene detection sensitivity (lower = more scenes)
            
        Returns:
            List of scenes with start/end frame numbers
        """
        logger.info(f"🎬 [SCENE-DETECTION] Starting scene detection for: {video_path}")
        logger.info(f"🎬 [SCENE-DETECTION] Threshold: {threshold}")
        
        try:
            # Detect scenes using ContentDetector
            scene_list = detect(video_path, ContentDetector(threshold=threshold))
            
            logger.info(f"✅ [SCENE-DETECTION] Detected {len(scene_list)} scenes")
            
            # Convert to our format
            scenes = []
            for idx, (start_time, end_time) in enumerate(scene_list):
                scene = {
                    "scene_id": f"scene_{idx:03d}",
                    "start_second": int(start_time.get_seconds()),
                    "end_second": int(end_time.get_seconds()),
                    "start_frame": start_time.get_frames(),
                    "end_frame": end_time.get_frames()
                }
                scenes.append(scene)
                logger.debug(f"  Scene {idx}: {scene['start_second']}s - {scene['end_second']}s")
            
            return scenes
            
        except Exception as e:
            logger.error(f"❌ [SCENE-DETECTION] Failed: {str(e)}", exc_info=True)
            # Return single scene if detection fails
            return [{
                "scene_id": "scene_000",
                "start_second": 0,
                "end_second": 9999,
                "start_frame": 0,
                "end_frame": 9999
            }]
    
    def assign_frames_to_scenes(self, frames: List[Dict], scenes: List[Dict]) -> List[Dict]:
        """
        Assign scene_id to each frame based on detected scenes.
        
        Args:
            frames: List of frame analysis results
            scenes: List of detected scenes
            
        Returns:
            Frames with scene_id added
        """
        logger.info(f"🔗 [SCENE-DETECTION] Assigning frames to scenes...")
        logger.info(f"📊 [SCENE-DETECTION] Total frames: {len(frames)}, Total scenes: {len(scenes)}")
        
        for frame in frames:
            second = frame.get("second", 0)
            
            # Find which scene this frame belongs to
            scene_id = "scene_000"  # default
            for scene in scenes:
                if scene["start_second"] <= second <= scene["end_second"]:
                    scene_id = scene["scene_id"]
                    break
            
            frame["scene_id"] = scene_id
        
        logger.info(f"✅ [SCENE-DETECTION] Frames assigned to scenes")
        return frames
