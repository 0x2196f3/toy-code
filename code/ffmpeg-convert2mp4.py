import os
import subprocess
import glob

def convert_webm_to_mp4(input_path, output_path):

    command = [
        'ffmpeg',
        '-i', input_path,
        '-c:v', 'copy', 
        '-c:a', 'copy',  
        output_path
    ]
    
    print(f"Converting {input_path} to {output_path}...")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"Error converting {input_path}:\n{result.stderr}")
    else:
        print(f"Successfully converted {input_path} to {output_path}")

def main(suffix):
    files = glob.glob("./*." + suffix)
    if not files:
        print("No .webm files found in the current directory.")
        return

    for webm_file in files:
        base_name = os.path.splitext(webm_file)[0]
        output_file = base_name + ".mp4"
        
        convert_webm_to_mp4(webm_file, output_file)

if __name__ == "__main__":
    main("webm")
    main("mkv")

