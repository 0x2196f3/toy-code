import os
import subprocess

def update_metadata(input_file):
    # Define the ffmpeg executable path (relative path in this example)
    ffmpeg_path = r".\ffmpeg.exe"
    
    # Use the filename (with extension) as the title
    title = os.path.basename(input_file)
    
    # Create a temporary output filename: e.g., "input.mp4" -> "input_temp.mp4"
    base, ext = os.path.splitext(input_file)
    temp_output = base + "_temp" + ext

    # Build the ffmpeg command as a list.
    cmd = [
        ffmpeg_path,
        "-i", input_file,
        "-metadata", f"title={title}",
        "-codec", "copy",
        temp_output
    ]

    print(f"Processing: {input_file}")
    print(f"Running command: {' '.join(cmd)}")
    
    # Execute the ffmpeg command and capture the output
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    
    if result.returncode != 0:
        print(f"Error processing {input_file}:")
        print(result.stderr)
        return False
    
    # If conversion was successful, remove the original file and rename the temp file
    try:
        os.remove(input_file)
        os.rename(temp_output, input_file)
        print(f"Updated metadata and replaced the original file: {input_file}\n")
    except Exception as e:
        print(f"File operation error for {input_file}: {e}\n")
        return False
    
    return True

def main():
    # List all files in the current directory
    current_dir = "./"
    files = os.listdir(current_dir)
    
    # Filter for files that have the .mp4 extension (case insensitive)
    mp4_files = [
        f for f in files
        if os.path.isfile(os.path.join(current_dir, f)) and f.lower().endswith(".mp4")
    ]
    
    if not mp4_files:
        print("No .mp4 files found in the current directory.")
        return
    
    for file in mp4_files:
        # Construct the full path to the file, preserving any special characters
        filepath = os.path.join(current_dir, file)
        success = update_metadata(filepath)
        if not success:
            print(f"Skipping deletion and renaming for {filepath} due to an error.")

if __name__ == "__main__":
    main()
