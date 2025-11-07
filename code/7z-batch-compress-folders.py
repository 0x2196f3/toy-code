#!/usr/bin/env python3
import os
import subprocess
import sys

SEVEN_Z_PATH = r"C:\Program Files\7-Zip\7z.exe"
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

def compress_folder(sevenz, folder_path, results):
    parent = os.path.dirname(folder_path)
    base = os.path.basename(folder_path.rstrip(os.sep))
    dest_name = base + '.7z'
    dest_path = os.path.join(parent, dest_name)

    if os.path.exists(dest_path):
        print(f"Skipping (archive exists): {folder_path}")
        results['failed'].append((folder_path, "archive_exists"))
        return

    # Estimate original size by summing files inside folder
    orig_size = 0
    for root, _, files in os.walk(folder_path):
        for f in files:
            try:
                orig_size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass

    cmd = [sevenz] + SEVEN_Z_OPTS + [dest_path, folder_path]
    print("Running:", " ".join(f'"{c}"' if ' ' in c else c for c in cmd))
    try:
        proc = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        print(f"Error launching 7z for {folder_path}: {e}")
        results['failed'].append((folder_path, str(e)))
        return

    if proc.returncode == 0:
        verify_cmd = [sevenz, 'l', dest_path]
        try:
            vproc = subprocess.run(verify_cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # verify that base folder name appears in the archive listing
            if vproc.returncode == 0 and base in vproc.stdout:
                comp_size = sizeof_bytes(dest_path)
                try:
                    # remove folder tree
                    for root, dirs, files in os.walk(folder_path, topdown=False):
                        for fname in files:
                            try:
                                os.remove(os.path.join(root, fname))
                            except OSError:
                                pass
                        for dname in dirs:
                            try:
                                os.rmdir(os.path.join(root, dname))
                            except OSError:
                                pass
                    try:
                        os.rmdir(folder_path)
                    except OSError:
                        pass
                    ratio = (comp_size / orig_size) if orig_size > 0 else 0
                    ratio_pct = ratio * 100
                    print(f"Compressed and removed: {folder_path} -> {dest_path}")
                    print(f"Original size (sum): {fmt_mb(orig_size)} | Compressed size: {fmt_mb(comp_size)} | Ratio: {ratio_pct:.2f}%")
                    results['succeeded'].append((folder_path, orig_size, comp_size))
                except Exception as e:
                    print(f"Archive created but failed to remove original folder {folder_path}: {e}")
                    results['failed'].append((folder_path, f"remove_failed: {e}"))
            else:
                print(f"Archive created but verification failed for {folder_path}. Leaving original.")
                results['failed'].append((folder_path, "verify_failed"))
        except Exception as e:
            print(f"Failed to verify archive {dest_path}: {e}")
            results['failed'].append((folder_path, f"verify_error: {e}"))
    else:
        print(f"7z failed for {folder_path} (exit {proc.returncode}). stdout/stderr:\n{proc.stdout}\n{proc.stderr}")
        results['failed'].append((folder_path, f"7z_exit_{proc.returncode}"))

def print_summary(results):
    succ = results['succeeded']
    fail = results['failed']
    total = len(succ) + len(fail)

    total_orig = sum(item[1] for item in succ) if succ else 0
    total_comp = sum(item[2] for item in succ) if succ else 0

    avg_ratio_pct = ( (total_comp / total_orig) * 100 ) if total_orig > 0 else 0.0

    print("\n=== Summary ===")
    print(f"Total folders considered: {total}")
    print(f"Succeeded: {len(succ)}")
    print(f"Failed / Skipped: {len(fail)}")
    print(f"Total original size (succeeded folders): {fmt_mb(total_orig)}")
    print(f"Total compressed size (succeeded folders): {fmt_mb(total_comp)}")
    print(f"Average compression ratio (weighted, succeeded folders): {avg_ratio_pct:.2f}%")

    if fail:
        print("\nFailed / Skipped folders (reason):")
        for fpath, reason in fail:
            print(f"- {fpath}: {reason}")

def main():
    sevenz = find_executable(SEVEN_Z_PATH)
    if not sevenz:
        print(f"7z executable not found at: {SEVEN_Z_PATH}", file=sys.stderr)
        sys.exit(1)

    results = {'succeeded': [], 'failed': []}

    start_dir = os.path.abspath('.')
    # iterate immediate subdirectories only
    for entry in os.listdir(start_dir):
        path = os.path.join(start_dir, entry)
        if os.path.isdir(path):
            compress_folder(sevenz, path, results)

    print_summary(results)

if __name__ == '__main__':
    main()
