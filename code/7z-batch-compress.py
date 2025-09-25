#!/usr/bin/env python3
import os
import subprocess
import sys

# Path to 7z executable
SEVEN_Z_PATH = r"C:\Program Files\7-Zip\7z.exe"

# File extensions to target (lowercase)
TARGET_EXTS = {'.iso', '.cso'}

# 7z options: maximum compression, solid archive, multithread (auto)
SEVEN_Z_OPTS = ['a', '-t7z', '-mx=9', '-m0=LZMA2', '-mmt=on', '-ms=on']

def find_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path
    if os.path.isfile(path):
        return path
    return None

def sizeof_bytes(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0

def mb(n_bytes):
    return n_bytes / (1024 * 1024)

def fmt_mb(n_bytes):
    return f"{mb(n_bytes):.2f} MB"

def compress_file(sevenz, src_path, results):
    src_dir = os.path.dirname(src_path)
    base = os.path.basename(src_path)
    dest_name = base + '.7z'               # e.g. game.iso.7z
    dest_path = os.path.join(src_dir, dest_name)

    # If dest already exists, skip
    if os.path.exists(dest_path):
        print(f"Skipping (archive exists): {src_path}")
        results['failed'].append((src_path, "archive_exists"))
        return

    orig_size = sizeof_bytes(src_path)

    cmd = [sevenz] + SEVEN_Z_OPTS + [dest_path, src_path]
    print("Running:", " ".join(f'"{c}"' if ' ' in c else c for c in cmd))
    try:
        proc = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        print(f"Error launching 7z for {src_path}: {e}")
        results['failed'].append((src_path, str(e)))
        return

    # 7z returns exit code 0 for no error. 1 = warning, >=2 = error.
    if proc.returncode == 0:
        # verify archive contains the file (list)
        verify_cmd = [sevenz, 'l', dest_path]
        try:
            vproc = subprocess.run(verify_cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if vproc.returncode == 0 and base in vproc.stdout:
                # get compressed size
                comp_size = sizeof_bytes(dest_path)
                try:
                    os.remove(src_path)
                    # compute ratio: compressed / original, and percent
                    ratio = (comp_size / orig_size) if orig_size > 0 else 0
                    ratio_pct = ratio * 100
                    print(f"Compressed and removed: {src_path} -> {dest_path}")
                    print(f"Original size: {fmt_mb(orig_size)} | Compressed size: {fmt_mb(comp_size)} | Ratio: {ratio_pct:.2f}%")
                    results['succeeded'].append((src_path, orig_size, comp_size))
                except OSError as e:
                    print(f"Archive created but failed to remove original {src_path}: {e}")
                    # still treat as failed since original not removed
                    comp_size = sizeof_bytes(dest_path)
                    results['failed'].append((src_path, f"remove_failed: {e}"))
            else:
                print(f"Archive created but verification failed for {src_path}. Leaving original.")
                results['failed'].append((src_path, "verify_failed"))
        except Exception as e:
            print(f"Failed to verify archive {dest_path}: {e}")
            results['failed'].append((src_path, f"verify_error: {e}"))
    else:
        print(f"7z failed for {src_path} (exit {proc.returncode}). stdout/stderr:\n{proc.stdout}\n{proc.stderr}")
        results['failed'].append((src_path, f"7z_exit_{proc.returncode}"))

def print_summary(results):
    succ = results['succeeded']
    fail = results['failed']
    total = len(succ) + len(fail)

    total_orig = sum(item[1] for item in succ) if succ else 0
    total_comp = sum(item[2] for item in succ) if succ else 0

    avg_ratio_pct = ( (total_comp / total_orig) * 100 ) if total_orig > 0 else 0.0

    print("\n=== Summary ===")
    print(f"Total files considered: {total}")
    print(f"Succeeded: {len(succ)}")
    print(f"Failed / Skipped: {len(fail)}")
    print(f"Total original size (succeeded files): {fmt_mb(total_orig)}")
    print(f"Total compressed size (succeeded files): {fmt_mb(total_comp)}")
    print(f"Average compression ratio (weighted, succeeded files): {avg_ratio_pct:.2f}%")

    if fail:
        print("\nFailed / Skipped files (reason):")
        for fpath, reason in fail:
            print(f"- {fpath}: {reason}")

def main():
    sevenz = find_executable(SEVEN_Z_PATH)
    if not sevenz:
        print(f"7z executable not found at: {SEVEN_Z_PATH}", file=sys.stderr)
        sys.exit(1)

    results = {
        'succeeded': [],  # list of tuples (src_path, orig_size, comp_size)
        'failed': []      # list of tuples (src_path, reason)
    }

    start_dir = os.path.abspath('.')
    for root, dirs, files in os.walk(start_dir):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext.lower() in TARGET_EXTS:
                src = os.path.join(root, fname)
                compress_file(sevenz, src, results)

    print_summary(results)

if __name__ == '__main__':
    main()
