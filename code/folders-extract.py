#!/usr/bin/env python3
import os
import shutil

ADD_FOLDER_NAME = True
RECURSIVE = True
ROOT_DIR = './'
REMOVE_ORIGINAL_FOLDER = False

def build_prefix(root_dir, file_dir):
    root_abs = os.path.abspath(root_dir)
    dir_abs = os.path.abspath(file_dir)

    if dir_abs == root_abs:
        return ''

    rel = os.path.relpath(dir_abs, root_abs)
    if rel.startswith('..'):
        parts = dir_abs.split(os.sep)
    else:
        parts = rel.split(os.sep)

    parts = [p for p in parts if p and p != os.curdir]
    return '_'.join(parts)

def unique_destination(path):
    base, ext = os.path.splitext(path)
    counter = 1
    candidate = path
    while os.path.exists(candidate):
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate

def move_files_one_level(root_dir, add_folder_name):
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
    for dirpath, dirnames, filenames in os.walk(root_abs):
        if os.path.abspath(dirpath) == root_abs:
            continue

        for fname in filenames:
            src = os.path.join(dirpath, fname)
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

def remove_empty_dirs(root_dir, skip_paths=None):
    if skip_paths is None:
        skip_paths = set()
    removed = []
    root_abs = os.path.abspath(root_dir)
    for dirpath, dirnames, filenames in os.walk(root_abs, topdown=False):
        dir_abs = os.path.abspath(dirpath)
        if dir_abs == root_abs:
            continue
        if dir_abs in skip_paths:
            continue
        try:
            if not os.listdir(dir_abs):
                os.rmdir(dir_abs)
                removed.append(dir_abs)
                print(f"Removed empty directory: {dir_abs}")
        except OSError as e:
            print(f"Could not remove {dir_abs}: {e}")
    return removed

if __name__ == "__main__":
    if not os.path.isdir(ROOT_DIR):
        raise SystemExit(f"Root directory does not exist: {ROOT_DIR}")
    script_path = os.path.abspath(__file__) if '__file__' in globals() else None
    skip_paths = set()
    if script_path:
        script_dir = os.path.abspath(os.path.dirname(script_path))
        skip_paths.add(script_dir)

    if RECURSIVE:
        move_files_recursive(ROOT_DIR, ADD_FOLDER_NAME)
    else:
        move_files_one_level(ROOT_DIR, ADD_FOLDER_NAME)

    if REMOVE_ORIGINAL_FOLDER:
        remove_empty_dirs(ROOT_DIR, skip_paths=skip_paths)
