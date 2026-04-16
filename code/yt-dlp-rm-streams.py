#!/usr/bin/env python3
import subprocess
import shutil
import sys
import logging
import re
from pathlib import Path
from typing import List

YTDLP = ".\\yt-dlp.exe"

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def get_video_ids(url: str) -> List[str]:
    logger.info("Running yt-dlp to get IDs for URL: %s", url)
    proc = subprocess.Popen(
        [YTDLP, "--flat-playlist", "--get-id", url],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=1, text=True, universal_newlines=True,
    )
    ids = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if line:
            logger.debug("yt-dlp output: %s", line)
            ids.append(line)
            print(line)
    ret = proc.wait()
    if ret != 0:
        logger.error("yt-dlp exited with code %d", ret)
        raise RuntimeError(f"yt-dlp failed with exit code {ret}")
    logger.info("Collected %d ids", len(ids))
    return ids

def compile_id_regex_chunks(ids: List[str], chunk_size: int = 1000):
    escaped = [re.escape(i) for i in ids]
    for i in range(0, len(escaped), chunk_size):
        chunk = escaped[i:i+chunk_size]
        pattern = "(" + "|".join(chunk) + ")"
        yield re.compile(pattern)

def move_files_for_ids(ids: List[str], target_dir: Path):
    cwd = Path.cwd()
    target_dir.mkdir(exist_ok=True)
    files = [p for p in cwd.iterdir() if p.is_file()]
    logger.info("Scanning %d files against %d ids", len(files), len(ids))
    regexes = list(compile_id_regex_chunks(ids, chunk_size=1000))
    moved = []
    for p in files:
        name = p.name
        matched = False
        for rx in regexes:
            m = rx.search(name)
            if m:
                matched = True
                break
        if matched:
            dest = target_dir / name
            if dest.exists():
                stem, suf = p.stem, p.suffix
                i = 1
                while True:
                    new_name = f"{stem}.{i}{suf}"
                    dest = target_dir / new_name
                    if not dest.exists():
                        break
                    i += 1
            logger.info("Moving %s -> %s", p.name, dest)
            shutil.move(str(p), str(dest))
            moved.append((p.name, str(dest)))
    return moved

def main(id: str = None):
    if id is None:
        if len(sys.argv) < 2:
            logger.error("No id provided and no URL argument")
            sys.exit(1)
        url = sys.argv[1]
    else:
        url = f"https://www.youtube.com/@{id}/streams"
    try:
        ids = get_video_ids(url)
    except Exception as e:
        logger.exception("Error getting video ids: %s", e)
        sys.exit(2)
    if not ids:
        logger.info("No video ids found.")
        sys.exit(0)
    target = Path("./temp")
    moved = move_files_for_ids(ids, target)
    logger.info("Found %d ids. Moved %d files to %s.", len(ids), len(moved), target.resolve())
    for src, dst in moved:
        print(f"{src} -> {dst}")

if __name__ == "__main__":
    main(id="")
