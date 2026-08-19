import os
import subprocess
import json
from datetime import datetime

MIN_AUDIO_STREAM_COUNT = 2
RESULT_FILE = "./result.json"


def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")


def print_video_files_with_multiple_audio_streams(root="."):
    video_files = []
    log(f"Scanning for video files under: {os.path.abspath(root)}")

    for dirpath, _, filenames in os.walk(root):
        log(f"Checking directory: {dirpath}")
        for name in filenames:
            if name.lower().endswith((".mkv", ".mp4")):
                full_path = os.path.join(dirpath, name)
                video_files.append(full_path)
                log(f"Found video file: {full_path}")

    video_files.sort()
    log(f"Total video files found: {len(video_files)}")

    results = []
    total_processed = 0
    total_matches = 0
    errors = []

    for path in video_files:
        total_processed += 1
        log(f"Processing [{total_processed}/{len(video_files)}]: {path}")

        try:
            result = subprocess.run(
                ["ffmpeg", "-i", path],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )

            audio_streams = [line for line in result.stderr.splitlines() if "Audio:" in line]
            stream_count = len(audio_streams)

            log(f"Audio streams found: {stream_count}")

            item = {
                "path": path,
                "audio_stream_count": stream_count,
                "has_multiple_audio_streams": stream_count >= MIN_AUDIO_STREAM_COUNT,
            }

            if stream_count >= MIN_AUDIO_STREAM_COUNT:
                total_matches += 1
                print(f"{path} has {stream_count} audio streams.")

            results.append(item)

        except Exception as e:
            error_msg = f"Error processing file {path}: {e}"
            log(error_msg)
            errors.append({"path": path, "error": str(e)})

    summary = {
        "scan_root": os.path.abspath(root),
        "min_audio_stream_count": MIN_AUDIO_STREAM_COUNT,
        "total_video_files_found": len(video_files),
        "total_processed": total_processed,
        "total_matches": total_matches,
        "generated_at": datetime.now().isoformat(),
        "results": results,
        "errors": errors,
    }

    log(f"Writing results to: {os.path.abspath(RESULT_FILE)}")
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    log("Done.")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print_video_files_with_multiple_audio_streams(".")
