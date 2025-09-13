#!/usr/bin/env python3
import subprocess
import glob
import os
import shutil

FFPROBE = os.path.join('.', 'ffprobe.exe')  # path to ffprobe.exe
SEARCH_GLOB = os.path.join("./youtube", '*.mp4')

def has_audio(path):
    cmd = [
        FFPROBE,
        '-v', 'error',
        '-select_streams', 'a',
        '-show_entries', 'stream=codec_type',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return bool(proc.stdout.strip())
    except FileNotFoundError:
        raise RuntimeError(f"ffprobe not found at {FFPROBE}")

def main():
    files = sorted(glob.glob(SEARCH_GLOB))
    if not files:
        print("No MP4 files found.")
        return

    no_audio = []
    for f in files:
        try:
            if not has_audio(f):
                no_audio.append(f)
        except RuntimeError as e:
            print(e)
            return

    if not no_audio:
        print("All files contain audio.")
        return

    print("MP4 files without audio:")
    for f in no_audio:
        print(f)

    ans = input("Move these files to their parent folder? Type Y to confirm: ").strip()
    if ans != 'Y':
        print("Cancelled.")
        return

    for src in no_audio:
        parent = os.path.dirname(os.path.dirname(src))  # parent of ./aaa/bbb is ./aaa
        dest = os.path.join(parent, os.path.basename(src))
        # if destination exists, append a suffix to avoid overwrite
        if os.path.exists(dest):
            base, ext = os.path.splitext(os.path.basename(src))
            i = 1
            while True:
                candidate = f"{base}.{i}{ext}"
                dest = os.path.join(parent, candidate)
                if not os.path.exists(dest):
                    break
                i += 1
        try:
            shutil.move(src, dest)
            print(f"Moved: {src} -> {dest}")
        except Exception as e:
            print(f"Failed to move {src}: {e}")

if __name__ == '__main__':
    main()
