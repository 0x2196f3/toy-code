import os
import re
import json
import shutil
import sys
import subprocess

def get_ffmpeg_path():
    ext = ".exe" if os.name == "nt" else ""
    local_path = os.path.abspath(f"ffmpeg{ext}")
    if os.path.isfile(local_path):
        return local_path
    return "ffmpeg"

def sanitize_name(text):
    if not text:
        return ""
    return re.sub(r'[<>:"/\\|?*]', ' ', str(text)).strip()

def get_unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{base}({counter}){ext}"):
        counter += 1
    return f"{base}({counter}){ext}"

def merge_media(ffmpeg_cmd, video_path, audio_path, output_path):
    output_path = get_unique_path(output_path)
    command = [
        ffmpeg_cmd, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "copy",
        output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except (subprocess.CalledProcessError, OSError):
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return None

def process_directory(root_dir, ffmpeg_cmd):
    if not os.path.isdir(root_dir):
        return None
    
    main_title = None
    
    try:
        subdirectories = sorted([d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))])
    except OSError:
        return None

    for sub in subdirectories:
        episode_dir = os.path.join(root_dir, sub)
        entry_file = os.path.join(episode_dir, "entry.json")
        
        if not os.path.isfile(entry_file):
            continue
            
        try:
            with open(entry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if main_title is None:
            main_title = sanitize_name(data.get("title", ""))
            
        type_tag = sanitize_name(data.get("type_tag", ""))
        
        strid = ""
        subtitle = ""
        
        if "ep" in data:
            strid = sanitize_name(data["ep"].get("index", ""))
            subtitle = sanitize_name(data["ep"].get("index_title", ""))
        elif "page_data" in data:
            strid = sanitize_name(data["page_data"].get("page", ""))
            subtitle = sanitize_name(data["page_data"].get("part", ""))
            
        out_filename = f"{strid}_{subtitle}.mp4" if strid else f"{main_title}.mp4"
        out_filepath = os.path.join(root_dir, out_filename)
        
        video_file = os.path.join(episode_dir, type_tag, "video.m4s")
        audio_file = os.path.join(episode_dir, type_tag, "audio.m4s")
        
        if os.path.isfile(video_file) and os.path.isfile(audio_file):
            success_path = merge_media(ffmpeg_cmd, video_file, audio_file, out_filepath)
            if success_path:
                try:
                    shutil.rmtree(episode_dir)
                except OSError:
                    pass

    return main_title

def main():
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except OSError:
        pass

    ffmpeg_bin = get_ffmpeg_path()
    
    try:
        subprocess.run([ffmpeg_bin, "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError):
        print("Error: FFmpeg not found or not executable.")
        return

    base_path = "."
    try:
        root_items = os.listdir(base_path)
    except OSError:
        return

    for item in root_items:
        item_full_path = os.path.join(base_path, item)
        if os.path.isdir(item_full_path):
            resolved_title = process_directory(item_full_path, ffmpeg_bin)
            if resolved_title and resolved_title != item:
                new_folder_path = get_unique_path(os.path.join(base_path, resolved_title))
                try:
                    os.rename(item_full_path, new_folder_path)
                except OSError:
                    pass

if __name__ == "__main__":
    main()
