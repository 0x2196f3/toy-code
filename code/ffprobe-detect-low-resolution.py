from pathlib import Path
import subprocess
import json
from datetime import timedelta

ROOT = Path(".")
FFPROBE = ROOT / "ffprobe.exe"

MAX_PIXEL_COUNT = 1920 * 1000
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".wmv"}


def format_size(size_bytes):
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024


def format_duration(seconds):
    if seconds is None:
        return "unknown"

    seconds = int(round(seconds))
    return str(timedelta(seconds=seconds))


for file_path in ROOT.rglob("*"):
    if not file_path.is_file():
        continue

    if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
        continue

    command = [
        str(FFPROBE),
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration",
        "-of", "json",
        str(file_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        formats = data.get("format", {})

        if not streams:
            print(f"Could not find video stream: {file_path}")
            continue

        width = streams[0].get("width")
        height = streams[0].get("height")

        if not width or not height:
            print(f"Could not determine resolution: {file_path}")
            continue

        pixel_count = width * height

        if pixel_count < MAX_PIXEL_COUNT:
            duration = formats.get("duration")
            duration_seconds = float(duration) if duration else None

            file_size = file_path.stat().st_size

            print(
                f"{file_path}\n"
                f"  Resolution: {width}x{height} "
                f"({pixel_count:,} pixels)\n"
                f"  Size:       {format_size(file_size)}\n"
                f"  Duration:   {format_duration(duration_seconds)}\n"
            )

    except subprocess.CalledProcessError:
        print(f"ffprobe failed: {file_path}")
    except json.JSONDecodeError:
        print(f"Invalid ffprobe output: {file_path}")
    except (OSError, ValueError) as error:
        print(f"Error processing {file_path}: {error}")
