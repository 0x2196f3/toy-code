from __future__ import annotations
import argparse
import io
import os
import shlex
import sys
import shutil
import subprocess
import threading
import queue
from typing import Optional

def print_cmd(cmd: list[str]) -> None:
    print("cmd = " + shlex.join(cmd))

def find_yt_dlp_executable() -> str:
    names = ["yt-dlp.exe", "yt-dlp"] if sys.platform == "win32" else ["yt-dlp"]

    for name in names:
        local_path = os.path.join(".", name)
        if os.path.isfile(local_path) and os.access(local_path, os.X_OK):
            return os.path.abspath(local_path)

    for name in names:
        found = shutil.which(name)
        if found:
            return found

    return "yt-dlp"


def extract_youtube_tag_from_line(line: str) -> Optional[str]:
    if not line:
        return None

    s = line.rstrip("\n")
    lower = s.lower()

    if not any(k in lower for k in ("members-only", "sign in to confirm your age", "age-restricted")):
        return None

    start = lower.find("[youtube]")
    if start == -1:
        return None

    colon_idx = s.find(":", start + 1)
    if colon_idx == -1:
        return None

    return s[start:colon_idx].replace("[", "").replace("]", "").replace('"', "")

def _append_line_safe(path: str, text: str):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass

def dedupe_file(path: str):
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        out_lines = list(dict.fromkeys(ln.rstrip("\n") + "\n" for ln in lines))
        
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
    except Exception:
        pass

def _handle_line(tag: str, line: str, members_path: Optional[str], age_path: Optional[str]):
    stream = sys.stderr if tag == "stderr" else sys.stdout
    
    try:
        stream.write(line)
        stream.flush()
    except Exception:
        pass

    if not members_path and not age_path:
        return

    lower = (line or "").lower()
    if any(k in lower for k in ("members-only", "sign in to confirm your age", "age-restricted")):
        tag_result = extract_youtube_tag_from_line(line)
        if tag_result:
            if "members-only" in lower and members_path:
                _append_line_safe(members_path, tag_result)
            if ("sign in to confirm your age" in lower or "age-restricted" in lower) and age_path:
                _append_line_safe(age_path, tag_result)

def enqueue_lines(stream, q: queue.Queue, tag: str):
    try:
        for line in iter(stream.readline, ""):
            if line == "":
                break
            q.put((tag, line))
    finally:
        stream.close()

def build_basic_cmd(resolution: str, force_ipvx: Optional[str], cookies_from_browser: Optional[str] = None,) -> list[str]:
    yt_dlp_exe = find_yt_dlp_executable()
    cmd = [yt_dlp_exe]

    res_map = {
        "4K": "2160",
        "1080P": "1080",
        "480P": "480",
        "360P": "360",
    }
    cmd += ["-S", f"+res:{res_map.get(resolution, '720')},br"]
        
    if force_ipvx:
        cmd += [force_ipvx]

    if cookies_from_browser:
            cmd += ["--cookies-from-browser", cookies_from_browser]
        
    cmd += [
        "-f", "bv+(ba[format_note*=original]/ba)",
        "--abort-on-unavailable-fragments",
        "--embed-thumbnail",
        "--embed-metadata",
        "--embed-subs",
        "--embed-chapters",
        "--paths", "temp:./tmp",
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-t", "sleep",
        "--compat-options", "no-live-chat",
        "--retries", "30"
    ]
    return cmd

def _run_yt_dlp(cmd: list[str], members_path: Optional[str] = None, age_path: Optional[str] = None,) -> int:
    print_cmd(cmd)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print(f"ERROR: yt-dlp executable not found: {cmd[0]}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: failed to start yt-dlp: {e}", file=sys.stderr)
        return 1

    stdout = io.TextIOWrapper(proc.stdout, newline="")
    stderr = io.TextIOWrapper(proc.stderr, newline="")

    q: queue.Queue = queue.Queue()
    threading.Thread(target=enqueue_lines, args=(stdout, q, "stdout"), daemon=True).start()
    threading.Thread(target=enqueue_lines, args=(stderr, q, "stderr"), daemon=True).start()

    try:
        while True:
            try:
                tag, line = q.get(timeout=0.1)
                _handle_line(tag, line, members_path, age_path)
            except queue.Empty:
                if proc.poll() is not None:
                    while not q.empty():
                        tag, line = q.get_nowait()
                        _handle_line(tag, line, members_path, age_path)
                    break
    except KeyboardInterrupt:
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except Exception:
            pass
        if members_path:
            dedupe_file(members_path)
        if age_path:
            dedupe_file(age_path)
        return 1

    retcode = proc.wait()
    if members_path:
        dedupe_file(members_path)
    if age_path:
        dedupe_file(age_path)
    return retcode

