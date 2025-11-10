#!/usr/bin/env python3
"""
Move all .mp4 files in the current directory whose video resolution is portrait (width < height)
to ./to_remove directory.
Requires ffprobe (part of ffmpeg) available as ./ffprobe.exe or ffprobe on PATH.
"""

import json
import os
import subprocess
import sys
import shutil

FFPROBE_CANDIDATES = ["./ffprobe.exe", "ffprobe"]

def find_ffprobe():
    for cmd in FFPROBE_CANDIDATES:
        try:
            subprocess.run([cmd, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return cmd
        except Exception:
            continue
    return None

def get_video_stream_resolution(ffprobe_cmd, filepath):
    # Use ffprobe to get stream info as json
    args = [
        ffprobe_cmd,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        filepath
    ]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=True)
        info = json.loads(proc.stdout)
        streams = info.get("streams") or []
        if not streams:
            return None, None
        stream = streams[0]
        return int(stream.get("width", 0)), int(stream.get("height", 0))
    except subprocess.CalledProcessError as e:
        print(f"ffprobe failed for {filepath}: {e}", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"Could not parse ffprobe output for {filepath}", file=sys.stderr)
    except Exception as e:
        print(f"Error getting resolution for {filepath}: {e}", file=sys.stderr)
    return None, None

def main():
    ffprobe_cmd = find_ffprobe()
    if not ffprobe_cmd:
        print("ffprobe not found. Make sure ./ffprobe.exe exists or ffprobe is on PATH.", file=sys.stderr)
        sys.exit(1)

    cwd = os.getcwd()
    target_dir = os.path.join(cwd, "to_remove")
    os.makedirs(target_dir, exist_ok=True)

    moved = []
    skipped = []
    for name in os.listdir(cwd):
        if not name.lower().endswith(".mp4"):
            continue
        path = os.path.join(cwd, name)
        if not os.path.isfile(path):
            continue
        width, height = get_video_stream_resolution(ffprobe_cmd, path)
        if width is None or height is None or width == 0 or height == 0:
            skipped.append((name, "no-resolution"))
            continue
        if width < height:
            dest = os.path.join(target_dir, name)
            # If a file with the same name exists in target, add a suffix to avoid overwrite
            if os.path.exists(dest):
                base, ext = os.path.splitext(name)
                i = 1
                while True:
                    new_name = f"{base}_{i}{ext}"
                    dest = os.path.join(target_dir, new_name)
                    if not os.path.exists(dest):
                        break
                    i += 1
            try:
                shutil.move(path, dest)
                moved.append((name, width, height, os.path.basename(dest)))
                print(f"Moved {name} -> {os.path.relpath(dest, cwd)} ({width}x{height})")
            except Exception as e:
                skipped.append((name, f"move-failed: {e}"))
        else:
            skipped.append((name, f"{width}x{height}"))
    print("\nSummary:")
    print(f"Moved: {len(moved)}")
    for m in moved:
        print(f" - {m[0]} -> {m[3]} ({m[1]}x{m[2]})")
    print(f"Skipped: {len(skipped)}")
    for s in skipped:
        print(f" - {s[0]} ({s[1]})")

if __name__ == "__main__":
    main()
