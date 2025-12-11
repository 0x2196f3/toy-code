import os
import shutil
import subprocess
from pathlib import Path
from multiprocessing import Pool, cpu_count
from datetime import datetime
import logging

SRC_ROOT = Path("./png")
DST_ROOT = Path("./jpg")
MAGICK = Path("./ImageMagick-full/magick.exe")
QUALITY = "90" 

WORKERS = max(1, cpu_count() - 1) 

MAX_FILES_PER_JOB = 200

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ],
)

summary = {
    "dirs_created": 0,
    "png_found": 0,
    "jpg_converted": 0,
    "jpg_skipped_exists": 0,
    "files_deleted": 0,
    "dirs_deleted": 0,
    "convert_errors": 0,
    "delete_errors": 0,
}

def ensure_dir(p: Path):
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
        summary["dirs_created"] += 1
        logging.info(f"Created directory: {p}")

def gather_tasks(src_root: Path, dst_root: Path):
    tasks = []
    for src_dir, _, files in os.walk(src_root):
        src_dir = Path(src_dir)
        rel = src_dir.relative_to(src_root)
        dst_dir = dst_root.joinpath(rel)
        ensure_dir(dst_dir)

        pngs = [f for f in src_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"]
        if not pngs:
            continue

        summary["png_found"] += len(pngs)

        to_convert = []
        for p in pngs:
            target = dst_dir.joinpath(p.stem + ".jpg")
            if not target.exists():
                to_convert.append(p.name)
            else:
                try:
                    png_mtime = p.stat().st_mtime
                    jpg_mtime = target.stat().st_mtime
                except Exception:
                    to_convert.append(p.name)
                else:
                    if jpg_mtime < png_mtime:
                        to_convert.append(p.name)
                    else:
                        summary["jpg_skipped_exists"] += 1

        if to_convert:
            tasks.append((str(src_dir), str(dst_dir), to_convert))
    return tasks

def run_mogrify_task(task):
    src_dir, dst_dir, filenames = task
    cmd = [str(MAGICK), "mogrify", "-path", dst_dir, "-format", "jpg", "-quality", QUALITY]
    cmd += [str(Path(src_dir) / fn) for fn in filenames]
    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        converted = len(filenames)
        logging.info(f"Converted {converted} files in {src_dir}")
        return ("ok", converted, None)
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode(errors="ignore")
        logging.error(f"Error converting in {src_dir}: {err.strip()}")
        return ("err", 0, err)

def convert_parallel(tasks):
    if not tasks:
        return
    expanded = []
    for src_dir, dst_dir, filenames in tasks:
        for i in range(0, len(filenames), MAX_FILES_PER_JOB):
            chunk = filenames[i:i + MAX_FILES_PER_JOB]
            expanded.append((src_dir, dst_dir, chunk))

    workers = min(WORKERS, len(expanded))
    with Pool(processes=workers) as pool:
        for status, count, err in pool.imap_unordered(run_mogrify_task, expanded):
            if status == "ok":
                summary["jpg_converted"] += count
            else:
                summary["convert_errors"] += 1

def mirror_delete_extras(src_root: Path, dst_root: Path):
    for dst_dir, dirs, files in os.walk(dst_root, topdown=False):
        dst_dir_path = Path(dst_dir)
        rel = dst_dir_path.relative_to(dst_root)
        src_dir_path = src_root.joinpath(rel)

        for fname in files:
            dst_file = dst_dir_path.joinpath(fname)
            if dst_file.suffix.lower() == ".jpg":
                src_png = src_dir_path.joinpath(dst_file.stem + ".png")
                if not src_png.exists():
                    try:
                        dst_file.unlink()
                        summary["files_deleted"] += 1
                        logging.info(f"Deleted file (no source PNG): {dst_file}")
                    except Exception as e:
                        summary["delete_errors"] += 1
                        logging.error(f"Failed to delete file {dst_file}: {e}")
            else:
                src_equiv = src_dir_path.joinpath(fname)
                if not src_equiv.exists():
                    try:
                        dst_file.unlink()
                        summary["files_deleted"] += 1
                        logging.info(f"Deleted extra file: {dst_file}")
                    except Exception as e:
                        summary["delete_errors"] += 1
                        logging.error(f"Failed to delete file {dst_file}: {e}")

        if not any(dst_dir_path.iterdir()):
            if not src_dir_path.exists():
                try:
                    dst_dir_path.rmdir()
                    summary["dirs_deleted"] += 1
                    logging.info(f"Deleted empty directory not in source: {dst_dir_path}")
                except Exception as e:
                    summary["delete_errors"] += 1
                    logging.error(f"Failed to delete directory {dst_dir_path}: {e}")

def create_missing_dirs_from_src(src_root: Path, dst_root: Path):
    for src_dir, _, _ in os.walk(src_root):
        src_dir = Path(src_dir)
        rel = src_dir.relative_to(src_root)
        dst_dir = dst_root.joinpath(rel)
        ensure_dir(dst_dir)

def main():
    start = datetime.now()
    logging.info("=== Sync started ===")
    create_missing_dirs_from_src(SRC_ROOT, DST_ROOT)

    tasks = gather_tasks(SRC_ROOT, DST_ROOT)
    logging.info(f"Tasks gathered: {len(tasks)} directories with pending conversions")
    convert_parallel(tasks)

    mirror_delete_extras(SRC_ROOT, DST_ROOT)

    end = datetime.now()
    duration = (end - start).total_seconds()
    logging.info("=== Sync finished ===")

    summary_lines = [
        f"Start time: {start.isoformat()}",
        f"End time:   {end.isoformat()}",
        f"Duration:   {duration:.2f} seconds",
        f"Directories created: {summary['dirs_created']}",
        f"PNG files found in source: {summary['png_found']}",
        f"JPEGs converted (created): {summary['jpg_converted']}",
        f"JPEGs skipped (already existed): {summary['jpg_skipped_exists']}",
        f"Files deleted in destination: {summary['files_deleted']}",
        f"Directories deleted in destination: {summary['dirs_deleted']}",
        f"Conversion errors: {summary['convert_errors']}",
        f"Deletion errors: {summary['delete_errors']}",
    ]
    logging.info("Summary:\n" + "\n".join(summary_lines))
    print("\n".join(summary_lines))

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    main()
    input("Press any key to exit")
    main()
    input("Press any key to exit")