def download_single(url: str, resolution: str = "4K", force_ipvx: Optional[str] = None,cookies_from_browser: Optional[str] = None,) -> int:
    cmd = build_basic_cmd(resolution, force_ipvx, cookies_from_browser)
    cmd += [
        "--no-playlist",
        "-o", os.path.join("download", "%(title.0:50)s_[%(id)s].%(ext)s"),
        url,
    ]
    return _run_yt_dlp(cmd)

def download_batch(archive_path: Optional[str], url: str, resolution: str = "720P", append_mode: bool = False, force_ipvx: Optional[str] = None, cookies_from_browser: Optional[str] = None,) -> int:
    if not archive_path or not os.path.isfile(archive_path):
        print(f"ERROR: archive file does not exist: {archive_path}", file=sys.stderr)
        return 1

    parent_dir = os.path.dirname(os.path.abspath(archive_path))
    if not parent_dir:
        print(f"ERROR: archive file must be inside a channel directory: {archive_path}", file=sys.stderr)
        return 1
    
    channel_name = os.path.basename(parent_dir)
    if not channel_name:
        print(f"ERROR: could not determine channel name from archive path: {archive_path}", file=sys.stderr)
        return 1

    os.makedirs(os.path.join(".", "download", channel_name), exist_ok=True)
    cmd = build_basic_cmd(resolution, force_ipvx, cookies_from_browser)
    if append_mode:
        cmd += ["--break-on-existing"]
    
    cmd += [
        "--download-archive", archive_path,
        "-o", os.path.join("download", channel_name, "%(title.0:50)s_[%(id)s].%(ext)s"),
        url
    ]
    
    members_path = os.path.join(parent_dir, "members-only.txt")
    age_path = os.path.join(parent_dir, "age-restricted.txt")
    
    return _run_yt_dlp(cmd, members_path, age_path)

def download_list(list_path: str, resolution: str = "720P", force_ipvx: Optional[str] = None, cookies_from_browser: Optional[str] = None,) -> int:
    if not os.path.isfile(list_path):
        print(f"ERROR: list file does not exist: {list_path}", file=sys.stderr)
        return 1

    try:
        with open(list_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"ERROR: failed to read list file '{list_path}': {e}", file=sys.stderr)
        return 1

    final_ret = 0
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("http://") or line.startswith("https://"):
            url = line
        else:
            url = f"https://www.youtube.com/watch?v={line}"

        ret = download_single(url, resolution=resolution, force_ipvx=force_ipvx, cookies_from_browser=cookies_from_browser,)
        if ret != 0:
            final_ret = ret

    return final_ret

def main(argv):
    p = argparse.ArgumentParser(prog="yt-dlp.py")
    p.add_argument("--resolution", "-r", choices=["4K", "1080P", "720P", "480P", "360P"], help='Video resolution (default 720P)')
    p.add_argument("--archive", help='Path to archive.txt (download archive)')
    p.add_argument("--cookies-from-browser", help="Extract cookies from a browser (e.g. chrome, firefox, edge, opera, safari)")

    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Channel or Playlist URL to download")
    group.add_argument("--id", help="Channel ID without '@' (will be expanded to three URLs)")
    group.add_argument("--single", help="Single URL download")
    group.add_argument("--list", help="File list of URLs or video IDs to download")

    p.add_argument("--append", "-a", action="store_true", help='If set, add --break-on-existing to yt-dlp')
    p.add_argument("--no-shorts", dest="shorts", action="store_false", default=True, help="Include /shorts when expanding a channel (default: true).")
    p.add_argument("--no-streams", dest="streams", action="store_false", default=True, help="Include /streams when expanding a channel (default: true).")
    
    ip_group = p.add_mutually_exclusive_group()
    ip_group.add_argument("-4", dest="ipv", action="store_const", const="-4", help="Force IPv4 when downloading.")
    ip_group.add_argument("-6", dest="ipv", action="store_const", const="-6", help="Force IPv6 when downloading.")

    args = p.parse_args(argv)
    resolution = args.resolution or "720P"
    cookies_browser = args.cookies_from_browser

    if args.single:
        return download_single(args.single, resolution, force_ipvx=args.ipv, cookies_from_browser=cookies_browser,)

    if args.list:
        return download_list(args.list, resolution=resolution, force_ipvx=args.ipv, cookies_from_browser=cookies_browser,)

    archive_path = os.path.abspath(args.archive) if args.archive else None
    
    if args.url:
        return download_batch(archive_path=archive_path, url=args.url, resolution=resolution, append_mode=args.append, force_ipvx=args.ipv, cookies_from_browser=cookies_browser,)
    
    if args.id:
        urls = [f"https://youtube.com/@{args.id}/videos"]
        if args.shorts:
            urls.append(f"https://youtube.com/@{args.id}/shorts")
        if args.streams:
            urls.append(f"https://youtube.com/@{args.id}/streams")

        final_ret = 0
        for u in urls:
            ret = download_batch(archive_path=archive_path, url=u, resolution=resolution, append_mode=args.append, force_ipvx=args.ipv, cookies_from_browser=cookies_browser,)
            if ret != 0:
                final_ret = ret
        return final_ret
    
    return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))