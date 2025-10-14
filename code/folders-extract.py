#!/usr/bin/env python3
import os
import shutil

# Configuration
ADD_FOLDER_NAME = True      # If True, prefix filenames with parent folder names
RECURSIVE = True           # If True, move files from all subfolders into the root
ROOT_DIR = './'            # Root folder to move files into (can be absolute or relative)

def build_prefix(root_dir, file_dir):
    """
    Build a prefix from the path components between root_dir and file_dir.
    Example: root_dir='./', file_dir='./aaa/bbb' -> 'aaa_bbb'
    """
    # Normalize and make absolute for reliable relative path calculation
    root_abs = os.path.abspath(root_dir)
    dir_abs = os.path.abspath(file_dir)

    if dir_abs == root_abs:
        return ''  # file is already in root

    # Compute relative path from root to the file's directory
    rel = os.path.relpath(dir_abs, root_abs)
    # If rel starts with '..', the file_dir is outside root_dir; handle by using full components
    if rel.startswith('..'):
        parts = dir_abs.split(os.sep)
    else:
        parts = rel.split(os.sep)

    # Join parts with underscore, ignoring empty components
    parts = [p for p in parts if p and p != os.curdir]
    return '_'.join(parts)

def unique_destination(path):
    """
    If path exists, append a numeric suffix before the extension to avoid overwriting.
    Example: file.txt -> file_1.txt -> file_2.txt ...
    """
    base, ext = os.path.splitext(path)
    counter = 1
    candidate = path
    while os.path.exists(candidate):
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate

def move_files_one_level(root_dir, add_folder_name):
    # Iterate items directly under root_dir
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        if os.path.isdir(item_path):
            for fname in os.listdir(item_path):
                src = os.path.join(item_path, fname)
                if not os.path.isfile(src):
                    continue
                if add_folder_name:
                    new_name = f"{item}_{fname}"
                else:
                    new_name = fname
                dest = os.path.join(root_dir, new_name)
                dest = unique_destination(dest)
                shutil.move(src, dest)
                print(f"Moved: {src} -> {dest}")

def move_files_recursive(root_dir, add_folder_name):
    root_abs = os.path.abspath(root_dir)
    # Walk the directory tree top-down
    for dirpath, dirnames, filenames in os.walk(root_abs):
        # Skip the root directory itself (we only want files in subfolders)
        if os.path.abspath(dirpath) == root_abs:
            continue

        for fname in filenames:
            src = os.path.join(dirpath, fname)
            # Optional: skip moving this script if placed in root (prevents self-move)
            # If you want to skip other files, add checks here.
            # Build new filename
            if add_folder_name:
                prefix = build_prefix(root_abs, dirpath)
                if prefix:
                    new_name = f"{prefix}_{fname}"
                else:
                    new_name = fname
            else:
                new_name = fname

            dest = os.path.join(root_abs, new_name)
            dest = unique_destination(dest)
            shutil.move(src, dest)
            print(f"Moved: {src} -> {dest}")

if __name__ == "__main__":
    # Prevent accidentally moving files outside intended root
    if not os.path.isdir(ROOT_DIR):
        raise SystemExit(f"Root directory does not exist: {ROOT_DIR}")

    # Avoid moving the script file itself if it's inside the root
    script_path = os.path.abspath(__file__) if '__file__' in globals() else None

    if RECURSIVE:
        move_files_recursive(ROOT_DIR, ADD_FOLDER_NAME)
    else:
        move_files_one_level(ROOT_DIR, ADD_FOLDER_NAME)
