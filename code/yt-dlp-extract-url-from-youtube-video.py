import subprocess
import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs, unquote

FFPROBE = "./ffprobe.exe"

def extract_video_id_from_query(qs):
    vid_list = qs.get("v")
    if not vid_list:
        return None
    vid = vid_list[0]
    return vid[:11] if len(vid) >= 11 else None

def find_first_youtube_video_url(text):
    YOUTUBE_HOSTS = {
        "www.youtube.com", "youtube.com", "m.youtube.com",
        "youtu.be", "www.youtu.be", "music.youtube.com"
    }
    for token in text.split():
        token = token.strip('\'"<>.,;:()[]{}')
        if not (token.startswith("http://") or token.startswith("https://")):
            if token.startswith("www.") or token.startswith("youtube.") or token.startswith("youtu.be"):
                token = "https://" + token
            else:
                continue
        try:
            p = urlparse(token)
        except Exception:
            continue
        host = p.netloc.lower()
        if host in YOUTUBE_HOSTS:
            if host.endswith("youtu.be"):
                video_id = p.path.lstrip('/')
                if len(video_id) >= 11:
                    return token, video_id[:11]
            if host.endswith("youtube.com") or host.endswith("m.youtube.com") or host.endswith("music.youtube.com"):
                if p.path == "/watch":
                    qs = parse_qs(p.query)
                    vid = extract_video_id_from_query(qs)
                    if vid:
                        return token, vid
                parts = [part for part in p.path.split("/") if part]
                if parts:
                    if parts[0] in ("embed", "v") and len(parts) > 1:
                        candidate = parts[1]
                        if len(candidate) >= 11:
                            return token, candidate[:11]
                    last = parts[-1]
                    if len(last) >= 11 and parts[0] not in ("playlist", "channel", "user", "c"):
                        return token, last[:11]
    return None, None
    
def custom_script(comment: str) -> str:
    url, id = find_first_youtube_video_url(comment)
    if id is None:
        print("error on " + str(comment))
        return ""
    return "youtube " + str(id)


def get_comment_from_mp4(path: Path) -> Optional[str]:
    cmd = [
        FFPROBE,
        "-v", "error",
        "-print_format", "json",
        "-show_entries", "format_tags",
        str(path)
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        return None
    out_bytes = proc.stdout or b""
    out_text = out_bytes.decode("utf-8", errors="replace")
    try:
        data = json.loads(out_text)
    except json.JSONDecodeError:
        return None
    tags = data.get("format", {}).get("tags", {}) or {}
    for key in ("comment", "Comment", "COMMENT"):
        if key in tags:
            val = tags[key]
            if isinstance(val, bytes):
                return val.decode("utf-8", errors="replace")
            return str(val)
    return None

def process_video(video_dir: str) -> None:
    dir_path = Path(video_dir)
    if not dir_path.is_dir():
        return

    print("entering " + str(dir_path))
    mp4_files = sorted(dir_path.glob("*.mp4"))
    out_path = dir_path / "archive.txt"
    dedup_path = dir_path / "dedup.txt"

    line_to_files: dict[str, List[str]] = {}
    ordered_lines: List[str] = []

    for mp4 in mp4_files:
        try:
            comment = get_comment_from_mp4(mp4)
        except Exception as e:
            print(f"ffprobe error for {mp4.name}: {e}")
            continue
        if comment is None:
            print("no comment in " + str(mp4))
            continue
        try:
            result = custom_script(comment)
        except Exception as e:
            print(f"custom_script error for {mp4.name}: {e}")
            continue
        result_line = result.replace("\r", " ").replace("\n", " ")
        ordered_lines.append(result_line)
        line_to_files.setdefault(result_line, []).append(mp4.name)

    with out_path.open("w", encoding="utf-8") as f:
        for line in ordered_lines:
            f.write(line + "\n")

    dedup_entries = {line: files for line, files in line_to_files.items() if len(files) > 1}

    if dedup_entries:
        with dedup_path.open("w", encoding="utf-8") as f:
            json.dump(dedup_entries, f, ensure_ascii=False, indent=2)

    total_repeated_lines = len(dedup_entries)
    total_repeated_files = sum(len(files) for files in dedup_entries.values())
    print(f"dedupe: {total_repeated_lines} repeated lines across {total_repeated_files} files")

def main():
    root = Path(str("./youtube"))
    for child in sorted(root.iterdir()):
        if child.is_dir():
            process_video(str(child))

if __name__ == "__main__":
   #main()
   process_video(str("./youtube/1"))
