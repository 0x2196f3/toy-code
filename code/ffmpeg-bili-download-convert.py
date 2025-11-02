import os
import re
import shutil
import json
import subprocess

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?* ]', ' ', filename)
       
def cmd(command):
    print(f"Running command: {command}")
    return subprocess.run(command, shell=True)

def delete(path):
    print(f"Deleting: {path}")
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)

def rename(old, new):
    print(f"Renaming: {old} to {new}")
    os.rename(old, new)

def merge_video_and_audio(video, audio, output=None, delete_origin=False):
    """Merge video and audio files into a single output file."""
    output = output or f"{remove_suffix(video)}.mp4"
    command = f"ffmpeg -i \"{video}\" -i \"{audio}\" -c:v copy -c:a copy -strict experimental \"{output}\""
    cmd(command)
    if delete_origin:
        delete(video)
        delete(audio)

def remove_suffix(text):
    return os.path.splitext(text)[0]

def get_suffix(text):
    return os.path.splitext(text)[1]

def convert(root):
    files = sorted(os.listdir(root))
    if not files:
        return None

    name = None
    for file in files:
        dir_path = os.path.join(root, file)
        if not os.path.isdir(dir_path):
            continue

        info_path = os.path.join(dir_path, "entry.json")
        if not os.path.exists(info_path):
            continue
        dir_name = None
        strid = None
        subtitle = None
        
        with open(info_path, "r", encoding="utf-8") as info:
            data = json.load(info)
            if name is None:
                name = sanitize_filename(data["title"])
            dir_name = sanitize_filename(data["type_tag"])
            try:
                strid = sanitize_filename(str(data.get("ep", {}).get("index", "")))
                subtitle = sanitize_filename(str(data.get("ep", {}).get("index_title", "")))
            except BaseException as e:
                pass
                
        file_name = os.path.join(root, f"{strid} {subtitle}.mp4" if strid else f"{name}.mp4")
        audio = os.path.join(dir_path, dir_name, "audio.m4s")
        video = os.path.join(dir_path, dir_name, "video.m4s")
        
        merge_video_and_audio(video, audio, file_name, False)
        delete(dir_path)

    return name

if __name__ == "__main__":
    cmd("ffmpeg -version")
    root_path = "./"
    for file in os.listdir(root_path):
        path = os.path.join(root_path, file)
        if os.path.isdir(path):
            name = convert(path)
            if name:
                rename(path, os.path.join(root_path, name))
