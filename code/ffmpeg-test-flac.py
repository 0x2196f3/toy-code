import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FFMPEG_PATH = SCRIPT_DIR / "ffmpeg.exe"

SPEED = 16

files = sorted([p for p in SCRIPT_DIR.glob("*.flac") if p.is_file()])

if not files:
    print("No .flac files found in", SCRIPT_DIR)
    sys.exit(0)

if not FFMPEG_PATH.exists():
    print("ffmpeg.exe not found at", FFMPEG_PATH)
    sys.exit(1)

def test_file(ffpath: Path) -> bool:
    cmd = [
        str(FFMPEG_PATH),
        "-hide_banner",
        "-v", "error",
        "-nostdin",
        "-i", str(ffpath),
        "-af",
        None,
        "-f", "wav",
        "NUL"
    ]


    target = float(SPEED)
    factors = []
    while target > 2.0:
        factors.append(2.0)
        target /= 2.0
    if target < 0.5:
        factors.append(0.5)
    else:
        factors.append(round(target, 6))
    af = ",".join(f"atempo={f}" for f in factors)
    cmd[cmd.index(None)] = af

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

ok_count = sum(1 for _,r in results if r)
print(f"\nTested {len(results)} files: {ok_count} OK, {len(results)-ok_count} failed.")
sys.exit(0 if ok_count == len(results) else 2)
