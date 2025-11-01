#!/usr/bin/env python3
import os
import shutil
import sys

ROOT_DIR = './'

def unique_destination(path):
    base, ext = os.path.splitext(path)
    counter = 1
    candidate = path
    while os.path.exists(candidate):
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate

def pack_files(root_dir):
    root_dir = os.path.abspath(root_dir)
    for entry in os.listdir(root_dir):
        src_path = os.path.join(root_dir, entry)
        if not os.path.isfile(src_path):
            continue

        if '_' not in entry:
            continue 

        first, rest = entry.split('_', 1)
        if not first:
            continue

        target_dir = os.path.join(root_dir, first)
        os.makedirs(target_dir, exist_ok=True)

        dest_name = rest
        dest_path = os.path.join(target_dir, dest_name)
        dest_path = unique_destination(dest_path)

        shutil.move(src_path, dest_path)
        print(f"Moved: {src_path} -> {dest_path}")

if __name__ == "__main__":
    root = ROOT_DIR
    if len(sys.argv) > 1:
        root = sys.argv[1]
    if not os.path.isdir(root):
        sys.exit(f"Root directory does not exist: {root}")
    pack_files(root)
