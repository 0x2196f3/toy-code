#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

VIDEO_EXTS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.m4v', '.mts', '.ts'}

def get_duration(path: Path) -> float:
    cmd = ["./ffprobe.exe",
           "-v", "error",
           "-select_streams", "v:0",
           "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1",
           str(path)]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return float(out.strip()) if out.strip() else 0.0
    except (subprocess.CalledProcessError, ValueError):
        return 0.0

def format_duration(total_seconds: float) -> str:
    hrs = int(total_seconds // 3600)
    mins = int((total_seconds % 3600) // 60)
    secs = total_seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"

def main():
    root = Path('.')
    if not root.exists():
        print("Directory '.' not found.", file=sys.stderr)
        sys.exit(1)

    total = 0.0
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS:
            total += get_duration(p)

    print(format_duration(total))

if __name__ == "__main__":
    main()
