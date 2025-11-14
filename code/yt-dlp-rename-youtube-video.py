import subprocess
import json
import unicodedata
from pathlib import Path
from typing import List, Tuple, Optional
import shutil
import os
import re
from urllib.parse import urlparse, parse_qs, unquote
import itertools
FFPROBE = "./ffprobe.exe"

MAX_BYTES=255

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
    
    
def sanitize_filename(s, restricted=False, is_id=False):
    NO_DEFAULT = False
    ACCENT_CHARS = dict(zip('ÂÃÄÀÁÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖŐØŒÙÚÛÜŰÝÞßàáâãäåæçèéêëìíîïðñòóôõöőøœùúûüűýþÿ',
                        itertools.chain('AAAAAA', ['AE'], 'CEEEEIIIIDNOOOOOOO', ['OE'], 'UUUUUY', ['TH', 'ss'],
                                        'aaaaaa', ['ae'], 'ceeeeiiiionooooooo', ['oe'], 'uuuuuy', ['th'], 'y')))
    """Sanitizes a string so it could be used as part of a filename.
    @param restricted   Use a stricter subset of allowed characters
    @param is_id        Whether this is an ID that should be kept unchanged if possible.
                        If unset, yt-dlp's new sanitization rules are in effect
    """
    if s == '':
        return ''

    def replace_insane(char):
        if restricted and char in ACCENT_CHARS:
            return ACCENT_CHARS[char]
        elif not restricted and char == '\n':
            return '\0 '
        elif is_id is NO_DEFAULT and not restricted and char in '"*:<>?|/\\':
            # Replace with their full-width unicode counterparts
            return {'/': '\u29F8', '\\': '\u29f9'}.get(char, chr(ord(char) + 0xfee0))
        elif char == '?' or ord(char) < 32 or ord(char) == 127:
            return ''
        elif char == '"':
            return '' if restricted else '\''
        elif char == ':':
            return '\0_\0-' if restricted else '\0 \0-'
        elif char in '\\/|*<>':
            return '\0_'
        if restricted and (char in '!&\'()[]{}$;`^,#' or char.isspace() or ord(char) > 127):
            return '' if unicodedata.category(char)[0] in 'CM' else '\0_'
        return char

    # Replace look-alike Unicode glyphs
    if restricted and (is_id is NO_DEFAULT or not is_id):
        s = unicodedata.normalize('NFKC', s)
    s = re.sub(r'[0-9]+(?::[0-9]+)+', lambda m: m.group(0).replace(':', '_'), s)  # Handle timestamps
    result = ''.join(map(replace_insane, s))
    if is_id is NO_DEFAULT:
        result = re.sub(r'(\0.)(?:(?=\1)..)+', r'\1', result)  # Remove repeated substitute chars
        STRIP_RE = r'(?:\0.|[ _-])*'
        result = re.sub(f'^\0.{STRIP_RE}|{STRIP_RE}\0.$', '', result)  # Remove substitute chars from start/end
    result = result.replace('\0', '') or '_'

    if not is_id:
        while '__' in result:
            result = result.replace('__', '_')
        result = result.strip('_')
        # Common case of "Foreign band name - English song title"
        if restricted and result.startswith('-_'):
            result = result[2:]
        if result.startswith('-'):
            result = '_' + result[len('-'):]
        result = result.lstrip('.')
        if not result:
            result = '_'
    return result
    
def _yt_dlp_style_sanitize(name: str) -> str:
    if name is None:
        return None
    # Normalize (NFC)
    name = unicodedata.normalize("NFC", name)

    # Remove NUL and control chars (0x00-0x1F and DEL), replace with space
    name = "".join(ch if (31 < ord(ch) < 0x7f or ord(ch) > 0x9f) else " " for ch in name)

    # Collapse newlines and carriage returns to spaces
    name = name.replace("\r", " ").replace("\n", " ")

    # Replace path separators and common unsafe chars with underscore
    for bad in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'):
        name = name.replace(bad, "_")

    # Prevent path traversal and repeated dots
    while ".." in name:
        name = name.replace("..", "_")

    # Strip leading/trailing whitespace and leading dot (avoid hidden files)
    name = name.strip()
    name = name.lstrip(".")

    # Truncate to MAX_BYTES without breaking UTF-8
    encoded = name.encode("utf-8", errors="ignore")
    if len(encoded) > MAX_BYTES:
        encoded = encoded[:MAX_BYTES]
        name = encoded.decode("utf-8", errors="ignore")
    else:
        name = encoded.decode("utf-8", errors="ignore")

    if not name:
        return None
    return name

