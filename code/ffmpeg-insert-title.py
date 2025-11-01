import os
import subprocess

def update_metadata(input_file):
    ffmpeg_path = r".\ffmpeg.exe"
    
    title = os.path.basename(input_file)
    
    base, ext = os.path.splitext(input_file)
    temp_output = base + "_temp" + ext

    cmd = [
        ffmpeg_path,
        "-i", input_file,
        "-metadata", f"title={title}",
        "-codec", "copy",
        temp_output
    ]

    print(f"Processing: {input_file}")
    print(f"Running command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    
    if result.returncode != 0:
        print(f"Error processing {input_file}:")
        print(result.stderr)
        return False
    
    try:
        os.remove(input_file)
        os.rename(temp_output, input_file)
        print(f"Updated metadata and replaced the original file: {input_file}\n")
    except Exception as e:
        print(f"File operation error for {input_file}: {e}\n")
        return False
    
    return True

def main():
    current_dir = "./"
    files = os.listdir(current_dir)
    
    mp4_files = [
        f for f in files
        if os.path.isfile(os.path.join(current_dir, f)) and f.lower().endswith(".mp4")
    ]
    
    if not mp4_files:
        print("No .mp4 files found in the current directory.")
        return
    
    for file in mp4_files:
        filepath = os.path.join(current_dir, file)
        success = update_metadata(filepath)
        if not success:
            print(f"Skipping deletion and renaming for {filepath} due to an error.")

if __name__ == "__main__":
    main()
