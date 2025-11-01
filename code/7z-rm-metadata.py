"""
normalize_archives.py

Usage:
  python normalize_archives.py [--path PATH] [--dry-run]

- --path PATH : directory to scan for .zip and .7z (default: current dir)
- --dry-run : show actions without replacing archives
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import pywintypes
    import win32file
    import win32con
    WIN32_AVAILABLE = True
except Exception:
    WIN32_AVAILABLE = False

DEFAULT_TIMESTAMP = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

def find_7z_exe():
    candidates = [
        Path(r"C:\Program Files\7-Zip\7z.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
        Path(r"C:\Program Files\7-Zip\7za.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7za.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return "7z.exe"

def run(cmd, cwd=None):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    return proc.stdout

def set_file_times(path: Path, ts: datetime):
    
    epoch_seconds = ts.timestamp()
    os.utime(path, (epoch_seconds, epoch_seconds))
    if WIN32_AVAILABLE and os.name == "nt":
        wintime = pywintypes.Time(ts)
        fh = win32file.CreateFile(
            str(path),
            win32con.GENERIC_WRITE,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
            None,
            win32con.OPEN_EXISTING,
            0,
            None
        )
        try:
            win32file.SetFileTime(fh, wintime, wintime, wintime)
        finally:
            fh.Close()

def normalize_directory_timestamps(root: Path, timestamp: datetime):
    for p in root.rglob("*"):
        if p.is_file():
            set_file_times(p, timestamp)
        elif p.is_dir():
            set_file_times(p, timestamp)

def process_archive(archive_path: Path, sevenz_exe: str, dry_run=False):
    ext = archive_path.suffix.lower()
    if ext not in (".zip", ".7z"):
        return

    print(f"Processing: {archive_path}")
    with tempfile.TemporaryDirectory() as tmpd:
        tmpd_path = Path(tmpd)
        cmd_extract = [sevenz_exe, "x", str(archive_path), f"-o{str(tmpd_path)}", "-y"]
        run(cmd_extract)
        normalize_directory_timestamps(tmpd_path, DEFAULT_TIMESTAMP)

        temp_archive = archive_path.with_suffix(archive_path.suffix + ".tmp")
        if ext == ".zip":
            cmd_add = [sevenz_exe, "a", "-tzip", f"-mx=9", str(temp_archive), str(tmpd_path) + os.sep + "*"]
        else:  # .7z
            cmd_add = [sevenz_exe, "a", "-t7z", f"-mx=9", str(temp_archive), str(tmpd_path) + os.sep + "*"]

        run(cmd_add)

        if dry_run:
            print(f"[dry-run] would replace {archive_path} with {temp_archive}")
            temp_archive.unlink(missing_ok=True)
        else:
            backup = archive_path.with_suffix(archive_path.suffix + ".bak")
            try:
                archive_path.replace(backup)
                temp_archive.replace(archive_path)
                backup.unlink(missing_ok=True)
            except Exception as e:
                if archive_path.exists():
                    temp_archive.unlink(missing_ok=True)
                else:
                    if backup.exists():
                        backup.replace(archive_path)
                raise

def main():
    parser = argparse.ArgumentParser(description="Normalize timestamps inside .zip and .7z archives and recompress with max compression.")
    parser.add_argument("--path", "-p", default=".", help="Directory path to scan")
    parser.add_argument("--dry-run", action="store_true", help="Show actions but do not replace archives")
    args = parser.parse_args()

    base = Path(args.path).resolve()
    if not base.exists():
        print("Path not found:", base)
        sys.exit(1)

    sevenz = find_7z_exe()
    print("Using 7z executable:", sevenz)

    for p in base.rglob("*"):
        if p.suffix.lower() in (".zip", ".7z"):
            try:
                process_archive(p, sevenz, dry_run=args.dry_run)
            except Exception as e:
                print(f"Failed processing {p}: {e}")

if __name__ == "__main__":
    main()
