from __future__ import annotations
import argparse
import os
import sys
import shutil
import subprocess
import threading
import queue
from typing import Optional


def print_cmd(cmd: list[str]) -> None:
    safe_parts = []
    for part in cmd:
        if not part:
            safe_parts.append("''")
        elif any(c in part for c in " \t\n'\"\\"):
            # prefer single quotes and escape existing single quotes
            safe_parts.append("'" + part.replace("'", "'\"'\"'") + "'")
        else:
            safe_parts.append(part)
    print("cmd = " + " ".join(safe_parts))
    
def _handle_line(tag: str, line: str, members_path: str, age_path: str):
    if tag == "stderr":
        if not line.endswith("\n"):
            line_to_print = line + "\n"
        else:
            line_to_print = line
        try:
            sys.stderr.write(line_to_print)
            sys.stderr.flush()
        except Exception:
            pass
    else:
        if not line.endswith("\n"):
            line_to_print = line + "\n"
        else:
            line_to_print = line
        try:
            sys.stdout.write(line_to_print)
            sys.stdout.flush()
        except Exception:
            pass

    lower = (line or "").lower()
    tag_result = extract_youtube_tag_from_line(line)
    if tag_result is not None:
        if "members-only" in lower:
            _append_line_safe(members_path, tag_result)
        if "sign in to confirm your age" in lower or "age-restricted" in lower:
            _append_line_safe(age_path, tag_result)

def _append_line_safe(path: str, text: str):
    try:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass
        

def extract_youtube_tag_from_line(line: str) -> Optional[str]:
    if line is None:
        return None

    s = line.rstrip("\n")
    lower = s.lower()

    if not ("members-only" in lower or "sign in to confirm your age" in lower):
        return None

    target = "youtube"
    L = len(s)
    tlen = len(target)

    start = -1
    for i in range(L):
        if s[i] == '[':
            if i + 1 + tlen <= L and lower[i+1:i+1+tlen] == target:
                start = i
                break
    if start == -1:
        return None

    colon_idx = -1
    for j in range(start + 1, L):
        if s[j] == ':':
            colon_idx = j
            break
    if colon_idx == -1:
        return None

    sub = s[start:colon_idx]

    cleaned = []
    for ch in sub:
        if ch in ('[', ']', '"'):
            continue
        cleaned.append(ch)
    result = "".join(cleaned)
    return result


def enqueue_lines(stream, q: queue.Queue, tag: str):
    try:
        for line in iter(stream.readline, ""):
            if line == "":
                break
            q.put((tag, line))
    finally:
        stream.close()
        
def dedupe_file(path):
    try:
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        seen = set()
        out_lines = []
        for ln in lines:
            key = ln.rstrip("\n")
            if key not in seen:
                seen.add(key)
                out_lines.append(ln if ln.endswith("\n") else ln + "\n")
        new_content = "".join(out_lines)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception:
        pass
        
def download_single(url: str, resolution: str = "4K") -> int:
    yt_dlp_exe = os.path.join(".", "yt-dlp.exe")
    if not os.path.isfile(yt_dlp_exe):
        found = shutil.which("yt-dlp.exe") or shutil.which("yt-dlp")
        if found:
            yt_dlp_exe = found

    cmd = [yt_dlp_exe]

    if resolution == "4K":
        cmd += ["-f", "bv*+ba+ba.1"]
    elif resolution == "1080P":
        cmd += ["-S", "+res:1080,br"]
    elif resolution == "480P":
        cmd += ["-S", "+res:480,br"]
    elif resolution == "360P":
        cmd += ["-S", "+res:360,br"]
    else:
        cmd += ["-S", "+res:720,br"]
    

    cmd += [
        "--embed-thumbnail",
        "--embed-metadata",
        "--embed-subs",
        "--embed-chapters",
        "--no-playlist",
        "--paths", "temp:./tmp",
        "-o", fr".\download\%(title.0:50)s_[%(id)s].%(ext)s",
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-t", "sleep",
        "--compat-options", "no-live-chat",
        url,
    ]

    print_cmd(cmd)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print(f"ERROR: yt-dlp executable not found: {yt_dlp_exe}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: failed to start yt-dlp: {e}", file=sys.stderr)
        return 1

    q: queue.Queue = queue.Queue()
    t_out = threading.Thread(target=enqueue_lines, args=(proc.stdout, q, "stdout"), daemon=True)
    t_err = threading.Thread(target=enqueue_lines, args=(proc.stderr, q, "stderr"), daemon=True)
    t_out.start()
    t_err.start()

    try:
        while True:
            try:
                tag, line = q.get(timeout=0.1)
            except queue.Empty:
                if proc.poll() is not None:
                    while not q.empty():
                        tag, line = q.get_nowait()
                        _handle_line(tag, line, None, None)
                    break
                continue
            _handle_line(tag, line, None, None)
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        return 1

    retcode = proc.wait()
    return retcode

        
