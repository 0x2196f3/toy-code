#!/usr/bin/env python3
# create-empty-file.py
# Usage: python create-empty-file.py filename size
# Examples:
#   python create-empty-file.py test1.flac 10mb
#   python create-empty-file.py test2.flac 512kb
#   python create-empty-file.py test3.flac 1g
# Size accepts suffixes: b, kb, mb, gb (case-insensitive). Default unit is bytes if no suffix.

import sys
from pathlib import Path
import re

UNIT_MAP = {
    'b': 1,
    'kb': 1024,
    'k': 1024,
    'mb': 1024**2,
    'm': 1024**2,
    'gb': 1024**3,
    'g': 1024**3,
}

def parse_size(s: str) -> int:
    s = s.strip().lower()
    m = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*([kmgb]{0,2})', s)
    if not m:
        raise ValueError("Invalid size format")
    num = float(m.group(1))
    unit = m.group(2) or 'b'
    if unit not in UNIT_MAP:
        raise ValueError("Unknown unit")
    return int(num * UNIT_MAP[unit])

def create_sparse(path: Path, size: int):
    with open(path, 'wb') as f:
        if size == 0:
            return
        f.seek(size - 1)
        f.write(b'\0')

def main(argv):
    if len(argv) != 3:
        print("Usage: create-empty-file.py filename size (e.g. 10mb, 512kb, 100b)")
        return 2
    filename = argv[1]
    size_str = argv[2]
    try:
        size = parse_size(size_str)
    except ValueError:
        print("Invalid size. Use numbers with optional suffix b/kb/mb/gb.")
        return 2
    path = Path(filename)
    if path.exists():
        print(f"Overwriting existing file: {path}")
    try:
        create_sparse(path, size)
    except PermissionError:
        print("Permission denied writing file:", path)
        return 3
    print(f"Created {path} — {size} bytes")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
