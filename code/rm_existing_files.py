import os
import re
import subprocess
import platform
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Regular expression to validate MD5 checksums
MD5_REGEX = re.compile(r"^[a-fA-F0-9]{32}$")

def calculate_md5(file_path):
    """
    Calculate the MD5 checksum of a file using the appropriate command based on the OS.
    Returns the MD5 hash if valid, otherwise returns None.
    """
    logging.debug("Calculating MD5 for file: %s", file_path)
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

    logging.debug("Computed MD5 for file %s: %s", file_path, computed_hash)
    return computed_hash

def get_files_info(directory):
    """
    Walk through the directory and return a dictionary with file info:
    { (file_size, md5): file_path }
    """
    files_info = {}
    logging.info("Walking through directory: %s", directory)
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            file_md5 = calculate_md5(file_path)
            if file_md5:
                files_info[(file_size, file_md5)] = file_path
                logging.debug("Added file to info: %s (Size: %d, MD5: %s)", file_path, file_size, file_md5)
            else:
                logging.warning("Could not compute MD5 for file: %s", file_path)
    return files_info

def delete_matching_files(dir_a, dir_b):
    """
    Compare files in dir_a with files in dir_b and delete matching files in dir_a.
    """
    logging.info("Starting to compare files between '%s' and '%s'", dir_a, dir_b)
    dir_b_files_info = get_files_info(dir_b)

    # Create a set of file sizes from dir_b for quick lookup
    dir_b_file_sizes = {size for size, _ in dir_b_files_info.keys()}

    for root, _, files in os.walk(dir_a):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)

            # Only calculate MD5 if the file size matches one in dir_b
            if file_size in dir_b_file_sizes:
                file_md5 = calculate_md5(file_path)
                if file_md5 and (file_size, file_md5) in dir_b_files_info:
                    logging.info("Deleting matching file: %s (Size: %d, MD5: %s)", file_path, file_size, file_md5)
                    os.remove(file_path)
                else:
                    logging.debug("No match for file: %s (Size: %d, MD5: %s)", file_path, file_size, file_md5)
            else:
                logging.debug("File size %d does not match any in dir_b for file: %s", file_size, file_path)

    logging.info("Completed file comparison and deletion process.")

if __name__ == "__main__":
    dir_a = "./"  # Replace with the path to dir_a
    dir_b = "./"  # Replace with the path to dir_b
    delete_matching_files(dir_a, dir_b)