def custom_script(title: str, id: str) -> str:
    """
    Template: "[$ID]_$TITLE" where TITLE is title[0:50] (characters),
    then sanitized in a yt-dlp-like way.
    """
    if title is None:
        title = ""
    if id is None:
        id = ""

    truncated = title[:50]
    # basic sanitization for id (avoid path separators)
    id_safe = str(id).replace("/", "_").replace("\\", "_").strip()

    combined = f"{truncated}_[{id_safe}]"
    safe = sanitize_filename(combined)
    return safe

def _decode_tag_value(val) -> str:
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)

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
        # ffprobe returned non-zero -> treat as skip
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
            return _decode_tag_value(tags[key])
    return None


def get_title_from_mp4(path: Path) -> Optional[str]:
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
    try:
        out_text = out_bytes.decode("utf-8", errors="replace")
    except Exception:
        out_text = ""

    try:
        data = json.loads(out_text)
    except json.JSONDecodeError:
        return None

    tags = data.get("format", {}).get("tags", {}) or {}

    if "title" in tags:
        return _decode_tag_value(tags["title"]).strip() or None

    
    comment_val = tags.get("comment")
    if comment_val is None:
        return None
    comment = _decode_tag_value(comment_val)

    # print(comment)
    marker = "https://github.com/Tyrrrz/YoutubeDownloader"
    if marker not in comment:
        return None

    # split into lines (handle \r\n, \r, \n), find the line that starts with "Video"
    lines = comment.splitlines()
    video_line = None
    for line in lines:
        # strip leading whitespace, then check for "Video" prefix
        if line.lstrip().startswith("Video"):
            video_line = line.lstrip()
            break
    if video_line is None:
        return None

    # expected format: "Video: <title>" or "Video: <title> / ..." — take after first colon
    colon_idx = video_line.find(":")
    if colon_idx == -1:
        # no colon, take remainder after "Video"
        title_part = video_line[len("Video"):].strip()
    else:
        title_part = video_line[colon_idx + 1 :].strip()

    # if the title_part contains " /" (trailing separators), cut at first " /"
    slash_idx = title_part.find(" /")
    if slash_idx != -1:
        title = title_part[:slash_idx].strip()
    else:
        title = title_part.strip()

    return title or None


