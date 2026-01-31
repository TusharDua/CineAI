import ffmpeg
import os
import sys

def split_video_by_second(video_path: str, output_dir: str, fps: int = 1):
    print("▶ Video path:", video_path)

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"❌ File not found: {video_path}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        (
            ffmpeg
            .input(video_path)
            .filter("fps", fps=fps)
            .output(
                os.path.join(output_dir, "frame_%05d.jpg"),
                start_number=0
            )
            .overwrite_output()
            .run()   # ❗ DO NOT use quiet=True while debugging
        )

        print("✅ Video split completed")

    except ffmpeg.Error as e:
        print("❌ FFmpeg failed")
        print("STDERR ↓↓↓")
        print(e.stderr.decode())
        sys.exit(1)


# ⚠️ MAKE SURE THIS IS A REAL VIDEO FILE
split_video_by_second(
    video_path="/Users/prasad/Documents/CINEAI/backend/samplevideo.mp4",  # <-- CHANGE THIS
    output_dir="frames"
)