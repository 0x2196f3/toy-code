import os
import shutil
import subprocess
from pathlib import Path
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging

SRC_ROOT = Path("./png")
DST_ROOT = Path("./jpg")
MAGICK = Path("./ImageMagick-full/magick.exe")
QUALITY = "90"

WORKERS = max(1, cpu_count() - 1)
MAX_FILES_PER_JOB = 200
COPY_THREADS = max(4, cpu_count())

EXCLUDE_FILENAMES = {
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
    "ehthumbs.db",
}

EXCLUDE_EXTENSIONS = {
    ".exe",
    ".py",
    ".pyc",
    ".bat",
    ".sh",
    ".txt",
    ".md",
    ".log",
    ".tmp"
}

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
    "files_ignored_src": 0,
    "files_deleted": 0,
    "dirs_deleted": 0,
    "convert_errors": 0,
    "copy_errors": 0,
    "delete_errors": 0,
}

def is_excluded(name):
    nl = name.lower()
    return nl in EXCLUDE_FILENAMES or os.path.splitext(nl)[1] in EXCLUDE_EXTENSIONS

def get_index(root_dir):
    idx, dirs = {}, set()
    if not os.path.exists(root_dir): return idx, dirs
    stack = [("", root_dir)]
    while stack:
        rel_dir, current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    try:
                        rel_path = f"{rel_dir}/{entry.name}" if rel_dir else entry.name
                        if entry.is_dir(follow_symlinks=False):
                            dirs.add(rel_path)
                            stack.append((rel_path, entry.path))
                        else:
                            idx[rel_path] = entry.stat(follow_symlinks=False).st_mtime
                    except OSError: pass
        except OSError: pass
    return idx, dirs

def run_mogrify(args):
    src_dir, dst_dir, files = args
    cmd = [MAGICK, "mogrify", "-path", dst_dir, "-format", "jpg", "-quality", QUALITY]
    cmd.extend([os.path.join(src_dir, f) for f in files])
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "ok", len(files), src_dir
    except subprocess.CalledProcessError as e:
        return "err", 0, e.stderr.decode(errors="ignore").strip()

def copy_file(rel):
    src, dst = os.path.join(SRC_ROOT, os.path.normpath(rel)), os.path.join(DST_ROOT, os.path.normpath(rel))
    try:
        shutil.copy2(src, dst)
        return "ok_copy", rel
    except Exception as e:
        return "err_copy", f"Failed to copy {src} to {dst}: {e}"

def delete_file(rel):
    p = os.path.join(DST_ROOT, os.path.normpath(rel))
    try:
        os.remove(p)
        return "ok_del", p
    except Exception as e:
        return "err_del", f"Delete failed: {p}: {e}"

def main():
    start = datetime.now()
    logging.info("=== Sync started ===")
    
    logging.info("Indexing source tree into memory...")
    src_idx, src_dirs = get_index(SRC_ROOT)
    logging.info(f"Source entries: {len(src_idx)}")
    
    logging.info("Indexing destination tree into memory...")
    dst_idx, dst_dirs = get_index(DST_ROOT)
    logging.info(f"Destination entries: {len(dst_idx)}")

    if not os.path.exists(DST_ROOT):
        os.makedirs(DST_ROOT, exist_ok=True)
        summary["dirs_created"] += 1
        logging.info(f"Created directory: {DST_ROOT}")

    for d in src_dirs:
        p = os.path.join(DST_ROOT, os.path.normpath(d))
        if not os.path.exists(p):
            os.makedirs(p, exist_ok=True)
            summary["dirs_created"] += 1
            logging.info(f"Created directory: {p}")

    mogrify_tasks, copy_tasks, delete_targets, mogrify_jobs = {}, [], [], []
    
    for rel, mtime in src_idx.items():
        name = os.path.basename(rel)
        if is_excluded(name):
            summary["files_ignored_src"] += 1
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext == ".png":
            summary["png_found"] += 1
            dst_rel = os.path.splitext(rel)[0] + ".jpg"
            if dst_rel not in dst_idx or dst_idx[dst_rel] < mtime:
                mogrify_tasks.setdefault(os.path.dirname(rel), []).append(name)
            else:
                summary["jpg_skipped_exists"] += 1
        else:
            summary["non_png_found"] += 1
            if rel not in dst_idx or dst_idx[rel] < mtime:
                copy_tasks.append(rel)
            else:
                summary["non_png_skipped"] += 1

    for rel in dst_idx:
        name = os.path.basename(rel)
        if is_excluded(name):
            delete_targets.append(rel)
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext == ".jpg":
            if os.path.splitext(rel)[0] + ".png" not in src_idx and rel not in src_idx:
                delete_targets.append(rel)
        elif rel not in src_idx:
            delete_targets.append(rel)

    for d, files in mogrify_tasks.items():
        src_d = os.path.join(SRC_ROOT, os.path.normpath(d)) if d else SRC_ROOT
        dst_d = os.path.join(DST_ROOT, os.path.normpath(d)) if d else DST_ROOT
        for i in range(0, len(files), MAX_FILES_PER_JOB):
            mogrify_jobs.append((src_d, dst_d, files[i:i+MAX_FILES_PER_JOB]))

    logging.info(f"Tasks gathered: {len(mogrify_jobs)} conversion batches, {len(copy_tasks)} file copies.")

    if mogrify_jobs:
        workers = min(WORKERS, len(mogrify_jobs))
        logging.info(f"Starting conversion pool with {workers} workers for {len(mogrify_jobs)} batches...")
        with Pool(processes=workers) as pool:
            for status, count, msg in pool.imap_unordered(run_mogrify, mogrify_jobs):
                if status == "ok":
                    summary["jpg_converted"] += count
                    logging.info(f"Converted {count} files in {msg}")
                else:
                    summary["convert_errors"] += 1
                    logging.error(f"Error converting: {msg}")

    if copy_tasks:
        logging.info(f"Syncing {len(copy_tasks)} non-PNG files with {COPY_THREADS} threads...")
        with ThreadPoolExecutor(max_workers=COPY_THREADS) as ex:
            for status, msg in ex.map(copy_file, copy_tasks):
                if status == "ok_copy":
                    summary["non_png_synced"] += 1
                    logging.info(f"Synced: {os.path.basename(msg)}")
                else:
                    summary["copy_errors"] += 1
                    logging.error(msg)

    if delete_targets:
        logging.info(f"Deleting {len(delete_targets)} extra files from destination...")
        with ThreadPoolExecutor(max_workers=COPY_THREADS) as ex:
            for status, msg in ex.map(delete_file, delete_targets):
                if status == "ok_del":
                    summary["files_deleted"] += 1
                    logging.info(f"Deleted extra file: {msg}")
                else:
                    summary["delete_errors"] += 1
                    logging.error(msg)

    for d in sorted(list(dst_dirs), key=lambda x: x.count("/"), reverse=True):
        if d not in src_dirs:
            p = os.path.join(DST_ROOT, os.path.normpath(d))
            try:
                if not os.listdir(p):
                    os.rmdir(p)
                    summary["dirs_deleted"] += 1
                    logging.info(f"Deleted empty directory: {p}")
            except Exception as e:
                summary["delete_errors"] += 1
                logging.error(f"Failed to delete directory {p}: {e}")

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
        f"Source files ignored (Excluded): {summary['files_ignored_src']}",
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
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
    input("Press any key to exit")