import os
import json
import numpy as np
import faiss
from google import genai
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Configuration
VIDEO_ANALYSIS_FILE = "video_analysis_output.json"
VECTOR_DB_FILE = "video_vector_db.index"
METADATA_FILE = "video_metadata.json"
FRAMES_DIR = "frames"
EMBEDDING_MODEL = "models/gemini-embedding-001"  # Gemini embedding model


def get_embedding(text: str, client: genai.Client) -> List[float]:
    """
    Generate embedding for a text using Gemini embedding model.
    """
    try:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text
        )
        # Response has embeddings attribute which is a list
        if hasattr(response, 'embeddings') and response.embeddings:
            embedding = response.embeddings[0]
            # Handle different embedding object structures
            if hasattr(embedding, 'values'):
                return list(embedding.values)
            elif isinstance(embedding, list):
                return list(embedding)
            else:
                return list(embedding)
        else:
            raise ValueError("No embeddings in response")
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        raise


def build_vector_database():
    """
    Build FAISS vector database from video analysis output.
    Creates embeddings for each frame's embedding_text and stores with metadata.
    """
    print("📖 Loading video analysis data...")
    
    # Load video analysis output
    if not os.path.exists(VIDEO_ANALYSIS_FILE):
        raise FileNotFoundError(f"❌ {VIDEO_ANALYSIS_FILE} not found. Run videosampler.py first.")
    
    with open(VIDEO_ANALYSIS_FILE, "r") as f:
        video_data = json.load(f)
    
    frames = video_data.get("frames", [])
    if not frames:
        raise ValueError("❌ No frames found in video analysis output.")
    
    print(f"📊 Found {len(frames)} frames to process")
    
    # Initialize Gemini client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY not found in environment variables")
    
    api_key = api_key.strip()
    client = genai.Client(api_key=api_key)
    
    # Generate embeddings
    print("🔄 Generating embeddings...")
    embeddings = []
    metadata = []
    
    for idx, frame in enumerate(frames):
        second = frame.get("second", idx)
        embedding_text = frame.get("embedding_text", "")
        llava_json = frame.get("llava_json", {})
        
        if not embedding_text:
            print(f"⚠️  Warning: No embedding_text for second {second}, skipping...")
            continue
        
        # Generate embedding
        try:
            embedding = get_embedding(embedding_text, client)
            embeddings.append(embedding)
            
            # Store metadata: second, frame path, and full JSON
            frame_filename = f"frame_{second:05d}.jpg"
            frame_path = os.path.join(FRAMES_DIR, frame_filename)
            
            metadata.append({
                "index": len(embeddings) - 1,
                "second": second,
                "frame_path": frame_path,
                "embedding_text": embedding_text,
                "llava_json": llava_json
            })
            
            if (idx + 1) % 10 == 0:
                print(f"✅ Processed {idx + 1}/{len(frames)} frames...")
                
        except Exception as e:
            print(f"❌ Error processing frame at second {second}: {e}")
            continue
    
    if not embeddings:
        raise ValueError("❌ No embeddings generated. Check your data and API key.")
    
    print(f"✅ Generated {len(embeddings)} embeddings")
    
    # Convert to numpy array
    embeddings_array = np.array(embeddings).astype("float32")
    dimension = embeddings_array.shape[1]
    
    print(f"📐 Embedding dimension: {dimension}")
    
    # Create FAISS index (using L2 distance - Inner Product for cosine similarity)
    # For cosine similarity, we normalize vectors and use Inner Product
    faiss.normalize_L2(embeddings_array)
    index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity
    
    # Add embeddings to index
    print("💾 Building FAISS index...")
    index.add(embeddings_array)
    
    # Save FAISS index
    print(f"💾 Saving FAISS index to {VECTOR_DB_FILE}...")
    faiss.write_index(index, VECTOR_DB_FILE)
    
    # Save metadata
    print(f"💾 Saving metadata to {METADATA_FILE}...")
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n🎉 Vector database created successfully!")
    print(f"📊 Index size: {index.ntotal} vectors")
    print(f"📁 Files created:")
    print(f"   - {VECTOR_DB_FILE}")
    print(f"   - {METADATA_FILE}")


if __name__ == "__main__":
    try:
        build_vector_database()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
