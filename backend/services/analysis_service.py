import os
import json
import re
import time
import logging
from google import genai
from google.genai import types
import PIL.Image
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

load_dotenv()

from services.video_service import VideoService

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Service for analyzing video frames and generating descriptions.
    """
    
    ANALYSIS_OUTPUT_DIR = "analysis_output"
    STATUS_DIR = "analysis_status"
    
    # Simple, reliable rate limiting: 8 requests per minute with fixed delays
    BATCH_SIZE = 4  # Frames per request
    REQUEST_DELAY = 7  # Seconds between requests (60/7 ≈ 8.5 req/min, safely under 10)
    INITIAL_COOLDOWN = 20  # Initial wait to clear any previous quota usage
    
    def __init__(self):
        os.makedirs(self.ANALYSIS_OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.STATUS_DIR, exist_ok=True)
        self.video_service = VideoService()
    
    def get_output_file(self, video_id: str) -> str:
        """Get path to analysis output file."""
        return os.path.join(self.ANALYSIS_OUTPUT_DIR, f"{video_id}_analysis.json")
    
    def get_status_file(self, video_id: str) -> str:
        """Get path to status file."""
        return os.path.join(self.STATUS_DIR, f"{video_id}_status.json")
    
    def extract_json(self, text: str) -> Dict[str, Any]:
        """Clean markdown and extract JSON."""
        text = re.sub(r"```json", "", text)
        text = re.sub(r"```", "", text)
        return json.loads(text.strip())
    
    def extract_json_array(self, text: str) -> List[Dict[str, Any]]:
        """Clean markdown and extract JSON array."""
        text = re.sub(r"```json", "", text)
        text = re.sub(r"```", "", text)
        data = json.loads(text.strip())
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "frames" in data:
            return data["frames"]
        return [data]
    
    def normalize_list(self, items: List[Any], key: str) -> List[str]:
        """Normalize list items."""
        result = []
        for item in items:
            if isinstance(item, dict):
                value = item.get(key)
                if value:
                    result.append(str(value))
            elif isinstance(item, str):
                result.append(item)
        return result
    
    def json_to_embedding_text_dual(self, data: Dict[str, Any]) -> tuple:
        """
        Convert JSON to two RICH embedding-ready texts:
        1. Technical text (for Director role)
        2. Content text (for Actor role)
        """
        second = data.get('second', 0)
        
        # Extract technical info
        tech_info = data.get("technical_info", {})
        shot_type = tech_info.get("shot_type", "unknown")
        camera_angle = tech_info.get("camera_angle", "unknown")
        lighting = tech_info.get("lighting", "unknown")
        color_grading = tech_info.get("color_grading", "unknown")
        visual_mood = tech_info.get("visual_mood", "unknown")
        scene_type = tech_info.get("scene_type", "unknown")
        
        # Extract content info
        content_info = data.get("content_info", {})
        
        # Handle both old format (list) and new format (dict) for emotions
        emotions_data = content_info.get("emotions", {})
        if isinstance(emotions_data, dict):
            primary_emotion = emotions_data.get("primary", "neutral")
            secondary_emotions = emotions_data.get("secondary", [])
            emotion_intensity = emotions_data.get("intensity", "medium")
            emotion_context = emotions_data.get("context", "")
            emotions_str = f"{primary_emotion}"
            if secondary_emotions:
                emotions_str += f", {', '.join(secondary_emotions)}"
            emotions_str += f" (intensity: {emotion_intensity})"
        else:
            # Old format: list of emotion objects
            emotions_list = self.normalize_list(emotions_data, "type")
            emotions_str = ', '.join(emotions_list) if emotions_list else 'none'
        
        # Extract actions
        actions = content_info.get("actions", [])
        if isinstance(actions, list):
            if actions and isinstance(actions[0], dict):
                actions_str = ', '.join([a.get("type", "") for a in actions if isinstance(a, dict)])
            else:
                actions_str = ', '.join([str(a) for a in actions if a])
        else:
            actions_str = str(actions) if actions else "none"
        
        # Extract setting
        setting = content_info.get("setting", {})
        if isinstance(setting, dict):
            location = setting.get("location", "unknown")
            time_of_day = setting.get("time_of_day", "")
            weather = setting.get("weather", "")
            atmosphere = setting.get("atmosphere", "")
            setting_str = f"{location}"
            if time_of_day:
                setting_str += f" at {time_of_day}"
            if weather:
                setting_str += f", {weather} weather"
            if atmosphere:
                setting_str += f", {atmosphere} atmosphere"
        else:
            setting_str = str(setting) if setting else "unknown"
        
        # Extract other details
        interactions = content_info.get("interactions", "")
        mood = content_info.get("mood", "")
        character_count = content_info.get("character_count", 0)
        scene_summary = content_info.get("scene_summary", "").strip()
        
        # Characters
        characters = content_info.get("characters", [])
        char_descriptions = []
        if isinstance(characters, list):
            for char in characters:
                if isinstance(char, dict):
                    desc = char.get("description", "")
                    activity = char.get("activity", "")
                    body_lang = char.get("body_language", "")
                    char_info = desc
                    if activity:
                        char_info += f" {activity}"
                    if body_lang:
                        char_info += f" ({body_lang})"
                    if char_info:
                        char_descriptions.append(char_info)
        
        # Technical embedding text (for Director)
        technical_text = (
            f"Second: {second}\n"
            f"Shot Type: {shot_type}\n"
            f"Camera Angle: {camera_angle}\n"
            f"Lighting: {lighting}\n"
            f"Color Grading: {color_grading}\n"
            f"Visual Mood: {visual_mood}\n"
            f"Scene Type: {scene_type}\n"
            f"Summary: {scene_summary}"
        )
        
        # Content embedding text (for Actor) - RICH and DETAILED
        content_text = (
            f"Second: {second}\n"
            f"Setting: {setting_str}\n"
            f"Characters: {len(char_descriptions)} - {'; '.join(char_descriptions) if char_descriptions else 'none'}\n"
            f"Actions: {actions_str}\n"
            f"Emotions: {emotions_str}\n"
            f"Interactions: {interactions if interactions else 'none'}\n"
            f"Mood: {mood if mood else 'neutral'}\n"
            f"Atmosphere: {atmosphere if atmosphere else 'neutral'}\n"
            f"Summary: {scene_summary}"
        )
        
        return technical_text, content_text
    
    def describe_image(self, image_path: str, second: int, client: genai.Client) -> Dict[str, Any]:
        """
        Generate DETAILED description for a frame using Gemini with enhanced analysis.
        """
        prompt = f"""