def rename_videos(video_dir: str, dry_run: bool = True) -> None:
    dir_path = Path(video_dir)
    if not dir_path.is_dir():
        return
    print("entering " + str(dir_path))
    mp4_files = sorted(dir_path.glob("*.mp4"))

    failed_dir = dir_path / "failed"
    failures: List[Tuple[Path, str]] = []

    if not dry_run:
        try:
            failed_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(failed_dir, 0o777)
            except Exception:
                pass
        except Exception as e:
            err = f"could not create failed dir {failed_dir}: {e}"
            print(err)
            failures.append((dir_path, err))

    for mp4 in mp4_files:
        title = get_title_from_mp4(mp4)
        if title is None:
            print("no title in " + str(mp4))
            failures.append((mp4, "no title in file"))
            _move_to_failed(mp4, failed_dir, dry_run, failures)
            continue
            
        comment = get_comment_from_mp4(mp4)
        if comment is None:
            print("no title in comment " + str(mp4))
            failures.append((mp4, "no title in file comment"))
            _move_to_failed(mp4, failed_dir, dry_run, failures)
            continue
            
        id = find_first_youtube_video_url(comment)
        if id is None:
            print("no id in " + str(mp4))
            failures.append((mp4, "no id in comments"))
            _move_to_failed(mp4, failed_dir, dry_run, failures)
            continue

        try:
            result = custom_script(title, id[1])
        except Exception as e:
            print(f"custom_script failed for {mp4}: {e}")
            failures.append((mp4, f"custom_script exception: {e}"))
            _move_to_failed(mp4, failed_dir, dry_run, failures)
            continue

        if not result:
            print(f"custom_script returned empty result for {mp4}")
            failures.append((mp4, "custom_script returned empty result"))
            _move_to_failed(mp4, failed_dir, dry_run, failures)
            continue

        safe_name = str(result).strip().replace("/", "_").replace("\\", "_")
        new_path = mp4.with_name(f"{safe_name}.mp4")

        if mp4.resolve() == new_path.resolve():
            print(f"skip rename (same name): {mp4.name}")
            continue

        if dry_run:
            print(f"DRY-RUN: would rename '{mp4.name}' -> '{new_path.name}'")
            continue
        else:
            try:
                mp4.rename(new_path)
                print(f"renamed '{mp4.name}' -> '{new_path.name}'")
            except Exception as e:
                print(f"failed to rename '{mp4.name}' -> '{new_path.name}': {e}")
                failures.append((mp4, f"rename failed: {e}"))
                _move_to_failed(mp4, failed_dir, dry_run, failures, after_rename=True)


    if failures:
        print("\nSummary of failures: " + str(len(failures)))
        for path, reason in failures:
            print(f"- {path}: {reason}")


def _move_to_failed(mp4_path: Path, failed_dir: Path, dry_run: bool, failures: List[Tuple[Path, str]], after_rename: bool = False) -> None:
    target = failed_dir / mp4_path.name
    if dry_run:
        print(f"DRY-RUN: would move failed file '{mp4_path.name}' -> '{target}'")
        return

    try:
        # Use replace to atomically move/overwrite if target exists.
        # On Windows, Path.replace works; if fail, fallback to shutil.move (which may not overwrite).
        try:
            mp4_path.replace(target)
        except Exception:
            # shutil.move will overwrite on some platforms if we remove target first
            if target.exists():
                try:
                    target.unlink()
                except Exception as e_rm:
                    raise RuntimeError(f"could not remove existing target {target}: {e_rm}")
            shutil.move(str(mp4_path), str(target))
        print(f"moved failed file '{mp4_path.name}' -> '{target}'")
        try:
            os.chmod(target, 0o777)
        except Exception:
            pass
    except Exception as e:
        reason = f"move failed{' after rename' if after_rename else ''}: {e}"
        print(f"failed to move '{mp4_path.name}' to failed dir: {e}")
        failures.append((mp4_path, reason))


def create_empty_files(video_dir: str, dry_run: bool = True) -> None:
    src_dir = Path(video_dir)
    if not src_dir.is_dir():
        return

    tmp_dir = Path("./tmp")
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"failed to create tmp dir {tmp_dir}: {e}")
        return

    mp4_files = sorted(src_dir.glob("*.mp4"))
    for mp4 in mp4_files:
        title = get_title_from_mp4(mp4)
        if title is None:
            print(f"no title in {mp4}")
            continue

        safe_name = str(title).strip().replace("/", "_").replace("\\", "_")
        target = tmp_dir / f"{safe_name}.mp4"

        if target.exists() and target.resolve() == mp4.resolve():
            print(f"skip create (same file): {target.name}")
            continue

        if dry_run:
            print(f"DRY-RUN: would create empty file '{target}'")
        else:
            try:
                target.open("wb").close()
                print(f"created empty file '{target}'")
            except Exception as e:
                print(f"failed to create '{target}': {e}")


def batch_rename(video_dir: str, dry_run: bool = True):
    root = Path(str(video_dir))
    for child in sorted(root.iterdir()):
        if child.is_dir():
            rename_videos(str(child), dry_runs)
            input("finished" + str(child) + "\n")

if __name__ == "__main__":
   rename_videos(str("./LAYERS_CLASSIC"), dry_run=False)
   # batch_rename(str("./youtube"), dry_run=False)
