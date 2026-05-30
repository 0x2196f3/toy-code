#!/usr/bin/env python3
import os
import re

DRY_RUN = True

def clean_filename_regex(filename):
    valid_chars = re.findall(r'[A-Za-z0-9]|[^\x00-\x7F]', filename)
    return ''.join(valid_chars)

def clean_filename_no_regex(filename):
    new_chars = []
    for ch in filename:
        if ord(ch) < 128:
            if ch.isalnum():
                new_chars.append(ch)
        else:
            new_chars.append(ch)
    return ''.join(new_chars)

def process_rename(filename, new_filename):
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
                    continue

                if new_filename_regex != filename:
                    if os.path.exists(new_filename_regex):
                        print(f"File '{new_filename_regex}' already exists. Skipping '{filename}'.")
                        continue

                    process_rename(filename, new_filename_regex)
            except Exception as e:
                print(f"Unexpected error processing file '{filename}': {e}")
                print("Skipping this file.")

if __name__ == '__main__':
    main()