Analyze this frame from second {second} with RICH DETAIL for intelligent video search.

TECHNICAL ANALYSIS (Director's View):
- Shot type: extreme wide shot, wide shot, medium shot, close-up, extreme close-up, two-shot, over-shoulder
- Camera angle: eye level, high angle, low angle, bird's eye, worm's eye, dutch angle
- Lighting: natural daylight, golden hour, artificial, high key, low key, backlit, dramatic, soft, hard
- Color grading: warm tones, cool tones, neutral, desaturated, vibrant, monochrome
- Visual mood: romantic, dramatic, tense, peaceful, energetic, melancholic, suspenseful
- Scene type: indoor, outdoor, beach, woods, city, rural, etc.

CONTENT ANALYSIS (Actor's View):
- Characters: count, descriptions, what they're wearing, body language, facial expressions
- Emotions: primary (happy, sad, romantic, angry, fearful, surprised, content, melancholic, loving, tense, peaceful)
- Emotion details: secondary emotions, intensity (low/medium/high), emotional context
- Actions: specific activities (walking slowly, running, fighting, embracing, talking, gazing, sitting, dancing, etc.)
- Interactions: how characters interact, relationships visible
- Setting details: location specifics (beach, forest, room type, etc.), time of day, weather, atmosphere
- Mood/Atmosphere: overall feeling (romantic, tense, peaceful, joyful, sad, mysterious, etc.)
- Story context: what seems to be happening narratively

Return ONLY valid JSON (no markdown):
{{
  "second": {second},
  "technical_info": {{
    "shot_type": "",
    "camera_angle": "",
    "lighting": "",
    "color_grading": "",
    "visual_mood": "",
    "scene_type": ""
  }},
  "content_info": {{
    "characters": [{{
      "description": "",
      "activity": "",
      "body_language": ""
    }}],
    "emotions": {{
      "primary": "",
      "secondary": [],
      "intensity": "",
      "context": ""
    }},
    "setting": {{
      "location": "",
      "time_of_day": "",
      "weather": "",
      "atmosphere": ""
    }},
    "actions": [],
    "interactions": "",
    "mood": "",
    "character_count": 0,
    "scene_summary": ""
  }}
}}

Be DETAILED and SPECIFIC. Capture subtle emotions and atmospheric details.
"""
        
        img = PIL.Image.open(image_path)
        
        # Retry logic for rate limiting (429 / Too Many Requests)
        max_retries = 8
        base_delay = 12  # Start with 12s, then 24s, 48s, ... (only when 429 occurs)
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[prompt, img],
                    config=types.GenerateContentConfig(temperature=0)
                )
                return self.extract_json(response.text)
                
            except Exception as e:
                error_str = str(e)
                is_rate_limit = (
                    "429" in error_str
                    or "Too Many Requests" in error_str
                    or "RESOURCE_EXHAUSTED" in error_str
                    or "quota" in error_str.lower()
                    or "rate" in error_str.lower()
                )
                if is_rate_limit:
                    if attempt < max_retries - 1:
                        retry_delay = base_delay * (2 ** attempt)
                        # Cap at 120s to avoid excessive wait
                        retry_delay = min(retry_delay, 120)
                        if "retryDelay" in error_str or "RetryInfo" in error_str:
                            delay_match = re.search(r'retryDelay[:\'"]?\s*[\'"]?(\d+)', error_str, re.IGNORECASE)
                            if delay_match:
                                retry_delay = max(retry_delay, int(delay_match.group(1)) + 10)
                        logger.warning(
                            f"⏳ [ANALYSIS-SERVICE] Rate limited (attempt {attempt + 1}/{max_retries}). "
                            f"Waiting {retry_delay}s before retry..."
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} attempts.")
                else:
                    raise
        
        raise Exception("Failed to get response after all retries")
    
    # Simple, reliable batch processing with fixed delay between requests
    def describe_image_batch(
        self, batch: List[Tuple[str, int]], client: genai.Client
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple frames in a single API request with ENHANCED DETAIL.
        batch: [(image_path, second), ...]
        """
        if not batch:
            return []
        
        seconds_list = [sec for _, sec in batch]
        prompt = f"""You will receive {len(batch)} frames from a video. Frame order and their video seconds:
{chr(10).join(f"Image {i+1}: second {sec}" for i, sec in enumerate(seconds_list))}

For EACH frame, provide DETAILED technical cinematography AND rich content analysis.
Return a JSON array of exactly {len(batch)} objects, in the same order as the images.

ANALYZE WITH DETAIL:
- Technical: shot type, camera angle, lighting quality, color grading, visual mood
- Content: character descriptions, specific actions, detailed emotions, setting, atmosphere, interactions
- Emotions: Be specific (romantic, melancholic, joyful, tense, peaceful, not just "happy/sad")
- Actions: Be specific (walking slowly, running quickly, embracing tenderly, not just "moving")
- Setting: Detailed location (beach at sunset, dark forest, cozy room, not just "outdoor")

Each object schema:
{{
  "second": <number>,
  "technical_info": {{
    "shot_type": "",
    "camera_angle": "",
    "lighting": "",
    "color_grading": "",
    "visual_mood": "",
    "scene_type": ""
  }},
  "content_info": {{
    "characters": [{{ "description": "", "activity": "", "body_language": "" }}],
    "emotions": {{
      "primary": "",
      "secondary": [],
      "intensity": "",
      "context": ""
    }},
    "setting": {{
      "location": "",
      "time_of_day": "",
      "weather": "",
      "atmosphere": ""
    }},
    "actions": [],
    "interactions": "",
    "mood": "",
    "character_count": 0,
    "scene_summary": ""
  }}
}}

Return ONLY the JSON array. No markdown, no backticks. Be DETAILED and capture SUBTLE nuances."""
        
        contents: List[Any] = [prompt]
        for path, _ in batch:
            contents.append(PIL.Image.open(path))
        
        max_retries = 5
        base_delay = 20
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0)
                )
                items = self.extract_json_array(response.text)
                # Ensure we have one result per image; match by index to seconds_list
                out = []
                for i, sec in enumerate(seconds_list):
                    if i < len(items):
                        obj = dict(items[i])
                        obj["second"] = sec
                        out.append(obj)
                    else:
                        out.append({
                            "second": sec,
                            "technical_info": {},
                            "content_info": {"objects": [], "actions": [], "emotions": [], "character_count": 0, "scene_summary": ""}
                        })
                return out
            except Exception as e:
                error_str = str(e)
                is_rate_limit = (
                    "429" in error_str or "Too Many Requests" in error_str
                    or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()
                    or "rate" in error_str.lower()
                )
                if is_rate_limit and attempt < max_retries - 1:
                    retry_delay = min(base_delay * (2 ** attempt), 120)
                    logger.warning(
                        f"⚠️  [ANALYSIS-SERVICE] Rate limited on batch (attempt {attempt + 1}/{max_retries}). "
                        f"Waiting {retry_delay}s before retry..."
                    )
                    time.sleep(retry_delay)
                    continue
                raise
        return []
    
    def analyze_frames(self, video_id: str, frames_dir: str) -> Dict[str, Any]:
        """
        Analyze all frames in a directory and generate descriptions.
        
        Returns:
            Analysis output dictionary
        """
        # Ensure output directory exists
        os.makedirs(self.ANALYSIS_OUTPUT_DIR, exist_ok=True)
        
        logger.info(f"🤖 [ANALYSIS-SERVICE] Starting frame analysis for video_id: {video_id}")
        logger.info(f"📁 [ANALYSIS-SERVICE] Frames directory: {frames_dir}")
        
        # Initialize Gemini client
        logger.info(f"🔑 [ANALYSIS-SERVICE] Initializing Gemini API client...")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error(f"❌ [ANALYSIS-SERVICE] GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        api_key = api_key.strip()
        client = genai.Client(api_key=api_key)
        logger.info(f"✅ [ANALYSIS-SERVICE] Gemini client initialized")
        
        results = []
        # Simple rate limiting: 7 seconds between requests = ~8.5 req/min (safely under 10)
        frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])
        total_frames = len(frame_files)
        batch_size = self.BATCH_SIZE
        num_batches = (total_frames + batch_size - 1) // batch_size
        logger.info(
            f"⏱️  [ANALYSIS-SERVICE] Simple rate limiting: {batch_size} frames/request, "
            f"{self.REQUEST_DELAY}s delay between requests"
        )
        logger.info(f"📊 [ANALYSIS-SERVICE] Total frames: {total_frames} in {num_batches} batch(es)")
        logger.info(f"🔒 [ANALYSIS-SERVICE] Estimated time: ~{num_batches * self.REQUEST_DELAY / 60:.1f} minutes")
        
        # Initial cooldown: wait for any previous quota usage to clear
        logger.info(f"⏳ [ANALYSIS-SERVICE] Initial {self.INITIAL_COOLDOWN}-second cooldown to clear previous quota...")
        time.sleep(self.INITIAL_COOLDOWN)
        
        start_time = time.time()
        
        for batch_idx in range(num_batches):
            start_i = batch_idx * batch_size
            chunk = frame_files[start_i : start_i + batch_size]
            batch_items: List[Tuple[str, int]] = []
            for f in chunk:
                sec = int(f.split("_")[1].split(".")[0])
                batch_items.append((os.path.join(frames_dir, f), sec))
            
            try:
                logger.info(
                    f"🖼️  [ANALYSIS-SERVICE] Batch {batch_idx + 1}/{num_batches}: "
                    f"frames {start_i + 1}-{start_i + len(batch_items)} (seconds {[b[1] for b in batch_items]})"
                )
                frame_results = self.describe_image_batch(batch_items, client)
                
                for llava_json in frame_results:
                    second = llava_json.get("second", 0)
                    technical_text, content_text = self.json_to_embedding_text_dual(llava_json)
                    results.append({
                        "second": second,
                        "llava_json": llava_json,
                        "embedding_text_technical": technical_text,
                        "embedding_text_content": content_text
                    })
                
                current_progress = len(results) / total_frames
                self.update_progress(video_id, len(results), total_frames, "analyzing_frames")
                self.update_overall_progress(video_id, "analyzing_frames", current_progress)
                
                elapsed = time.time() - start_time
                done = len(results)
                remaining = total_frames - done
                est_remaining = (elapsed / done * remaining) if done else 0
                logger.info(
                    f"✅ [ANALYSIS-SERVICE] Batch {batch_idx + 1}/{num_batches} done. "
                    f"Progress: {done}/{total_frames} ({current_progress*100:.1f}%). "
                    f"Elapsed: {elapsed:.1f}s | Est. remaining: {est_remaining/60:.1f}min"
                )
                
                # Simple delay between requests (skip on last batch)
                if batch_idx < num_batches - 1:
                    logger.info(f"⏳ [ANALYSIS-SERVICE] Waiting {self.REQUEST_DELAY}s before next batch...")
                    time.sleep(self.REQUEST_DELAY)
                    
            except Exception as e:
                logger.error(f"❌ [ANALYSIS-SERVICE] Batch {batch_idx + 1} failed: {str(e)}", exc_info=True)
                # Wait before continuing to next batch even on failure
                time.sleep(self.REQUEST_DELAY)
        
        total_time = time.time() - start_time
        logger.info(f"✅ [ANALYSIS-SERVICE] Frame analysis completed!")
        logger.info(f"📊 [ANALYSIS-SERVICE] Total frames analyzed: {len(results)}/{total_frames}")
        logger.info(f"⏱️  [ANALYSIS-SERVICE] Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        logger.info(f"⏱️  [ANALYSIS-SERVICE] Average time per frame: {total_time/len(results) if results else 0:.1f} seconds")
        
        # Save analysis output
        output = {
            "video_id": video_id,
            "frames": results
        }
        
        output_file = self.get_output_file(video_id)
        logger.info(f"💾 [ANALYSIS-SERVICE] Saving analysis output to: {output_file}")
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        logger.info(f"✅ [ANALYSIS-SERVICE] Analysis output saved successfully")
        
        return output
    
    def is_analyzed(self, video_id: str) -> bool:
        """Check if video has been analyzed."""
        return os.path.exists(self.get_output_file(video_id))
    
    def update_status(self, video_id: str, status: str, message: str):
        """Update analysis status."""
        # Ensure directory exists
        os.makedirs(self.STATUS_DIR, exist_ok=True)
        
        status_file = self.get_status_file(video_id)
        status_data = {
            "video_id": video_id,
            "status": status,
            "message": message,
            "timestamp": time.time()
        }
        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)
    
    def update_progress(self, video_id: str, current: int, total: int, stage: str = "analyzing_frames"):
        """Update analysis progress."""
        # Ensure directory exists
        os.makedirs(self.STATUS_DIR, exist_ok=True)
        
        status_file = self.get_status_file(video_id)
        progress = {
            "current": current,
            "total": total,
            "percentage": int((current / total) * 100) if total > 0 else 0,
            "stage": stage
        }
        
        status_data = {
            "video_id": video_id,
            "status": stage,
            "message": f"Processing frame {current}/{total}",
            "progress": progress,
            "timestamp": time.time()
        }
        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)
    
    def update_overall_progress(self, video_id: str, stage: str, stage_progress: float, total_stages: int = 3):
        """
        Update overall progress across all stages.
        stage_progress: 0.0 to 1.0 (progress within current stage)
        total_stages: Total number of stages (default: 3)
        """
        # Ensure directory exists
        os.makedirs(self.STATUS_DIR, exist_ok=True)
        
        status_file = self.get_status_file(video_id)
        
        # Stage weights (can be adjusted based on actual time taken)
        stage_weights = {
            "generating_frames": 0.1,      # 10% of total
            "analyzing_frames": 0.7,      # 70% of total (most time-consuming)
            "building_vector_db": 0.2      # 20% of total
        }
        
        # Calculate stage index
        stage_order = ["generating_frames", "analyzing_frames", "building_vector_db"]
        stage_index = stage_order.index(stage) if stage in stage_order else 0
        
        # Calculate overall percentage
        overall_percentage = 0.0
        for i, s in enumerate(stage_order):
            if i < stage_index:
                overall_percentage += stage_weights.get(s, 0)
            elif i == stage_index:
                overall_percentage += stage_weights.get(s, 0) * stage_progress
        
        overall_percentage = min(100, int(overall_percentage * 100))
        
        # Get existing status data
        if os.path.exists(status_file):
            with open(status_file, "r") as f:
                status_data = json.load(f)
        else:
            status_data = {"video_id": video_id}
        
        # Update with overall progress
        status_data.update({
            "status": stage,
            "overall_progress": {
                "percentage": overall_percentage,
                "stage": stage,
                "stage_progress": stage_progress
            },
            "timestamp": time.time()
        })
        
        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)
    
    def get_status(self, video_id: str) -> Dict[str, Any]:
        """Get current analysis status."""
        status_file = self.get_status_file(video_id)
        
        if not os.path.exists(status_file):
            return {
                "status": "not_started",
                "message": "Analysis not started"
            }
        
        with open(status_file, "r") as f:
            status_data = json.load(f)
        
        return status_data
