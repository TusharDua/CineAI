import os
import json
import numpy as np
import faiss
import logging
import time
from google import genai
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from services.video_service import VideoService

logger = logging.getLogger(__name__)


class VectorDBService:
    """
    Service for building and managing vector databases.
    """
    
    VECTOR_DB_DIR = "vector_databases"
    EMBEDDING_MODEL = "models/gemini-embedding-001"
    
    def __init__(self):
        os.makedirs(self.VECTOR_DB_DIR, exist_ok=True)
        self.video_service = VideoService()
    
    def get_vector_db_file(self, video_id: str, role: str = "content") -> str:
        """Get path to vector database index file for specific role."""
        return os.path.join(self.VECTOR_DB_DIR, f"{video_id}_{role}.index")
    
    def get_metadata_file(self, video_id: str) -> str:
        """Get path to metadata file (shared for both roles)."""
        return os.path.join(self.VECTOR_DB_DIR, f"{video_id}_metadata.json")
    
    def get_embedding(self, text: str, client: genai.Client) -> List[float]:
        """Generate embedding for text."""
        try:
            response = client.models.embed_content(
                model=self.EMBEDDING_MODEL,
                contents=text
            )
            if hasattr(response, 'embeddings') and response.embeddings:
                embedding = response.embeddings[0]
                if hasattr(embedding, 'values'):
                    return list(embedding.values)
                elif isinstance(embedding, list):
                    return list(embedding)
                else:
                    return list(embedding)
            else:
                raise ValueError("No embeddings in response")
        except Exception as e:
            raise Exception(f"Error generating embedding: {e}")
    
    def build_vector_database(self, video_id: str, analysis_output: Dict[str, Any], analysis_service=None):
        """
        Build dual FAISS vector databases (technical + content) from analysis output.
        
        Args:
            video_id: Unique video identifier
            analysis_output: Analysis output dictionary with frames
            analysis_service: Optional AnalysisService instance for progress updates
        """
        logger.info(f"💾 [VECTOR-DB-SERVICE] Starting DUAL vector database construction for video_id: {video_id}")
        
        frames = analysis_output.get("frames", [])
        if not frames:
            logger.error(f"❌ [VECTOR-DB-SERVICE] No frames found in analysis output")
            raise ValueError("No frames found in analysis output")
        
        logger.info(f"📊 [VECTOR-DB-SERVICE] Total frames to process: {len(frames)}")
        
        # Initialize Gemini client
        logger.info(f"🔑 [VECTOR-DB-SERVICE] Initializing Gemini API client for embeddings...")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error(f"❌ [VECTOR-DB-SERVICE] GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        api_key = api_key.strip()
        client = genai.Client(api_key=api_key)
        logger.info(f"✅ [VECTOR-DB-SERVICE] Gemini client initialized")
        
        # Generate dual embeddings
        technical_embeddings = []
        content_embeddings = []
        metadata = []
        frames_dir = self.video_service.get_frames_dir(video_id)
        total_frames = len(frames)
        
        logger.info(f"🔄 [VECTOR-DB-SERVICE] Starting DUAL embedding generation (technical + content)...")
        start_time = time.time()
        
        for idx, frame in enumerate(frames, 1):
            second = frame.get("second", idx - 1)
            scene_id = frame.get("scene_id", "scene_000")
            embedding_text_technical = frame.get("embedding_text_technical", "")
            embedding_text_content = frame.get("embedding_text_content", "")
            llava_json = frame.get("llava_json", {})
            
            if not embedding_text_technical or not embedding_text_content:
                logger.warning(f"⚠️  [VECTOR-DB-SERVICE] Skipping frame at second {second} (missing embedding text)")
                continue
            
            try:
                logger.debug(f"🔄 [VECTOR-DB-SERVICE] Generating embeddings {idx}/{total_frames} for second {second}...")
                
                # Generate technical embedding (for Director)
                technical_embedding = self.get_embedding(embedding_text_technical, client)
                logger.debug(f"✅ [VECTOR-DB-SERVICE] Technical embedding generated (dimension: {len(technical_embedding)})")
                
                # Generate content embedding (for Actor)
                content_embedding = self.get_embedding(embedding_text_content, client)
                logger.debug(f"✅ [VECTOR-DB-SERVICE] Content embedding generated (dimension: {len(content_embedding)})")
                
                technical_embeddings.append(technical_embedding)
                content_embeddings.append(content_embedding)
                
                # Store metadata
                frame_filename = f"frame_{second:05d}.jpg"
                frame_path = os.path.join(frames_dir, frame_filename)
                
                metadata.append({
                    "index": len(technical_embeddings) - 1,
                    "second": second,
                    "scene_id": scene_id,
                    "frame_path": frame_path,
                    "embedding_text_technical": embedding_text_technical,
                    "embedding_text_content": embedding_text_content,
                    "llava_json": llava_json
                })
                
                # Update progress if analysis_service provided
                if analysis_service:
                    current_progress = idx / total_frames if total_frames > 0 else 0
                    analysis_service.update_overall_progress(video_id, "building_vector_db", current_progress)
                
                if idx % 10 == 0 or idx == total_frames:
                    elapsed = time.time() - start_time
                    current_progress = idx / total_frames if total_frames > 0 else 0
                    logger.info(f"📊 [VECTOR-DB-SERVICE] Progress: {idx}/{total_frames} dual embeddings ({current_progress*100:.1f}%)")
                    logger.info(f"⏱️  [VECTOR-DB-SERVICE] Elapsed: {elapsed:.1f}s | Avg: {elapsed/idx:.2f}s/frame")
                
            except Exception as e:
                logger.error(f"❌ [VECTOR-DB-SERVICE] Error processing frame at second {second}: {str(e)}", exc_info=True)
                continue
        
        if not technical_embeddings or not content_embeddings:
            logger.error(f"❌ [VECTOR-DB-SERVICE] No embeddings generated")
            raise ValueError("No embeddings generated")
        
        logger.info(f"✅ [VECTOR-DB-SERVICE] Generated {len(technical_embeddings)} technical and {len(content_embeddings)} content embeddings")
        
        # Build Technical Index (for Director role)
        logger.info(f"🔄 [VECTOR-DB-SERVICE] Building TECHNICAL vector database...")
        self._build_single_index(video_id, technical_embeddings, "technical")
        
        # Build Content Index (for Actor role)
        logger.info(f"🔄 [VECTOR-DB-SERVICE] Building CONTENT vector database...")
        self._build_single_index(video_id, content_embeddings, "content")
        
        # Save metadata (shared for both indices)
        metadata_file = self.get_metadata_file(video_id)
        logger.info(f"💾 [VECTOR-DB-SERVICE] Saving metadata to: {metadata_file}")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✅ [VECTOR-DB-SERVICE] Metadata saved ({len(metadata)} entries)")
        
        total_time = time.time() - start_time
        logger.info(f"🎉 [VECTOR-DB-SERVICE] DUAL vector database construction completed!")
        logger.info(f"⏱️  [VECTOR-DB-SERVICE] Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        logger.info(f"📊 [VECTOR-DB-SERVICE] Final sizes - Technical: {len(technical_embeddings)}, Content: {len(content_embeddings)} vectors")
    
    def _build_single_index(self, video_id: str, embeddings: List[List[float]], role: str):
        """Build and save a single FAISS index for a specific role."""
        logger.info(f"🔄 [VECTOR-DB-SERVICE] Creating {role.upper()} FAISS index...")
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings).astype("float32")
        dimension = embeddings_array.shape[1]
        logger.info(f"📊 [VECTOR-DB-SERVICE] {role.upper()} - Dimension: {dimension}, Shape: {embeddings_array.shape}")
        
        # Create FAISS index
        faiss.normalize_L2(embeddings_array)
        index = faiss.IndexFlatIP(dimension)
        
        # Add embeddings to index
        index.add(embeddings_array)
        logger.info(f"✅ [VECTOR-DB-SERVICE] {role.upper()} - Added {index.ntotal} vectors to index")
        
        # Save FAISS index
        vector_db_file = self.get_vector_db_file(video_id, role)
        logger.info(f"💾 [VECTOR-DB-SERVICE] Saving {role.upper()} index to: {vector_db_file}")
        faiss.write_index(index, vector_db_file)
        logger.info(f"✅ [VECTOR-DB-SERVICE] {role.upper()} index saved successfully")
    
    def vector_db_exists(self, video_id: str) -> bool:
        """Check if vector databases exist for a video (both technical and content)."""
        return (
            os.path.exists(self.get_vector_db_file(video_id, "technical")) and
            os.path.exists(self.get_vector_db_file(video_id, "content")) and
            os.path.exists(self.get_metadata_file(video_id))
        )
