import os
import shutil
import sys

TEN_GIB = 10 * 1024**3
SAFETY_LEAVE = 1 * 1024**2
WRITE_CHUNK = 4 * 1024**2

try:
    script_dir = os.path.dirname(os.path.realpath(__file__))
except NameError:
    script_dir = os.getcwd()
os.chdir(script_dir)

def free_bytes(path='.'):
    return shutil.disk_usage(path).free

def write_random_file(path, size_bytes):
    with open(path, 'wb') as f:
        remaining = size_bytes
        while remaining > 0:
            chunk = WRITE_CHUNK if remaining >= WRITE_CHUNK else remaining
            f.write(os.urandom(chunk))
            remaining -= chunk

def main():
    base_name = "10GB.bin"
    free = free_bytes('.')
    if free <= SAFETY_LEAVE:
        print("Not enough free space to start.")
        sys.exit(1)

    per_file = min(TEN_GIB, max(1, free // 10))
    if per_file < 1024:
        print("Calculated per-file size too small; aborting.")
        sys.exit(1)

    index = 0
    created = []
    while True:
        free = free_bytes('.')
        if free <= SAFETY_LEAVE:
            break
        if free - SAFETY_LEAVE >= per_file:
            name = base_name if index == 0 else f"{base_name}-{index}"
            print(f"Creating {name} ({per_file} bytes)...")
            write_random_file(name, per_file)
            created.append(name)
            index += 1
            continue
        final_size = free - SAFETY_LEAVE
        if final_size > 0:
            name = base_name if index == 0 else f"{base_name}-{index}"
            print(f"Creating final file {name} ({final_size} bytes)...")
            write_random_file(name, final_size)
            created.append(name)
        break

    print("Done. Created files:")
    for n in created:
        print("  ", n)

if __name__ == "__main__":
    main()
    input("Press Any Key To Continue")
