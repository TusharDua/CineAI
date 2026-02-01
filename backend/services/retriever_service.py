import os
import json
import numpy as np
import faiss
from google import genai
from google.genai import types
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from services.vector_db_service import VectorDBService


class RetrieverService:
    """
    Service for retrieving relevant frames from vector database with LLM-generated answers.
    """
    
    EMBEDDING_MODEL = "models/gemini-embedding-001"
    LLM_MODEL = "gemini-2.0-flash"  # For generating answers
    DEFAULT_TOP_K = 5
    
    def __init__(self):
        self.vector_db_service = VectorDBService()
        self._loaded_indices = {}  # Cache loaded indices
    
    def _load_index(self, video_id: str, role: str = "content"):
        """Load FAISS index and metadata for a video and role (with caching)."""
        cache_key = f"{video_id}_{role}"
        if cache_key in self._loaded_indices:
            return self._loaded_indices[cache_key]
        
        vector_db_file = self.vector_db_service.get_vector_db_file(video_id, role)
        metadata_file = self.vector_db_service.get_metadata_file(video_id)
        
        if not os.path.exists(vector_db_file) or not os.path.exists(metadata_file):
            raise FileNotFoundError(f"Vector database not found for video {video_id} with role {role}")
        
        index = faiss.read_index(vector_db_file)
        
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        # Initialize Gemini client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        api_key = api_key.strip()
        client = genai.Client(api_key=api_key)
        
        self._loaded_indices[cache_key] = {
            "index": index,
            "metadata": metadata,
            "client": client
        }
        
        return self._loaded_indices[cache_key]
    
    def _get_query_embedding(self, query: str, client: genai.Client, role: str = "actor") -> np.ndarray:
        """
        Generate embedding for query with role-specific context.
        This ensures the query embedding matches the vector space of the target index.
        """
        try:
            # Add role-specific context to query for better semantic alignment
            if role == "director":
                # For director: emphasize technical/cinematography aspects
                enhanced_query = f"Technical cinematography and filmmaking: {query}. Focus on shot types, camera angles, lighting, and visual composition."
            elif role == "producer":
                # For producer: emphasize production/commercial aspects and OBJECTS/PROPS
                enhanced_query = f"Production and commercial aspects: {query}. Focus on visible objects, props, equipment, vehicles, production value, locations, sets, costumes, budget indicators, and commercial appeal. Pay special attention to specific items and objects present in the scene."
            else:
                # For actor: emphasize content/performance aspects
                enhanced_query = f"Scene content and performance: {query}. Focus on characters, actions, emotions, and story elements."
            
            response = client.models.embed_content(
                model=self.EMBEDDING_MODEL,
                contents=enhanced_query
            )
            
            if hasattr(response, 'embeddings') and response.embeddings:
                embedding_obj = response.embeddings[0]
                if hasattr(embedding_obj, 'values'):
                    embedding_values = list(embedding_obj.values)
                elif isinstance(embedding_obj, list):
                    embedding_values = list(embedding_obj)
                else:
                    embedding_values = list(embedding_obj)
            else:
                raise ValueError("No embeddings in response")
            
            embedding = np.array([embedding_values], dtype="float32")
            faiss.normalize_L2(embedding)
            return embedding
        except Exception as e:
            raise Exception(f"Error generating query embedding: {e}")
    
    def search(self, video_id: str, query: str, role: str = "actor", top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        """
        Search for relevant frames based on role.
        
        Args:
            video_id: Unique video identifier
            query: Search query
            role: User role - "actor" (content search), "director" (technical search), or "producer" (production search)
            top_k: Number of results to return
            
        Returns:
            List of result dictionaries with duplicate timestamps filtered out
        """
        # Map role to index type
        if role == "director":
            index_type = "technical"
        elif role == "producer":
            index_type = "production"
        else:  # actor
            index_type = "content"
        
        # Load index and metadata
        data = self._load_index(video_id, index_type)
        index = data["index"]
        metadata = data["metadata"]
        client = data["client"]
        
        # Generate query embedding with role-specific context
        query_embedding = self._get_query_embedding(query, client, role)
        
        # For removing duplicates, fetch more results initially
        fetch_k = top_k * 3 if role == "producer" else top_k * 2
        
        # Search in FAISS index
        scores, indices = index.search(query_embedding, min(fetch_k, index.ntotal))
        
        # Retrieve metadata for results
        results = []
        seen_timestamps = set()
        TIME_THRESHOLD = 3  # seconds - consider timestamps within 3 seconds as duplicates
        
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            
            meta = metadata[idx]
            second = meta["second"]
            
            # Check if this timestamp is too close to an already added one
            is_duplicate = False
            for seen_ts in seen_timestamps:
                if abs(second - seen_ts) <= TIME_THRESHOLD:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # Extract role-specific information
            llava_json = meta.get("llava_json", {})
            result = {
                "second": second,
                "frame_path": meta["frame_path"],
                "score": float(score),
                "timestamp": self._format_timestamp(second),
                "scene_id": meta.get("scene_id", "scene_000")
            }
            
            # Add role-specific data
            if role == "director":
                result["technical_info"] = llava_json.get("technical_info", {})
                result["embedding_text"] = meta.get("embedding_text_technical", "")
            elif role == "producer":
                result["production_info"] = llava_json.get("production_info", {})
                result["embedding_text"] = meta.get("embedding_text_production", "")
            else:  # actor
                result["content_info"] = llava_json.get("content_info", {})
                result["embedding_text"] = meta.get("embedding_text_content", "")
            
            # Always include scene summary
            content_info = llava_json.get("content_info", {})
            result["scene_summary"] = content_info.get("scene_summary", "")
            
            results.append(result)
            seen_timestamps.add(second)
            
            # Stop if we have enough unique results
            if len(results) >= top_k:
                break
        
        # Sort by timestamp (ascending order)
        results.sort(key=lambda x: x['second'])
        
        return results
    
    def _format_timestamp(self, seconds: int) -> str:
        """Convert seconds to MM:SS format."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def _expand_query(self, query: str, role: str) -> List[str]:
        """
        Expand query to capture semantic variations and improve recall.
        """
        query_lower = query.lower()
        expansions = [query]  # Always include original
        
        # Emotion expansions
        emotion_map = {
            'romantic': ['romantic', 'intimate', 'loving', 'tender', 'affectionate', 'passionate'],
            'emotional': ['emotional', 'touching', 'moving', 'heartfelt', 'poignant'],
            'happy': ['happy', 'joyful', 'cheerful', 'content', 'pleased', 'delighted'],
            'sad': ['sad', 'melancholic', 'sorrowful', 'upset', 'unhappy', 'grieving'],
            'tense': ['tense', 'anxious', 'nervous', 'worried', 'stressed', 'uneasy'],
            'peaceful': ['peaceful', 'calm', 'serene', 'tranquil', 'relaxed', 'quiet'],
            'angry': ['angry', 'furious', 'rage', 'mad', 'irritated', 'hostile']
        }
        
        # Location expansions
        location_map = {
            'beach': ['beach', 'seaside', 'ocean', 'shore', 'coast', 'waterfront'],
            'woods': ['woods', 'forest', 'trees', 'woodland', 'nature'],
            'city': ['city', 'urban', 'street', 'downtown', 'metropolitan'],
            'indoor': ['indoor', 'inside', 'interior', 'room']
        }
        
        # Action expansions
        action_map = {
            'walking': ['walking', 'strolling', 'pacing', 'moving'],
            'running': ['running', 'sprinting', 'rushing', 'hurrying'],
            'fighting': ['fighting', 'combat', 'battle', 'struggle'],
            'talking': ['talking', 'speaking', 'conversing', 'discussing']
        }
        
        # Expand emotions
        for base_emotion, synonyms in emotion_map.items():
            if base_emotion in query_lower:
                for synonym in synonyms[:3]:  # Top 3 synonyms
                    expanded = query_lower.replace(base_emotion, synonym)
                    if expanded != query_lower:
                        expansions.append(expanded)
        
        # Expand locations
        for base_location, synonyms in location_map.items():
            if base_location in query_lower:
                for synonym in synonyms[:2]:  # Top 2 synonyms
                    expanded = query_lower.replace(base_location, synonym)
                    if expanded != query_lower:
                        expansions.append(expanded)
        
        # Expand actions
        for base_action, synonyms in action_map.items():
            if base_action in query_lower:
                for synonym in synonyms[:2]:
                    expanded = query_lower.replace(base_action, synonym)
                    if expanded != query_lower:
                        expansions.append(expanded)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_expansions = []
        for exp in expansions:
            if exp not in seen:
                seen.add(exp)
                unique_expansions.append(exp)
        
        return unique_expansions[:5]  # Return top 5 expansions
        """Convert seconds to MM:SS format."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def _generate_answer(self, query: str, results: List[Dict[str, Any]], role: str, client: genai.Client) -> Dict[str, Any]:
        """
        Generate a natural language answer using LLM based on retrieved results.
        Returns answer with most relevant moments only.
        """
        if not results:
            return {
                "answer": "I couldn't find any relevant moments in the video that match your query. Try rephrasing or asking about something else.",
                "relevant_moments": [],
                "found_count": 0
            }
        
        # Build RICH context from retrieved results
        context_parts = []
        for idx, result in enumerate(results, 1):
            timestamp = result["timestamp"]
            second = result["second"]
            summary = result["scene_summary"]
            
            if role == "director":
                tech = result.get("technical_info", {})
                context_parts.append(
                    f"Moment {idx} at {timestamp} (second {second}):\n"
                    f"  Shot: {tech.get('shot_type', 'unknown')}\n"
                    f"  Angle: {tech.get('camera_angle', 'unknown')}\n"
                    f"  Lighting: {tech.get('lighting', 'unknown')}\n"
                    f"  Color: {tech.get('color_grading', 'unknown')}\n"
                    f"  Visual Mood: {tech.get('visual_mood', 'unknown')}\n"
                    f"  Scene: {summary}"
                )
            elif role == "producer":
                prod = result.get("production_info", {})
                props = prod.get("props", [])
                props_str = ", ".join([str(p) for p in props]) if props else "none"
                
                context_parts.append(
                    f"Moment {idx} at {timestamp} (second {second}):\n"
                    f"  Production Value: {prod.get('production_value', 'unknown')}\n"
                    f"  Location Type: {prod.get('location_type', 'unknown')}\n"
                    f"  Set Design: {prod.get('set_design', 'unknown')}\n"
                    f"  **Props/Objects: {props_str}**\n"  # Emphasized
                    f"  Costumes: {prod.get('costumes', 'unknown')}\n"
                    f"  Commercial Appeal: {prod.get('commercial_appeal', 'unknown')}\n"
                    f"  Budget: {prod.get('budget_indication', 'unknown')}\n"
                    f"  Pacing: {prod.get('pacing', 'unknown')}\n"
                    f"  Scene: {summary}"
                )
            else:  # actor
                content = result.get("content_info", {})
                
                # Handle emotions (dict or list format)
                emotions_data = content.get("emotions", {})
                if isinstance(emotions_data, dict):
                    emotion_str = f"{emotions_data.get('primary', 'neutral')}"
                    if emotions_data.get('secondary'):
                        emotion_str += f", {', '.join(emotions_data.get('secondary', []))}"
                    emotion_str += f" ({emotions_data.get('intensity', 'medium')} intensity)"
                    if emotions_data.get('context'):
                        emotion_str += f" - {emotions_data.get('context')}"
                else:
                    emotions = content.get("emotions", [])
                    emotion_str = ", ".join([e.get("type", "none") for e in emotions]) if emotions else "none"
                
                # Get setting details
                setting = content.get("setting", {})
                if isinstance(setting, dict):
                    setting_str = setting.get("location", "unknown")
                    if setting.get("atmosphere"):
                        setting_str += f", {setting.get('atmosphere')} atmosphere"
                else:
                    setting_str = str(setting) if setting else "unknown"
                
                # Get actions
                actions = content.get("actions", [])
                actions_str = ", ".join([str(a) for a in actions]) if actions else "none"
                
                # Get mood
                mood = content.get("mood", "neutral")
                
                context_parts.append(
                    f"Moment {idx} at {timestamp} (second {second}):\n"
                    f"  Setting: {setting_str}\n"
                    f"  Characters: {content.get('character_count', 0)}\n"
                    f"  Emotions: {emotion_str}\n"
                    f"  Actions: {actions_str}\n"
                    f"  Mood: {mood}\n"
                    f"  Scene: {summary}"
                )
        
        context = "\n\n".join(context_parts)
        
        # Create prompt for LLM
        if role == "director":
            system_prompt = """You are a master cinematographer analyzing video footage. 
Based on the retrieved moments with detailed technical analysis, answer the user's question about cinematography, shot composition, lighting, and visual storytelling.

Be specific, accurate, and honest. If moments truly match, explain which ones and why. 
If they don't match well, say so and suggest what to search for instead.
Focus on technical and visual aspects."""
        elif role == "producer":
            system_prompt = """You are an experienced film producer analyzing production elements and commercial aspects.
Based on the retrieved moments with detailed production analysis, answer the user's question about production value, locations, sets, props, costumes, budget indicators, and commercial viability.

**IMPORTANT:** Pay special attention to visible objects, props, equipment, and items in the scene. When the user asks about objects (like "find car" or "show phone"), prioritize mentioning the specific props and objects present.

Be specific, accurate, and honest. If moments truly match, explain which ones and why, highlighting the specific objects/props found.
If they don't match well, say so and suggest what to search for instead.
Focus on objective, business-oriented production elements and specific visible items."""
        else:
            system_prompt = """You are an expert video content analyst specializing in story, performance, emotions, and atmosphere.
Based on the retrieved moments with detailed content analysis, answer the user's question about characters, emotions, actions, settings, and narrative elements.

Be specific, accurate, and honest. If moments truly match, explain which ones and why.
If they don't match well, say so and suggest what to search for instead.
Capture subtle emotional nuances and atmospheric details."""
        
        prompt = f"""User Query: "{query}"

Retrieved Moments from Video (with rich details):
{context}

Task: 
1. Carefully analyze if these moments TRULY answer the user's query
2. Look for subtle details that match the query (emotions, atmosphere, settings, actions)
3. Provide a clear, natural answer (2-4 sentences) explaining what you found
4. List ONLY the moment numbers that are genuinely relevant (e.g., "1, 3" or "2" or "none")
5. If none truly match, honestly say so and suggest alternative search terms

Important:
- Be specific about WHY moments are relevant (mention emotions, settings, actions)
- Don't force matches - if nothing fits, say so
- Capture subtle nuances (romantic vs just happy, tense vs angry, etc.)

Format:
ANSWER: [Your detailed natural language answer]
RELEVANT: [Comma-separated moment numbers like "1, 3, 5" or "none"]"""

        try:
            response = client.models.generate_content(
                model=self.LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,  # Lower for more accurate analysis
                    system_instruction=system_prompt
                )
            )
            
            response_text = response.text.strip()
            
            # Parse response
            answer_line = ""
            relevant_line = ""
            
            for line in response_text.split('\n'):
                if line.startswith('ANSWER:'):
                    answer_line = line.replace('ANSWER:', '').strip()
                elif line.startswith('RELEVANT:'):
                    relevant_line = line.replace('RELEVANT:', '').strip()
            
            # If not in expected format, use whole response as answer
            if not answer_line:
                answer_line = response_text
                relevant_line = "1"  # Default to first result
            
            # Parse relevant moment numbers
            relevant_indices = []
            if relevant_line.lower() != "none":
                try:
                    relevant_indices = [int(x.strip()) - 1 for x in relevant_line.split(',') if x.strip().isdigit()]
                except:
                    relevant_indices = [0]  # Default to first if parsing fails
            
            # Filter to only relevant moments
            relevant_moments = []
            for idx in relevant_indices:
                if 0 <= idx < len(results):
                    relevant_moments.append(results[idx])
            
            # Sort relevant moments by timestamp (ascending order for chronological viewing)
            relevant_moments.sort(key=lambda x: x['second'])
            
            # If LLM said none are relevant but we have results, include top 1 with disclaimer
            if not relevant_moments and results:
                relevant_moments = [results[0]]
                answer_line = f"While I found some moments, they don't closely match '{query}'. Here's the closest match, but consider refining your search. {answer_line}"
            
            return {
                "answer": answer_line,
                "relevant_moments": relevant_moments,
                "found_count": len(relevant_moments)
            }
            
        except Exception as e:
            # Fallback: return simple answer with top results
            return {
                "answer": f"I found {len(results)} moment(s) that might be relevant to '{query}'. Please review them to see if they match what you're looking for.",
                "relevant_moments": results[:3],  # Top 3
                "found_count": len(results[:3])
            }
    
    def search_with_answer(self, video_id: str, query: str, role: str = "actor", top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
        """
        Intelligent search with query expansion and answer generation using RAG pattern.
        
        Returns:
            Dict with 'answer' (natural language), 'relevant_moments' (filtered list), 'found_count'
        """
        # Expand query for better semantic coverage
        expanded_queries = self._expand_query(query, role)
        
        # Search with multiple query variations
        all_candidates = {}  # Use dict to deduplicate by second
        for exp_query in expanded_queries:
            results = self.search(video_id, exp_query, role, top_k=10)
            for result in results:
                second = result["second"]
                if second not in all_candidates or result["score"] > all_candidates[second]["score"]:
                    all_candidates[second] = result
        
        # Convert back to list and sort by score first to get best matches
        raw_results = sorted(all_candidates.values(), key=lambda x: x["score"], reverse=True)[:top_k]
        
        # Then sort by timestamp for chronological display
        raw_results.sort(key=lambda x: x["second"])
        
        # Load client for LLM
        index_type = "technical" if role == "director" else "production" if role == "producer" else "content"
        data = self._load_index(video_id, index_type)
        client = data["client"]
        
        # Generate intelligent answer
        return self._generate_answer(query, raw_results, role, client)
