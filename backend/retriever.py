import os
import json
import numpy as np
import faiss
from google import genai
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

# Configuration
VECTOR_DB_FILE = "video_vector_db.index"
METADATA_FILE = "video_metadata.json"
EMBEDDING_MODEL = "models/gemini-embedding-001"
DEFAULT_TOP_K = 5  # Number of results to retrieve


class VideoRetriever:
    """
    Retrieves relevant video frames based on user queries using FAISS vector search.
    """
    
    def __init__(self):
        """Initialize the retriever by loading the FAISS index and metadata."""
        print("🔄 Loading vector database...")
        
        # Check if files exist
        if not os.path.exists(VECTOR_DB_FILE):
            raise FileNotFoundError(
                f"❌ {VECTOR_DB_FILE} not found. Run vector_db_builder.py first."
            )
        if not os.path.exists(METADATA_FILE):
            raise FileNotFoundError(
                f"❌ {METADATA_FILE} not found. Run vector_db_builder.py first."
            )
        
        # Load FAISS index
        self.index = faiss.read_index(VECTOR_DB_FILE)
        print(f"✅ Loaded FAISS index with {self.index.ntotal} vectors")
        
        # Load metadata
        with open(METADATA_FILE, "r") as f:
            self.metadata = json.load(f)
        print(f"✅ Loaded metadata for {len(self.metadata)} frames")
        
        # Initialize Gemini client for embeddings
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY not found in environment variables")
        
        api_key = api_key.strip()
        self.client = genai.Client(api_key=api_key)
        
        print("✅ Retriever initialized successfully!\n")
    
    def _get_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for the user query."""
        try:
            response = self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=query
            )
            # Response has embeddings attribute which is a list
            if hasattr(response, 'embeddings') and response.embeddings:
                embedding_obj = response.embeddings[0]
                # Handle different embedding object structures
                if hasattr(embedding_obj, 'values'):
                    embedding_values = list(embedding_obj.values)
                elif isinstance(embedding_obj, list):
                    embedding_values = list(embedding_obj)
                else:
                    embedding_values = list(embedding_obj)
            else:
                raise ValueError("No embeddings in response")
            
            embedding = np.array([embedding_values], dtype="float32")
            faiss.normalize_L2(embedding)  # Normalize for cosine similarity
            return embedding
        except Exception as e:
            raise Exception(f"Error generating query embedding: {e}")
    
    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        """
        Search for relevant frames based on the query.
        
        Args:
            query: User's search query
            top_k: Number of results to return
            
        Returns:
            List of dictionaries containing:
            - second: timestamp in seconds
            - frame_path: path to the frame image
            - score: similarity score
            - embedding_text: the text description
            - llava_json: full frame analysis JSON
        """
        # Generate query embedding
        query_embedding = self._get_query_embedding(query)
        
        # Search in FAISS index
        scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # Retrieve metadata for results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # Invalid index
                continue
            
            meta = self.metadata[idx]
            results.append({
                "second": meta["second"],
                "frame_path": meta["frame_path"],
                "score": float(score),
                "embedding_text": meta["embedding_text"],
                "llava_json": meta["llava_json"]
            })
        
        return results
    
    def format_timestamp(self, seconds: int) -> str:
        """Convert seconds to MM:SS format."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for display."""
        if not results:
            return "No results found."
        
        formatted = []
        for i, result in enumerate(results, 1):
            timestamp = self.format_timestamp(result["second"])
            score = result["score"]
            summary = result["llava_json"].get("scene_summary", "No summary")
            
            formatted.append(
                f"{i}. [{timestamp}]({result['second']}) - Score: {score:.3f}\n"
                f"   {summary}\n"
                f"   Frame: {result['frame_path']}"
            )
        
        return "\n".join(formatted)


def chat_loop():
    """
    Interactive chat loop for continuous queries.
    """
    try:
        retriever = VideoRetriever()
    except Exception as e:
        print(f"❌ Failed to initialize retriever: {e}")
        return
    
    print("=" * 60)
    print("🎬 Video Frame Retriever - Chat Mode")
    print("=" * 60)
    print("Type your queries to find relevant video frames.")
    print("Commands:")
    print("  - 'quit' or 'exit' to stop")
    print("  - 'top_k N' to change number of results (default: 5)")
    print("=" * 60)
    print()
    
    top_k = DEFAULT_TOP_K
    
    while True:
        try:
            # Get user query
            query = input("🔍 Your query: ").strip()
            
            if not query:
                continue
            
            # Handle commands
            if query.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            if query.lower().startswith("top_k"):
                try:
                    new_k = int(query.split()[-1])
                    top_k = max(1, min(new_k, 20))  # Limit between 1-20
                    print(f"✅ Top-K set to {top_k}\n")
                    continue
                except:
                    print("❌ Invalid format. Use: top_k 5\n")
                    continue
            
            # Perform search
            print(f"\n🔎 Searching for top {top_k} results...")
            results = retriever.search(query, top_k=top_k)
            
            if not results:
                print("❌ No results found.\n")
                continue
            
            # Display results
            print("\n" + "=" * 60)
            print("📋 Results:")
            print("=" * 60)
            print(retriever.format_results(results))
            print("=" * 60)
            print()
            
            # Show timestamps in a list for easy reference
            timestamps = [retriever.format_timestamp(r["second"]) for r in results]
            print(f"⏱️  Timestamps: {', '.join(timestamps)}")
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    chat_loop()
