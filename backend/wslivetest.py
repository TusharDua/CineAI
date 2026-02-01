# -*- coding: utf-8 -*-
"""
Gemini Live API - Voice & Video GUI (Stable VAD & Queue Fix)
Purpose: Fixes QueueFull crashes and includes "Force Reply" for audio issues.
"""

import asyncio
import base64
import io
import threading
import queue
import traceback
import cv2
import pyaudio
import PIL.Image, PIL.ImageTk
import tkinter as tk
from tkinter import scrolledtext
from google import genai

# --- CONFIGURATION ---
API_KEY = 
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

CONFIG = {
    "response_modalities": ["AUDIO"],
    "output_audio_transcription": {},
    "system_instruction": """
    You are a helpful assistant. 
    You can see the user's video feed. 
    If the user asks about their desk or items, describe exactly what you see.
    Be concise and conversational.
    """
}

# --- AUDIO SETTINGS ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

class GeminiVoiceWorker:
    def __init__(self, output_queue):
        self.output_queue = output_queue
        self.client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1beta"})
        self.session = None
        self.video_queue = asyncio.Queue(maxsize=1)
        self.command_queue = asyncio.Queue()
        self.running = True
        
        self.pya = pyaudio.PyAudio()
        self.mic_stream = None
        self.speaker_stream = None
        
        # DEBUG: List Microphones
        print("\n--- AVAILABLE MICROPHONES ---")
        for i in range(self.pya.get_device_count()):
            info = self.pya.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"Index {i}: {info['name']}")
        print("-----------------------------\n")

    def start(self):
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.mic_stream = self.pya.open(
                format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE,
                input=True, frames_per_buffer=CHUNK_SIZE
            )
            self.speaker_stream = self.pya.open(
                format=FORMAT, channels=CHANNELS, rate=RECEIVE_SAMPLE_RATE,
                output=True, frames_per_buffer=CHUNK_SIZE
            )
        except Exception as e:
            self.output_queue.put(f"[Error] Audio Device Failed: {e}")
            return

        try:
            self.loop.run_until_complete(self.main_task())
        except Exception as e:
            self.output_queue.put(f"[Error] Backend crashed: {e}")
        finally:
            self.cleanup()

    async def main_task(self):
        while self.running:
            self.output_queue.put("[System] Connecting to Gemini...")
            try:
                async with self.client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                    self.session = session
                    self.output_queue.put("[System] Connected! Speak now.")
                    
                    await asyncio.gather(
                        self.send_video_loop(),
                        self.send_audio_loop(),
                        self.receive_loop(),
                        self.command_loop()
                    )
            except Exception as e:
                self.output_queue.put(f"[Error] Disconnected: {e}")
                self.output_queue.put("[System] Reconnecting in 2s...")
                await asyncio.sleep(2)

    async def send_video_loop(self):
        while self.running:
            try:
                frame_data = await self.video_queue.get()
                await self.session.send_realtime_input(media_chunks=[frame_data])
                await asyncio.sleep(0.5) 
            except Exception:
                break

    async def send_audio_loop(self):
        """Reads mic data and sends to API."""
        while self.running:
            try:
                data = await asyncio.to_thread(self.mic_stream.read, CHUNK_SIZE, exception_on_overflow=False)
                await self.session.send_realtime_input(media_chunks=[{"mime_type": "audio/pcm", "data": base64.b64encode(data).decode()}])
            except Exception:
                break

    async def command_loop(self):
        """Listens for 'Force Reply' button click."""
        while True:
            cmd = await self.command_queue.get()
            if cmd == "FORCE_REPLY":
                self.output_queue.put("[System] Sending 'End of Turn' signal...")
                await self.session.send_client_content(turns=[], turn_complete=True)

    async def receive_loop(self):
        while self.running:
            try:
                turn = self.session.receive()
                async for response in turn:
                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data:
                                self.speaker_stream.write(part.inline_data.data)

                    if response.server_content and response.server_content.output_transcription:
                        text = response.server_content.output_transcription.text
                        if text:
                            self.output_queue.put(f"AI: {text}")
            except Exception:
                break

    def trigger_force_reply(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(
                lambda: self.command_queue.put_nowait("FORCE_REPLY")
            )

    def cleanup(self):
        if self.mic_stream: self.mic_stream.close()
        if self.speaker_stream: self.speaker_stream.close()
        self.pya.terminate()

    # --- THE FIX: SAFE FRAME ENQUEUEING ---
    def send_frame(self, frame_data):
        # We perform the queue operation INSIDE the loop thread to be safe
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._enqueue_video_frame, frame_data)

    def _enqueue_video_frame(self, frame_data):
        # This function runs safely inside the background thread
        try:
            # If queue is full, remove the old frame to make space
            if self.video_queue.full():
                self.video_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass # Queue was already empty, ignore
        
        try:
            # Now safely put the new frame
            self.video_queue.put_nowait(frame_data)
        except asyncio.QueueFull:
            pass # Should not happen, but prevents crash if it does

