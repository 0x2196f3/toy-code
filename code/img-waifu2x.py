#!/usr/bin/env python3
import sys
import os
import shutil
import subprocess
from pathlib import Path
import time

def clean():
    dirs = [Path("./input"), Path("./output")]
    exts = {".png", ".jpg", ".jpeg"}
let
    time.sleep(0.2)

    for d in dirs:
        if not d.is_dir():
            print(f"Not a dir: {d}")
            continue
        for p in d.iterdir():
            if not p.is_file() or p.suffix.lower() not in exts:
                continue
            tmp = p.with_name(p.stem + "__touch" + p.suffix)
            try:
                p.replace(tmp)
                tmp.replace(p)
            except Exception as e:
                print(f"Could not touch {p}: {e}")

def err(msg):
    print("Error:", msg, file=sys.stderr)
    sys.exit(1)

def clear_dir(path: Path):
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

def main():
    src = Path("./input").resolve()
    dst = Path("./output").resolve()

    if not src.exists() or not src.is_dir():
        err(f"src directory not found: {src}")

    if not dst.exists():
        dst.mkdir(parents=True, exist_ok=True)
    else:
        if any(dst.iterdir()):
            clear_dir(dst)

    waifu = Path("./waifu2x-ncnn-vulkan/waifu2x-ncnn-vulkan.exe")
    magick = Path("./ImageMagick-full/magick.exe")

    if not waifu.exists():
        err(f"{waifu} not found.")
    if not magick.exists():
        err(f"{magick} not found.")

    waifu_cmd = [
        str(waifu),
        "-i", str(src),
        "-o", str(dst),
        "-n", "2",
        "-s", "2",
    ]
    print("Running waifu2x:", " ".join(waifu_cmd))
    try:
        subprocess.check_call(waifu_cmd)
    except subprocess.CalledProcessError as e:
        err(f"waifu2x failed with exit code {e.returncode}")

    pngs = list(dst.glob("*.png"))
    if not pngs:
        err("No PNG files found in dst after waifu2x run.")

    mogrify_cmd = [
        str(magick),
        "mogrify",
        "-format", "jpg",
        "-quality", "90",
        str(dst / "*.png"),
    ]
    print("Running ImageMagick:", " ".join(mogrify_cmd))
    try:
        subprocess.check_call(mogrify_cmd)
    except subprocess.CalledProcessError as e:
        err(f"ImageMagick mogrify failed with exit code {e.returncode}")

    for p in dst.glob("*.png"):
        try:
            p.unlink()
        except Exception as e:
            print(f"Warning: could not remove {p}: {e}", file=sys.stderr)
            
    for p in src.glob("*.png"):
        try:
            p.unlink()
        except Exception as e:
            print(f"Warning: could not remove {p}: {e}", file=sys.stderr)
            
            
    for jpg in dst.glob("*.jpg"):
        name = jpg.name
        if name.startswith("modified_"):
            new_name = name[len("modified_"):]
            target = dst / new_name
            try:
                if target.exists():
                    base = target.stem
                    ext = target.suffix
                    i = 1
                    while True:
                        candidate = dst / f"{base}_{i}{ext}"
                        if not candidate.exists():
                            target = candidate
                            break
                        i += 1
                jpg.rename(target)
            except Exception as e:
                print(f"Warning: could not rename {jpg} -> {target}: {e}", file=sys.stderr)

    print("Done.")
    
    clean()

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    main()
    input("Press Any Key to Exit")
