#!/usr/bin/env python3
# test_flac_playable.py
# Usage: python test_flac_playable.py
# Requires ffmpeg.exe in the same folder or adjust FFMPEG_PATH.

import subprocess
import sys
from pathlib import Path

# Path to ffmpeg.exe (same dir as script by default)
SCRIPT_DIR = Path(__file__).resolve().parent
FFMPEG_PATH = SCRIPT_DIR / "ffmpeg.exe"

# Fast playback speed factor (e.g., 16 = 16x faster)
SPEED = 16

# Files to test: all .flac in current directory
files = sorted([p for p in SCRIPT_DIR.glob("*.flac") if p.is_file()])

if not files:
    print("No .flac files found in", SCRIPT_DIR)
    sys.exit(0)

if not FFMPEG_PATH.exists():
    print("ffmpeg.exe not found at", FFMPEG_PATH)
    sys.exit(1)

def test_file(ffpath: Path) -> bool:
    """
    Returns True if ffmpeg reads the whole file and exits with 0.
    Uses atempo for audio speed (supports 0.5-2.0; chain if needed) for real-time output,
    but for speed-reading we can use setpts on a null output so ffmpeg decodes quickly.
    Approach: decode audio and write to null muxer (pcm_s16le to NUL) while speeding pts for video filter trick.
    """
    # Use -vn in case file has no video. Use '-f null -' to drop output; but audio-only to null requires an audio sink.
    # We'll force ffmpeg to decode audio and write to the null device via wav and NUL file.
    # On Windows NUL is a special filename; use 'NUL' as output.
    cmd = [
        str(FFMPEG_PATH),
        "-hide_banner",
        "-v", "error",
        "-nostdin",
        "-i", str(ffpath),
        # accelerate by setting audio pts via asetpts (playback speed multiplier):
        # asetpts='PTS/FACTOR' alone is a filter for audio timestamps, but better to use atempo when writing audio out.
        # However atempo only supports up to 2x per filter, so chain it if SPEED>2.
        # Simpler: use "-af" with chained atempo filters computed below, then output to NUL as WAV.
        "-af",
        None,  # placeholder for af filter string
        "-f", "wav",
        "NUL"
    ]

    # Build atempo chain for desired SPEED. atempo changes playback speed by factor; for fast playback >2, chain multiple atempo.
    # We'll create factors that multiply to SPEED (approx) using powers of 2 and remaining factor between 0.5-2.0.
    target = float(SPEED)
    factors = []
    # reduce target by powers of 2 until <=2
    while target > 2.0:
        factors.append(2.0)
        target /= 2.0
    # now target <= 2.0
    if target < 0.5:
        # if too small, merge into last factor (rare for tiny SPEED values)
        factors.append(0.5)
    else:
        factors.append(round(target, 6))
    af = ",".join(f"atempo={f}" for f in factors)
    cmd[cmd.index(None)] = af

    # Run ffmpeg and capture return code
    try:
        proc = subprocess.run(cmd, timeout=300, check=False)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout reading {ffpath}")
        return False
    except Exception as e:
        print(f"Error running ffmpeg on {ffpath}: {e}")
        return False

results = []
for f in files:
    ok = test_file(f)
    results.append((f.name, ok))
    print(f"{f.name}: {'OK' if ok else 'FAIL'}")

# Summary
ok_count = sum(1 for _,r in results if r)
print(f"\nTested {len(results)} files: {ok_count} OK, {len(results)-ok_count} failed.")
sys.exit(0 if ok_count == len(results) else 2)
