#!/usr/bin/env python3
import os

root = "./"
target_size = 4096  # bytes

for dirpath, dirnames, filenames in os.walk(root):
    for name in filenames:
        path = os.path.join(dirpath, name)
        try:
            if os.path.islink(path):
                continue
            if os.path.getsize(path) == target_size:
                os.remove(path)
                print(f"deleted: {path}")
        except Exception as e:
            print(f"error: {path}: {e}")
