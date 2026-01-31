import os
import json
import re
import time
from google import genai
from google.genai import types
import PIL.Image
from typing import Dict, Any, List
from dotenv import load_dotenv
load_dotenv()
FRAMES_DIR = "frames"
OUTPUT_FILE = "video_analysis_output.json"


# -------------------------------------------------
# Helper: clean markdown and extract JSON
# -------------------------------------------------
def extract_json(text: str) -> Dict[str, Any]:
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return json.loads(text.strip())


# -------------------------------------------------
# Step 1: JSON → Embedding-ready canonical text
# -------------------------------------------------
def normalize_list(items: List[Any], key: str) -> List[str]:
    result = []
    for item in items:
        if isinstance(item, dict):
            value = item.get(key)
            if value:
                result.append(str(value))
        elif isinstance(item, str):
            result.append(item)
    return result


def json_to_embedding_text(data: Dict[str, Any]) -> str:
    objects = normalize_list(data.get("objects", []), "type")
    actions = normalize_list(data.get("actions", []), "type")

    return (
        f"Second: {data.get('second')}\n"
        f"Objects: {', '.join(objects) if objects else 'none'}\n"
        f"Actions: {', '.join(actions) if actions else 'none'}\n"
        f"Summary: {data.get('scene_summary', '').strip()}"
    )


# -------------------------------------------------
# Step 2: Call Gemini 2 for one frame with retry logic
# -------------------------------------------------
def describe_image_with_llava(image_path: str, second: int, client: genai.Client = None) -> Dict[str, Any]:
    # Initialize Gemini API client (reuse if provided)
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Clean API key - strip whitespace
        api_key = api_key.strip()
        
        # Validate API key format (should only contain alphanumeric, hyphens, underscores)
        # This helps catch copy-paste errors with special characters
        if not api_key.replace('-', '').replace('_', '').isalnum():
            raise ValueError(
                "GEMINI_API_KEY contains invalid characters. "
                "API keys should only contain letters, numbers, hyphens, and underscores. "
                "Please check your .env file and ensure the key is correct."
            )
        
        # Create client
        client = genai.Client(api_key=api_key)
    
    prompt = f"""
This image is from second {second} of a video.

Return ONLY valid JSON.
Do NOT use markdown or backticks.

Schema:
{{
  "second": {second},
  "objects": [{{ "type": "" }}],
  "actions": [{{ "type": "" }}],
  "scene_summary": ""
}}
"""

    # Read image file
    img = PIL.Image.open(image_path)
    
    # Retry logic for rate limiting
    max_retries = 5
    base_delay = 6  # Base delay in seconds (to stay under 10 requests/min)
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, img],
                config=types.GenerateContentConfig(temperature=0)
            )
            return extract_json(response.text)
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a rate limit error (429)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                if attempt < max_retries - 1:
                    # Extract retry delay from error if available, otherwise use exponential backoff
                    retry_delay = base_delay * (2 ** attempt)  # Exponential backoff: 6, 12, 24, 48, 96 seconds
                    
                    # Try to extract suggested delay from error message
                    if "retryDelay" in error_str or "RetryInfo" in error_str:
                        # Look for delay in seconds in the error message
                        delay_match = re.search(r'retryDelay[:\'"]?\s*[\'"]?(\d+)', error_str, re.IGNORECASE)
                        if delay_match:
                            retry_delay = int(delay_match.group(1)) + 5  # Add 5 seconds buffer
                    
                    print(f"⏳ Rate limit hit. Waiting {retry_delay} seconds before retry (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded after {max_retries} attempts. Please wait and try again later.")
            else:
                # For other errors, raise immediately
                raise

    raise Exception("Failed to get response after all retries")


# -------------------------------------------------
# Step 3: Process all frames
# -------------------------------------------------
def process_video_frames():
    results = []
    
    # Initialize client once and reuse it
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    api_key = api_key.strip()
    client = genai.Client(api_key=api_key)
    
    # Rate limiting: 10 requests per minute = 6 seconds between requests minimum
    # Using 7 seconds to be safe
    request_delay = 7

    for filename in sorted(os.listdir(FRAMES_DIR)):
        if not filename.endswith(".jpg"):
            continue

        second = int(filename.split("_")[1].split(".")[0])
        image_path = os.path.join(FRAMES_DIR, filename)

        print(f"▶ Processing second {second}")

        try:
            llava_json = describe_image_with_llava(image_path, second, client)
            embedding_text = json_to_embedding_text(llava_json)

            results.append({
                "second": second,
                "llava_json": llava_json,
                "embedding_text": embedding_text
            })

            print(f"✅ Done second {second}")
            
            # Add delay between requests to stay within rate limit
            # Skip delay on last request
            if second < len([f for f in os.listdir(FRAMES_DIR) if f.endswith(".jpg")]) - 1:
                time.sleep(request_delay)

        except Exception as e:
            print(f"❌ Failed at second {second}: {e}")
            # Still add delay even on failure to respect rate limits
            time.sleep(request_delay)

    return results


# -------------------------------------------------
# Main
# -------------------------------------------------
if __name__ == "__main__":
    output = {
        "video_id": "sample_video_001",
        "frames": process_video_frames()
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n🎉 Processing complete")
    print(f"📄 Output saved to {OUTPUT_FILE}")

    #uvicorn main:app --host 0.0.0.0 --port 8000