import asyncio
import cv2
import sys
import os

# Install: pip install google-genai opencv-python
from google import genai
from google.genai import types

# --- CONFIGURATION ---
API_KEY = "AIzaSyDpO-DdnuzmGu5JYCOpSANDK2x5acYhbZQ" # Paste your fresh key here

# We use 'gemini-exp-1206' because it was explicitly in your available list
# and supports multimodal inputs without forcing audio.
MODEL_ID = "gemini-exp-1206" 

SYSTEM_INSTRUCTION = """
You are a helpful video assistant. 
Watch the video stream and provide a concise, real-time commentary 
on what the user is doing or holding. 
Keep your responses short and snappy (under 1 sentence).
"""

async def main():
    # Force v1alpha for experimental models
    client = genai.Client(api_key=API_KEY, http_options={'api_version': 'v1alpha'})

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print(f"--- connecting to {MODEL_ID} ---")
    
    # We explicitly configure the generation to be safe and text-focused
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"], 
        system_instruction=types.Content(parts=[types.Part(text=SYSTEM_INSTRUCTION)]),
        generation_config=types.GenerationConfig(
            temperature=0.5, 
            max_output_tokens=150
        )
    )

    try:
        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            print("--- Connected! Press 'q' to quit ---")

            # 1. Start a task to listen for the AI's response
            async def receive_responses():
                while True:
                    try:
                        async for response in session.receive():
                            server_content = response.server_content
                            if server_content and server_content.model_turn:
                                for part in server_content.model_turn.parts:
                                    if part.text:
                                        print(f"Gemini: {part.text}", flush=True)
                    except Exception as e:
                        print(f"Receive loop error: {e}")
                        break
            
            receive_task = asyncio.create_task(receive_responses())

            # 2. Send an initial text "hello" to wake up the model safely
            await session.send(input="Hello, I am streaming video now.", end_of_turn=True)

            # 3. Main Video Loop
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Resize to 640x480 to save bandwidth/latency
                frame_resized = cv2.resize(frame, (640, 480))
                
                # Encode to JPEG
                _, buffer = cv2.imencode('.jpg', frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 50])
                
                # Send the image bytes
                await session.send(input=buffer.tobytes(), mime_type="image/jpeg", end_of_turn=True)

                cv2.imshow('Gemini Live Feed', frame)
                
                # Wait 1 second (sending too fast causes rate limit errors)
                await asyncio.sleep(1.0) 

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            receive_task.cancel()

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        if "404" in str(e) or "Not Found" in str(e):
             print(f"Model {MODEL_ID} not found. Try 'gemini-2.0-flash-001' next.")
        elif "403" in str(e):
             print("Permission denied. Please check your API Key.")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("--- disconnected ---")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())