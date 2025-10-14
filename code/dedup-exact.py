import os
import subprocess
import platform
import logging
import re
from collections import defaultdict

# Set up logging with StreamHandler (works on Windows PowerShell too)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Regular expression to match a valid MD5 hash (32 hex characters)
MD5_REGEX = re.compile(r"^[a-fA-F0-9]{32}$")

def calculate_md5(file_path):
    """
    Calculate the MD5 checksum of a file using the appropriate command based on the OS.
    Returns the MD5 hash if valid, otherwise returns None.
    """
    if platform.system() == "Windows":
        # Use certutil on Windows
        command = ['certutil', '-hashfile', file_path, 'MD5']
    else:
        # Use md5sum on Linux and similar
        command = ['md5sum', file_path]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except Exception as e:
        logging.error("Could not run subprocess for file %s: %s", file_path, e)
        return None

    if result.returncode != 0:
        logging.error("Subprocess failed for file %s. Return code: %s, Error: %s", 
                      file_path, result.returncode, result.stderr)
        return None

    try:
        if platform.system() == "Windows":
            output_lines = result.stdout.splitlines()
            # Expecting output with the MD5 hash on the second line
            if len(output_lines) < 2:
                logging.error("Unexpected output format from certutil for file %s: %s", file_path, result.stdout)
                return None
            computed_hash = output_lines[1].strip()
        else:
            parts = result.stdout.split()
            if not parts:
                logging.error("Unexpected output from md5sum for file %s: %s", file_path, result.stdout)
                return None
            computed_hash = parts[0]
    except UnicodeDecodeError as ude:
        logging.error("Unicode decode error while processing file %s: %s", file_path, ude)
        return None
    except Exception as e:
        logging.error("Error processing output for file %s: %s", file_path, e)
        return None

    if not MD5_REGEX.fullmatch(computed_hash):
        logging.error("Computed hash '%s' for file %s is not a valid MD5 checksum.", computed_hash, file_path)
        return None

    return computed_hash

def files_are_identical(file1, file2, chunk_size=4096):
    """
    Compare two files' contents byte-by-byte.
    Returns True if files are identical, otherwise False.
    """
    try:
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            while True:
                b1 = f1.read(chunk_size)
                b2 = f2.read(chunk_size)
                if b1 != b2:
                    return False
                if not b1:  # End of file reached
                    break
    except Exception as e:
        logging.error("Error comparing files %s and %s: %s", file1, file2, e)
        return False
    return True

def deduplicate_files(directory):
    """
    Deduplicate files in the given directory based on their sizes, MD5 checksums,
    and a final byte-by-byte comparison. Returns a summary dictionary.
    """
    # Mapping file size to a list of filenames
    size_map = defaultdict(list)
    total_files = 0
    removed_duplicates = 0
    errors = 0
    skipped_files = 0  # Files skipped because MD5 couldn't be calculated

    # Indexing: Group files by file size
    logging.info("Indexing files by size in directory: %s", directory)
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                file_size = os.path.getsize(file_path)
            except Exception as e:
                logging.error("Error getting size for file %s: %s", file_path, e)
                errors += 1
                continue
            size_map[file_size].append(file_path)
            total_files += 1

    logging.info("Indexing complete. Found %d unique file sizes covering %d files.", len(size_map), total_files)

    processed_files = 0

    # Second Pass: For files with same sizes, check MD5 and then do a secure comparison.
    for file_size, file_paths in size_map.items():
        # Only potential duplicates (i.e. groups with more than one file) need further checks.
        if len(file_paths) > 1:
            md5_map = {}
            for file_path in file_paths:
                file_md5 = calculate_md5(file_path)
                processed_files += 1
                logging.info("Processing file %d of %d: %s", processed_files, total_files, file_path)
                if file_md5 is None:
                    logging.warning("Skipping file due to MD5 calculation failure: %s", file_path)
                    skipped_files += 1
                    continue

                if file_md5 in md5_map:
                    # At least one file with the same MD5 exists.
                    canonical_file = md5_map[file_md5]
                    if files_are_identical(canonical_file, file_path):
                        try:
                            os.remove(file_path)
                            removed_duplicates += 1
                            logging.warning("Deleting duplicate file (identical contents): %s", file_path)
                        except Exception as e:
                            logging.error("Failed to delete file %s: %s", file_path, e)
                            errors += 1
                    else:
                        # MD5 collision but files are not identical. Use a unique key by appending filename.
                        # This is extremely unlikely but handled here for completeness.
                        logging.warning("MD5 collision detected but files differ: %s and %s", canonical_file, file_path)
                        key = file_md5 + "_" + os.path.basename(file_path)
                        md5_map[key] = file_path
                else:
                    md5_map[file_md5] = file_path

    summary = {
        "total_files_found": total_files,
        "files_processed": processed_files,
        "duplicates_removed": removed_duplicates,
        "skipped_files": skipped_files,
        "errors": errors
    }
    return summary

if __name__ == "__main__":
    directory_path = "./"
    logging.info("Starting deduplication in directory: %s", directory_path)
    summary = deduplicate_files(directory_path)
    
    # Print summary output
    logging.info("Deduplication complete.")
    logging.info("Total files found: %d", summary["total_files_found"])
    logging.info("Files processed: %d", summary["files_processed"])
    logging.info("Duplicates removed: %d", summary["duplicates_removed"])
    logging.info("Files skipped (MD5 failure): %d", summary["skipped_files"])
    if summary["errors"]:
        logging.warning("Errors encountered during processing: %d", summary["errors"])
    else:
        logging.info("No errors encountered during processing.")

    input("Press Enter to exit...")
