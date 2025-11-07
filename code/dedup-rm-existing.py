import os
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import shutil

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

MD5_CHUNK = 1024 * 1024

def calculate_md5(path, chunk_size=MD5_CHUNK):
    try:
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logging.error("Failed to hash %s: %s", path, e)
        return None

def build_files_map(directory, workers=8):
    files_map = {}
    sizes_set = set()
    paths = []
    for root, _, files in os.walk(directory):
        for name in files:
            p = os.path.join(root, name)
            try:
                sz = os.path.getsize(p)
            except Exception as e:
                logging.warning("Skipping size read for %s: %s", p, e)
                continue
            paths.append((p, sz))
            sizes_set.add(sz)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(calculate_md5, p): (p, sz) for p, sz in paths}
        for fut in as_completed(futs):
            p, sz = futs[fut]
            md5 = fut.result()
            if md5:
                files_map.setdefault((sz, md5), []).append(p)
    return files_map, sizes_set

def delete_matching_files(dir_a, dir_b, dry_run=True, move_to_trash=False, trash_dir=None, workers=4):
    logging.info("Scanning directory B: %s", dir_b)
    b_map, b_sizes = build_files_map(dir_b, workers=workers)
    logging.info("Scanning and comparing directory A: %s", dir_a)

    candidates = []
    for root, _, files in os.walk(dir_a):
        for name in files:
            p = os.path.join(root, name)
            try:
                sz = os.path.getsize(p)
            except Exception as e:
                logging.warning("Skipping size read for %s: %s", p, e)
                continue
            if sz in b_sizes:
                candidates.append((p, sz))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(calculate_md5, p): (p, sz) for p, sz in candidates}
        for fut in as_completed(futs):
            p, sz = futs[fut]
            md5 = fut.result()
            if not md5:
                continue
            key = (sz, md5)
            if key in b_map:
                if dry_run:
                    logging.info("Would delete: %s (Size: %d, MD5: %s)", p, sz, md5)
                else:
                    try:
                        if move_to_trash and trash_dir:
                            os.makedirs(trash_dir, exist_ok=True)
                            dest = os.path.join(trash_dir, os.path.relpath(p, start=dir_a))
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            shutil.move(p, dest)
                            logging.info("Moved to trash: %s -> %s", p, dest)
                        else:
                            os.remove(p)
                            logging.info("Deleted: %s", p)
                    except Exception as e:
                        logging.error("Failed to remove/move %s: %s", p, e)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir_a")
    parser.add_argument("dir_b")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--move-to-trash", action="store_true", default=False)
    parser.add_argument("--trash-dir", default=None)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    delete_matching_files(args.dir_a, args.dir_b, dry_run=args.dry_run, move_to_trash=args.move_to_trash, trash_dir=args.trash_dir, workers=args.workers)


if __name__ == "__main__":
    dir_a = "Z:/a"    
    dir_b = "Z:/b"
    delete_matching_files(dir_a, dir_b, dry_run=False)
