import os
import sys
import json
import logging
import hashlib
import platform
from collections import defaultdict

DRY_RUN = True
MIN_SIZE = 1 * 1024**3
STATE_JSON = "dedupe_state.json"
DEDUP_JSON = "dedupe_duplicates.json"
EXTREMELY_FAST = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

def atomic_write(data, filepath):
    if not filepath:
        return
    temp_path = filepath + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, filepath)
    except Exception as e:
        logging.error(f"Failed to write JSON to {filepath}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

def get_file_hash(filepath, file_size):
    sha = hashlib.sha256()
    read_limit = None
    
    if EXTREMELY_FAST:
        read_limit = max(1 * 1024**2, int(file_size * 0.01))
    
    bytes_read = 0
    chunk_size = 1024 * 1024
    
    try:
        with open(filepath, 'rb') as f:
            while True:
                if read_limit is not None and bytes_read >= read_limit:
                    break
                
                to_read = chunk_size
                if read_limit is not None:
                    remaining = read_limit - bytes_read
                    if remaining < chunk_size:
                        to_read = remaining
                
                chunk = f.read(to_read)
                if not chunk:
                    break
                
                sha.update(chunk)
                bytes_read += len(chunk)
                
    except (OSError, IOError) as e:
        logging.error(f"Error reading file {filepath}: {e}")
        return None
        
    return sha.hexdigest()

def scan_files(directory):
    size_groups = defaultdict(list)
    stats = {
        "total_files_walked": 0,
        "files_ignored_by_size": 0,
        "errors_indexing": 0
    }
    
    logging.info(f"Indexing files in {directory}")
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                stat_info = os.stat(filepath)
                fsize = stat_info.st_size
                stats["total_files_walked"] += 1
                
                if fsize < MIN_SIZE:
                    stats["files_ignored_by_size"] += 1
                    continue
                    
                size_groups[fsize].append({
                    "path": filepath,
                    "sha256": "0"
                })
                
            except OSError:
                stats["errors_indexing"] += 1
                
    filtered_groups = {str(k): v for k, v in size_groups.items() if len(v) > 1}
    files_to_check = sum(len(v) for v in filtered_groups.values())
    
    return filtered_groups, stats, files_to_check

def perform_deduplication(directory):
    files_map, stats, total_to_check = scan_files(directory)
    
    runtime_state = {
        "files_by_size": files_map,
        "stats": stats,
        "progress": {
            "files_processed": 0,
            "duplicates_found": 0,
            "bytes_reclaimed": 0,
            "errors": 0,
            "skipped": 0,
            "total_to_process": total_to_check
        }
    }
    
    if STATE_JSON:
        atomic_write(runtime_state, STATE_JSON)
        
    logging.info(f"Found {len(files_map)} size groups with potential duplicates. Processing {total_to_check} files.")
    
    final_duplicates = {}
    
    for size_str, group in files_map.items():
        if len(group) < 2:
            continue
            
        file_size = int(size_str)
        seen_hashes = {}
        
        for entry in group:
            path = entry["path"]
            
            existing_hash = entry.get("sha256", "0")
            
            if existing_hash != "0":
                file_hash = existing_hash
            else:
                file_hash = get_file_hash(path, file_size)
                runtime_state["progress"]["files_processed"] += 1
                
                if file_hash:
                    entry["sha256"] = file_hash
                else:
                    runtime_state["progress"]["skipped"] += 1
                    entry["sha256"] = "0"
                    continue
            
            if file_hash in seen_hashes:
                original_path = seen_hashes[file_hash]
                runtime_state["progress"]["duplicates_found"] += 1
                
                if DRY_RUN:
                    logging.warning(f"[DRY RUN] Duplicate found: {path} == {original_path}")
                else:
                    try:
                        os.remove(path)
                        logging.warning(f"Deleted duplicate: {path}")
                        runtime_state["progress"]["bytes_reclaimed"] += file_size
                    except OSError as e:
                        logging.error(f"Failed to delete {path}: {e}")
                        runtime_state["progress"]["errors"] += 1
                
                if file_hash not in final_duplicates:
                    final_duplicates[file_hash] = [original_path]
                final_duplicates[file_hash].append(path)
                
            else:
                seen_hashes[file_hash] = path
            
            if STATE_JSON:
                atomic_write(runtime_state, STATE_JSON)
                
    if DEDUP_JSON:
        output_report = {
            "duplicates": {},
            "metadata": runtime_state["stats"]
        }
        output_report["metadata"].update(runtime_state["progress"])
        
        for h, paths in final_duplicates.items():
            output_report["duplicates"][h] = {
                "files": paths,
                "count": len(paths),
                "example_keep": paths[0]
            }
        atomic_write(output_report, DEDUP_JSON)
        
    return runtime_state

if __name__ == "__main__":
    target_dir = "./"
    logging.info(f"Starting Scan. DRY_RUN={DRY_RUN}, FAST_MODE={EXTREMELY_FAST}, MIN_SIZE={MIN_SIZE}")
    
    result = perform_deduplication(target_dir)
    
    p = result["progress"]
    logging.info("Scan Complete.")
    logging.info(f"Processed: {p['files_processed']}")
    logging.info(f"Duplicates: {p['duplicates_found']}")
    logging.info(f"Errors: {p['errors']}")
    logging.info(f"Skipped: {p['skipped']}")
    
    input("Press Enter to exit...")