def download_batch(archive_path: str, url: str, resolution: str = "720P", append_mode: bool = False) -> int:
    if not os.path.isfile(archive_path):
        print(f"ERROR: archive file does not exist: {archive_path}", file=sys.stderr)
        return 1

    parent_dir = os.path.dirname(archive_path)
    if not parent_dir:
        print(f"ERROR: archive file must be inside a channel directory: {archive_path}", file=sys.stderr)
        return 1

    channel_name = os.path.basename(parent_dir)
    if not channel_name:
        print(f"ERROR: could not determine channel name from archive path: {archive_path}", file=sys.stderr)
        return 1

    tmp_channel_dir = os.path.join(".", "download", channel_name)
    os.makedirs(tmp_channel_dir, exist_ok=True)

    yt_dlp_exe = os.path.join(".", "yt-dlp.exe")
    if not os.path.isfile(yt_dlp_exe):
        found = shutil.which("yt-dlp.exe") or shutil.which("yt-dlp")
        if found:
            yt_dlp_exe = found

    cmd = [yt_dlp_exe]
    cmd += ["--download-archive", archive_path]
    if append_mode:
        cmd += ["--break-on-existing"]

    if resolution == "4K":
        cmd += ["-f", "bv*+ba+ba.1"]
    elif resolution == "1080P":
        cmd += ["-S", "+res:1080,br"]
    elif resolution == "480P":
        cmd += ["-S", "+res:480,br"]
    elif resolution == "360P":
        cmd += ["-S", "+res:360,br"]
    else:
        cmd += ["-S", "+res:720,br"]

    cmd += [
        "--embed-thumbnail",
        "--embed-metadata",
        "--embed-subs",
        "--embed-chapters",
        "-o", fr".\download\{channel_name}\%(title.0:50)s_[%(id)s].%(ext)s",
        "--paths", "temp:./tmp",
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-t", "sleep",
        "--compat-options", "no-live-chat",
        url,
    ]
    
    print_cmd(cmd)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print(f"ERROR: yt-dlp executable not found: {yt_dlp_exe}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: failed to start yt-dlp: {e}", file=sys.stderr)
        return 1

    q: queue.Queue = queue.Queue()
    t_out = threading.Thread(target=enqueue_lines, args=(proc.stdout, q, "stdout"), daemon=True)
    t_err = threading.Thread(target=enqueue_lines, args=(proc.stderr, q, "stderr"), daemon=True)
    t_out.start()
    t_err.start()

    members_path = os.path.join(parent_dir, "members-only.txt")
    age_path = os.path.join(parent_dir, "age-restricted.txt")

    try:
        while True:
            try:
                tag, line = q.get(timeout=0.1)
            except queue.Empty:
                if proc.poll() is not None:
                    while not q.empty():
                        tag, line = q.get_nowait()
                        _handle_line(tag, line, members_path, age_path)
                    break
                continue
            _handle_line(tag, line, members_path, age_path)
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        dedupe_file(members_path)
        dedupe_file(age_path)
        return 1

    retcode = proc.wait()
    dedupe_file(members_path)
    dedupe_file(age_path)
    return retcode


def main(argv):
    p = argparse.ArgumentParser(prog="yt-dlp.py")
    p.add_argument("--resolution", "-r", choices=["4K", "1080P", "720P", "480P", "360P"], help='Video resolution (default 720P)')
    p.add_argument("--archive", help='Path to archive.txt (download archive)')
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help='URL to download')
    group.add_argument("--id", help='Channel ID without \'@\' (will be expanded to three URLs)')
    group.add_argument("--single", help='Single URL download; if set, other args are ignored')
    p.add_argument("--append", "-a", action="store_true", help='If set, add --break-on-existing to yt-dlp')
    p.add_argument("--no-stream", action="store_true", help='(Only for --id) Do not include the /streams URL when expanding a channel ID')

    args = p.parse_args(argv)
    resolution = args.resolution if args.resolution is not None else "720P"
    
    if args.single:
        return download_single(args.single, resolution)
        
    archive_path = os.path.abspath(args.archive) if args.archive else None
    append_mode = args.append
    
    if args.url:
        return download_batch(archive_path=archive_path, url=args.url, resolution=resolution, append_mode=append_mode)
    else:
        cid = args.id
        urls = [
            f"https://youtube.com/@{cid}/videos",
            f"https://youtube.com/@{cid}/shorts",
        ]
        if not args.no_stream:
            urls.append(f"https://youtube.com/@{cid}/streams")

        final_ret = 0
        for u in urls:
            ret = download_batch(archive_path=archive_path, url=u, resolution=resolution, append_mode=append_mode)
            if ret != 0:
                final_ret = ret
        return final_ret

if __name__ == "__main__":
    exit_code = main(sys.argv[1:])
    sys.exit(exit_code)
