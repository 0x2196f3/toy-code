#!/usr/bin/env python3
import os
import re

DRY_RUN = True  # Set to False to perform actual renaming

def clean_filename_regex(filename):
    """
    Cleans the filename using a regex.

    The regex finds all characters that are either:
    - Non-ASCII (we leave these intact)
    - ASCII alphanumeric (A-Za-z0-9)

    All other ASCII characters are removed.
    """
    valid_chars = re.findall(r'[A-Za-z0-9]|[^\x00-\x7F]', filename)
    return ''.join(valid_chars)

def clean_filename_no_regex(filename):
    """
    Cleans the filename without using regex.

    For each character:
    - If it is ASCII and alphanumeric, keep it.
    - If it is ASCII and not alphanumeric, remove it.
    - For non-ASCII characters, keep them.
    """
    new_chars = []
    for ch in filename:
        if ord(ch) < 128:
            if ch.isalnum():
                new_chars.append(ch)
        else:
            new_chars.append(ch)
    return ''.join(new_chars)

def process_rename(filename, new_filename):
    """
    Attempts to rename a file from filename to new_filename.
    Any errors are caught, and the file is skipped.
    """
    try:
        if DRY_RUN:
            print(f"[DRY RUN] Would rename: '{filename}' -> '{new_filename}'")
        else:
            os.rename(filename, new_filename)
            print(f"Renamed: '{filename}' -> '{new_filename}'")
    except Exception as e:
        print(f"Error renaming '{filename}' to '{new_filename}': {e}")
        print("Skipping this file.")

def main():
    for filename in os.listdir('.'):
        if os.path.isfile(filename):
            try:
                new_filename_regex = clean_filename_regex(filename)
                new_filename_no_regex = clean_filename_no_regex(filename)

                if new_filename_regex != new_filename_no_regex:
                    print(f"Discrepancy found in cleaning for '{filename}'!")
                    print(f"Regex version: {new_filename_regex}")
                    print(f"No-regex version: {new_filename_no_regex}")
                    print("Skipping this file due to discrepancy.")
                    continue  # Skip renaming if discrepancy detected

                if new_filename_regex != filename:
                    # Check for potential conflicts: if a file already exists with the new name
                    if os.path.exists(new_filename_regex):
                        print(f"File '{new_filename_regex}' already exists. Skipping '{filename}'.")
                        continue

                    process_rename(filename, new_filename_regex)
            except Exception as e:
                print(f"Unexpected error processing file '{filename}': {e}")
                print("Skipping this file.")

if __name__ == '__main__':
    main()
