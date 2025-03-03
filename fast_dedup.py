import os
import subprocess
import platform
import logging
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_md5(file_path):
    """Calculate the MD5 checksum of a file using the appropriate command based on the OS."""
    if platform.system() == "Windows":
        # Use certutil on Windows
        result = subprocess.run(['certutil', '-hashfile', file_path, 'MD5'], capture_output=True, text=True)
        # The output format includes extra lines, we need the second line
        md5_hash = result.stdout.splitlines()[1].strip()
    else:
        # Use md5sum on Linux
        result = subprocess.run(['md5sum', file_path], capture_output=True, text=True)
        md5_hash = result.stdout.split()[0]  # Get the hash from the output

    return md5_hash

def deduplicate_files(directory):
    """Deduplicate files in the given directory based on their sizes and MD5 checksums."""
    size_map = defaultdict(list)
    
    # First pass: index files by size
    logging.info("Indexing files by size...")
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            size_map[file_size].append(file_path)

    logging.info("Indexing complete. Found %d unique file sizes.", len(size_map))

    # Second pass: check for duplicates by size and MD5
    total_files = sum(len(paths) for paths in size_map.values())
    processed_files = 0

    for file_size, file_paths in size_map.items():
        if len(file_paths) > 1:  # Only check if there are potential duplicates
            md5_map = {}
            for file_path in file_paths:
                file_md5 = calculate_md5(file_path)
                processed_files += 1
                logging.info("Processing file %d of %d: %s", processed_files, total_files, file_path)

                if file_md5 in md5_map:
                    # If the MD5 already exists, delete the file
                    logging.warning("Deleting duplicate file: %s", file_path)
                    os.remove(file_path)
                else:
                    # Otherwise, add it to the hashmap
                    md5_map[file_md5] = file_path

    logging.info("Deduplication complete. Processed %d files.", processed_files)

if __name__ == "__main__":
    directory_path = os.path.dirname(os.path.abspath(__file__)) # input("Enter the directory path to deduplicate files: ")
    deduplicate_files(directory_path)
    input()