# --- FRONTEND: UI ---
class VoiceScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini Voice & Vision (Stable)")
        self.root.geometry("1100x650")
        
        self.msg_queue = queue.Queue()
        self.worker = GeminiVoiceWorker(self.msg_queue)
        
        self.cap = cv2.VideoCapture(0)
        
        self.setup_ui()
        self.worker.start()
        
        self.update_video()
        self.check_messages()

    def setup_ui(self):
        left_frame = tk.Frame(self.root, bg="black")
        left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        right_frame = tk.Frame(self.root, width=350)
        right_frame.pack(side="right", fill="y", padx=5, pady=5)

        self.video_label = tk.Label(left_frame, bg="black", text="Starting Camera...", fg="white")
        self.video_label.pack(expand=True)

        tk.Label(right_frame, text="Controls", font=("Arial", 14, "bold")).pack(pady=10)

        # FORCE REPLY BUTTON
        self.btn_force = tk.Button(right_frame, text="✋ I'm Done Speaking (Force Reply)", 
                                   font=("Arial", 12, "bold"), bg="#FF5722", fg="white", height=2, 
                                   command=self.on_force_click)
        self.btn_force.pack(fill="x", pady=10)

        tk.Label(right_frame, text="Use this if AI doesn't reply automatically.", font=("Arial", 10), fg="gray").pack(pady=5)

        self.text_area = scrolledtext.ScrolledText(right_frame, height=25, font=("Arial", 11), state="disabled")
        self.text_area.pack(fill="both", expand=True)
        
        self.text_area.tag_config("ai", foreground="blue", font=("Arial", 11, "bold"))
        self.text_area.tag_config("sys", foreground="gray", font=("Arial", 10, "italic"))

    def on_force_click(self):
        self.worker.trigger_force_reply()
        self.log_ui("Sent 'End of Turn' signal...", "sys")

    def log_ui(self, message, tag=None):
        self.text_area.config(state="normal")
        if tag == "ai":
            self.text_area.insert(tk.END, "\n" + message + "\n", tag)
        else:
            self.text_area.insert(tk.END, message + "\n", tag)
        self.text_area.see(tk.END)
        self.text_area.config(state="disabled")

    def check_messages(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                if msg.startswith("AI:"):
                    self.log_ui(msg, "ai")
                elif msg.startswith("[System]") or msg.startswith("[Error]"):
                    self.log_ui(msg, "sys")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_messages)

    def update_video(self):
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = PIL.Image.fromarray(frame_rgb)
            img_ui = img.resize((640, 480))
            imgtk = PIL.ImageTk.PhotoImage(image=img_ui)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

            img.thumbnail([800, 800])
            image_io = io.BytesIO()
            img.save(image_io, format="jpeg", quality=60)
            image_io.seek(0)
            
            b64_data = base64.b64encode(image_io.read()).decode()
            self.worker.send_frame({"mime_type": "image/jpeg", "data": b64_data})

        self.root.after(30, self.update_video)

    def on_close(self):
        self.worker.running = False
        self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceScannerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
