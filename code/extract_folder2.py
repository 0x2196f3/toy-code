# flatten_single_child.py
# Windows-ready; uses os and shutil
import os
import shutil

def is_immediate_only_one_dir_and_no_files(path):
    # list immediate entries
    try:
        entries = os.listdir(path)
    except OSError:
        return False
    # count files and directories among immediate children
    dirs = [d for d in entries if os.path.isdir(os.path.join(path, d))]
    files = [f for f in entries if os.path.isfile(os.path.join(path, f))]
    return len(dirs) == 1 and len(files) == 0

def move_child_contents_up(parent_path):
    child_name = next(d for d in os.listdir(parent_path) if os.path.isdir(os.path.join(parent_path, d)))
    child_path = os.path.join(parent_path, child_name)
    # move all entries from child_path into parent_path
    for name in os.listdir(child_path):
        src = os.path.join(child_path, name)
        dst = os.path.join(parent_path, name)
        # If destination exists, decide behavior: here we rename to avoid overwrite by appending suffix
        if os.path.exists(dst):
            base, ext = os.path.splitext(name)
            i = 1
            while True:
                new_name = f"{base} (conflict {i}){ext}"
                dst = os.path.join(parent_path, new_name)
                if not os.path.exists(dst):
                    break
                i += 1
        try:
            shutil.move(src, dst)
            print(f"Moved: {src} -> {dst}")
        except Exception as e:
            print(f"Failed to move {src} -> {dst}: {e}")
    # remove the now-empty child directory (only if empty)
    try:
        os.rmdir(child_path)
        print(f"Removed empty folder: {child_path}")
    except OSError as e:
        print(f"Could not remove {child_path}: {e}")

def main(root_dir='.'):
    root_dir = os.path.abspath(root_dir)
    # iterate immediate subfolders of root_dir
    for name in os.listdir(root_dir):
        parent = os.path.join(root_dir, name)
        if not os.path.isdir(parent):
            continue
        if is_immediate_only_one_dir_and_no_files(parent):
            print(f"Flattening: {parent}")
            move_child_contents_up(parent)

if __name__ == '__main__':
    # default runs in current directory; pass a path as first arg to use another folder
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    main(path)
