#!/usr/bin/env python3
"""
Recursively delete files in ./a whose basename (name without extension)
does not exist anywhere under ./b.

Behavior:
- Walk ./b first to build a set of basenames present in ./b.
- Then walk ./a and delete files whose basename is not in that set.
- Symlinks are treated as files (os.path.islink check); adjust as needed.
- Prints deleted file paths. No dry-run mode by default; add if desired.
"""

from pathlib import Path
import os
import sys

DIR_A = Path("Z:/media/mini/郭德纲相声2_480P")
DIR_B = Path("\\\\TRUENAS\\Data\\media\\xiangsheng")

if not DIR_A.exists() or not DIR_A.is_dir():
    print(f"Error: {DIR_A} not found or not a directory.", file=sys.stderr)
    sys.exit(1)
if not DIR_B.exists() or not DIR_B.is_dir():
    print(f"Error: {DIR_B} not found or not a directory.", file=sys.stderr)
    sys.exit(1)

# Build set of basenames (stem) present in ./b (recursive)
b_stems = {p.stem.lower() for p in DIR_B.rglob("*") if p.is_file() or p.is_symlink()}


# Iterate ./a and delete files whose stem not in b_stems
deleted_count = 0
for p in DIR_A.rglob("*"):
    if p.is_file() or p.is_symlink():
        if p.stem.lower() not in b_stems:
            try:
                p.unlink()
                print(f"Deleted: {p}")
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete {p}: {e}", file=sys.stderr)

print(f"Done. Deleted {deleted_count} file(s).")
