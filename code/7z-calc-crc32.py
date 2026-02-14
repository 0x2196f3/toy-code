import pathlib
import re
import binascii
import sys
import os

CRC_RE = re.compile(r'\(([A-Fa-f0-9]{8})\)\.mp4$', re.IGNORECASE)

def find_mp4_with_crc(root: pathlib.Path):
    for p in root.rglob('*.mp4'):
        m = CRC_RE.search(p.name)
        if m:
            yield p, m.group(1).upper()

def compute_crc32_local(file_path: pathlib.Path) -> str:
    bufsize = 4 * 1024 * 1024
    crc = 0
    with file_path.open('rb') as f:
        while True:
            chunk = f.read(bufsize)
            if not chunk:
                break
            crc = binascii.crc32(chunk, crc)
    return f"{crc & 0xFFFFFFFF:08X}"

def main():
    root = pathlib.Path('.').resolve()
    if len(sys.argv) > 1:
        root = pathlib.Path(sys.argv[1])

    errors = 0
    for path, expected in find_mp4_with_crc(root):
        try:
            actual = compute_crc32_local(path)
        except Exception as e:
            print(f"ERROR reading {path}: {e}", file=sys.stderr)
            errors += 1
            continue
        if actual.upper() != expected.upper():
            print(f"Mismatch: {path} expected {expected} actual {actual}")
            errors += 1

    if errors == 0:
        print("All CRC32 values match.")
    else:
        print(f"Done. {errors} mismatch(es)/error(s) found.")

if __name__ == "__main__":
    main()
