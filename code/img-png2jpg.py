import os
import sys
import shutil
import subprocess
from pathlib import Path
from multiprocessing import Pool, cpu_count
from datetime import datetime
import logging

SRC_ROOT = Path("png")
DST_ROOT = Path("jpg")
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
    "non_png_found": 0,
    "non_png_synced": 0,
    "non_png_skipped": 0,
    "files_deleted": 0,
    "dirs_deleted": 0,
    "convert_errors": 0,
    "copy_errors": 0,
    "delete_errors": 0,
}

def ensure_dir(p: Path):
    if not p.exists():
        try:
            p.mkdir(parents=True, exist_ok=True)
            summary["dirs_created"] += 1
            logging.info(f"Created directory: {p}")
        except Exception as e:
            logging.error(f"Failed to create directory {p}: {e}")

def gather_tasks(src_root: Path, dst_root: Path):
    mogrify_tasks = []
    copy_tasks = []

    for src_dir, _, files in os.walk(src_root):
        src_dir = Path(src_dir)
        rel = src_dir.relative_to(src_root)
        dst_dir = dst_root.joinpath(rel)
        
        ensure_dir(dst_dir)

        current_dir_pngs_to_convert = []

        for fname in files:
            src_file = src_dir / fname
            
            if src_file.suffix.lower() == ".png":
                summary["png_found"] += 1
                dst_jpg = dst_dir / (src_file.stem + ".jpg")
                
                should_convert = False
                if not dst_jpg.exists():
                    should_convert = True
                else:
                    try:
                        if dst_jpg.stat().st_mtime < src_file.stat().st_mtime:
                            should_convert = True
                        else:
                            summary["jpg_skipped_exists"] += 1
                    except OSError:
                        should_convert = True

                if should_convert:
                    current_dir_pngs_to_convert.append(fname)

            else:
                summary["non_png_found"] += 1
                dst_file = dst_dir / fname
                
                should_copy = False
                if not dst_file.exists():
                    should_copy = True
                else:
                    try:
                        if dst_file.stat().st_mtime < src_file.stat().st_mtime:
                            should_copy = True
                        else:
                            summary["non_png_skipped"] += 1
                    except OSError:
                        should_copy = True
                
                if should_copy:
                    copy_tasks.append((src_file, dst_file))

        if current_dir_pngs_to_convert:
            mogrify_tasks.append((str(src_dir), str(dst_dir), current_dir_pngs_to_convert))

    return mogrify_tasks, copy_tasks

def run_mogrify_task(task):
    src_dir, dst_dir, filenames = task
    cmd = [str(MAGICK), "mogrify", "-path", dst_dir, "-format", "jpg", "-quality", QUALITY]
    cmd += [str(Path(src_dir) / fn) for fn in filenames]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    logging.info(f"Starting conversion pool with {workers} workers for {len(expanded)} batches...")
    
    with Pool(processes=workers) as pool:
        for status, count, err in pool.imap_unordered(run_mogrify_task, expanded):
            if status == "ok":
                summary["jpg_converted"] += count
            else:
                summary["convert_errors"] += 1

def process_file_copies(copy_tasks):
    if not copy_tasks:
        return

    logging.info(f"Syncing {len(copy_tasks)} non-PNG files...")
    for src, dst in copy_tasks:
        try:
            shutil.copy2(src, dst)
            summary["non_png_synced"] += 1
            logging.info(f"Synced: {src.name}")
        except Exception as e:
            summary["copy_errors"] += 1
            logging.error(f"Failed to copy {src} to {dst}: {e}")

def mirror_delete_extras(src_root: Path, dst_root: Path):
    logging.info("Starting cleanup of extra files in destination...")
    
    for dst_dir, dirs, files in os.walk(dst_root, topdown=False):
        dst_dir_path = Path(dst_dir)
        try:
            rel = dst_dir_path.relative_to(dst_root)
            src_dir_path = src_root.joinpath(rel)
        except ValueError:
            continue

        for fname in files:
            dst_file = dst_dir_path.joinpath(fname)
            
            should_delete = False
            
            if dst_file.suffix.lower() == ".jpg":
                src_png = src_dir_path.joinpath(dst_file.stem + ".png")
                src_exact_jpg = src_dir_path.joinpath(dst_file.name)
                
                if not src_png.exists() and not src_exact_jpg.exists():
                    should_delete = True
            else:
                src_equiv = src_dir_path.joinpath(fname)
                if not src_equiv.exists():
                    should_delete = True

            if should_delete:
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
                    logging.info(f"Deleted empty directory: {dst_dir_path}")
                except Exception as e:
                    summary["delete_errors"] += 1
                    logging.error(f"Failed to delete directory {dst_dir_path}: {e}")

def main():
    start = datetime.now()
    logging.info("=== Sync started ===")
    
    convert_tasks, copy_tasks = gather_tasks(SRC_ROOT, DST_ROOT)
    
    logging.info(f"Tasks gathered: {len(convert_tasks)} conversion batches, {len(copy_tasks)} file copies.")

    convert_parallel(convert_tasks)

    process_file_copies(copy_tasks)

    mirror_delete_extras(SRC_ROOT, DST_ROOT)

    end = datetime.now()
    duration = (end - start).total_seconds()
    logging.info("=== Sync finished ===")

    summary_lines = [
        f"Start time: {start.isoformat()}",
        f"End time:   {end.isoformat()}",
        f"Duration:   {duration:.2f} seconds",
        "-" * 30,
        f"Directories created: {summary['dirs_created']}",
        "-" * 30,
        f"PNGs found in source: {summary['png_found']}",
        f"JPEGs converted/updated: {summary['jpg_converted']}",
        f"JPEGs skipped (up to date): {summary['jpg_skipped_exists']}",
        "-" * 30,
        f"Non-PNGs found: {summary['non_png_found']}",
        f"Non-PNGs synced/updated: {summary['non_png_synced']}",
        f"Non-PNGs skipped (up to date): {summary['non_png_skipped']}",
        "-" * 30,
        f"Files deleted in dest: {summary['files_deleted']}",
        f"Directories deleted in dest: {summary['dirs_deleted']}",
        "-" * 30,
        f"Conversion errors: {summary['convert_errors']}",
        f"Copy errors: {summary['copy_errors']}",
        f"Deletion errors: {summary['delete_errors']}",
    ]
    logging.info("Summary:\n" + "\n".join(summary_lines))
    print("\n".join(summary_lines))

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    main()
    input("Press any key to exit")
