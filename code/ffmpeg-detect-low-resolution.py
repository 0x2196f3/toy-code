import os
import subprocess
import shutil

threshold = 1200 * 720

FFPROBE = os.path.abspath('./ffprobe.exe')

for root, _, files in os.walk('./video'):
    for fname in files:
        if not fname.lower().endswith('.mp4'):
            continue

        src_path = os.path.join(root, fname)
        cmd = [
            FFPROBE, '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0:s=x',
            src_path
        ]
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            w, h = map(int, output.decode().strip().split('x'))
        except Exception:
            print(f"Could not get resolution for {src_path}")
            continue

        if w * h < threshold:
            parent_folder = os.path.basename(os.path.abspath(root))
            dest_folder = os.path.join('.', f'low_{parent_folder}')
            os.makedirs(dest_folder, exist_ok=True)

            dest_path = os.path.join(dest_folder, fname)
            print(f"Moving {src_path} → {dest_path} ({w}×{h})")
            shutil.move(src_path, dest_path)
