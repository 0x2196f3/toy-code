import os
import json
import re
import sys
import urllib.request
from datetime import datetime

URL = "https://cloud.sbsub.com/data/data.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}
def fetch_json(url, headers, timeout=15):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        try:
            txt = body.decode("utf-8")
        except Exception:
            txt = body.decode("latin-1")
        return json.loads(txt)

try:
    top_json = fetch_json(URL, HEADERS)
except Exception as e:
    raise SystemExit(f"Failed to fetch or parse JSON from {URL}: {e}")

try:
    res = top_json["res"]
    if not isinstance(res, list) or len(res) == 0:
        raise KeyError("res is not a non-empty list")
    first = res[0]
    if not isinstance(first, list) or len(first) <= 4:
        raise KeyError("res[0] is not a list with at least 5 elements")
    DATA_JSON = first[4]
except Exception as e:
    raise SystemExit(f"Failed to extract DATA_JSON from fetched JSON: {e}")

if isinstance(DATA_JSON, str):
    try:
        data = json.loads(DATA_JSON)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Failed to parse DATA_JSON string: {e}")
elif isinstance(DATA_JSON, dict):
    data = DATA_JSON
else:
    raise SystemExit("DATA_JSON is neither a JSON string nor a dict")

DIR = "."

bracket_re = re.compile(r'^\[([^\]]+)\]')

def format_date_to_6digits(date_str):
    for fmt in ("%Y/%m/%d", "%Y/%-m/%-d", "%Y-%m-%d", "%Y-%-m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%y%m%d")
        except Exception:
            pass
    parts = re.split(r'\D+', date_str)
    parts = [p for p in parts if p]
    if len(parts) >= 3:
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            dt = datetime(year, month, day)
            return dt.strftime("%y%m%d")
        except Exception:
            pass
    digits = ''.join(re.findall(r'\d', date_str))
    if len(digits) >= 6:
        return digits[:6]
    return digits.zfill(6)
    
def sanitize_chars(s: str, replacement: str = "") -> str:
    """
    Remove or replace characters that are not allowed in Windows or Linux filenames.
    - Removes NUL (\\x00) and slash '/' (Linux path separator).
    - Removes Windows forbidden characters: <>:\"/\\|?*
    - Also removes ASCII control characters (U+0000..U+001F).
    - `replacement` is inserted in place of each forbidden character (default: remove).
    """
    if not isinstance(s, str):
        raise TypeError("s must be a str")

    forbidden = set('<>:"/\\|?*\x00')  # union of Windows forbidden + NUL; include '/' and '\\'
    out_chars = []
    for ch in s:
        if ord(ch) <= 0x1F:  # control characters U+0000..U+001F
            # treat as forbidden
            rep = replacement
        elif ch in forbidden:
            rep = replacement
        else:
            rep = ch
        if rep:
            out_chars.append(rep)
    return "".join(out_chars)
    

conflicts = []

for entry in os.listdir(DIR):

    path = os.path.join(DIR, entry)
    if not os.path.isfile(path):
        continue

    lower = entry.lower()
    if not (lower.endswith(".mp4") or lower.endswith(".mkv")):
        continue

    name = os.path.splitext(entry)[0]
    prefix_groups = []
    pos = 0
    while True:
        m = re.match(r'\[([^\]]+)\]', name[pos:])
        if not m:
            break
        prefix_groups.append(m.group(1))
        pos += m.end()        

    original_key = None
    original_key_idx = None
    for idx in (0, 2):
        if idx < len(prefix_groups):
            candidate = prefix_groups[idx]
            if re.fullmatch(r'[\d.]+', candidate):
                original_key = candidate
                original_key_idx = idx
                break
    if original_key is None:
        for idx, candidate in enumerate(prefix_groups):
            if re.fullmatch(r'[\d.]+', candidate):
                original_key = candidate
                original_key_idx = idx
                break
                
    if original_key is None:
        if len(name) >= 3:
            first3 = name[:3]
            try:
                val = int(first3)
            except ValueError as e:
                print(e)
                continue
            if 0 < val < 1000:
                name = ""
                original_key = str(val)
            else:
                continue
        else:
            continue

    if original_key not in data:
        continue

    value = data[original_key]
    if not isinstance(value, list) or len(value) <= 6:
        continue

    item2 = value[1]
    raw_item4 = value[3]
    if isinstance(raw_item4, dict) and raw_item4:
        joined = "".join(str(k) for k in raw_item4.keys())
        item4 = format_date_to_6digits(joined) if re.search(r'\d', joined) else joined
    else:
        item4 = format_date_to_6digits(str(raw_item4))

    raw_item7 = value[6]
    if isinstance(raw_item7, dict) and raw_item7:
        key_of_item7 = ".".join(str(k) for k in raw_item7.keys())
    else:
        key_of_item7 = str(raw_item7)

    rest = name[pos:]

    if original_key_idx == 2:
        remaining_after_orig = prefix_groups[original_key_idx+1:]
        other_brackets_after_removal = remaining_after_orig
    else:
        other_brackets_after_removal = [b for b in prefix_groups if b != original_key]

    other_brackets_after_removal = [b for b in other_brackets_after_removal if b != str(item2)]
    needle = f'[{item2}]'
    idx = rest.find(needle)
    if idx != -1:
        rest = rest[:idx] + rest[idx + len(needle):]

    ext = os.path.splitext(entry)[1]

    def sanitize(s):
        return str(s).replace('[', '').replace(']', '')

    new_brackets = [original_key, item2, item4, key_of_item7] + other_brackets_after_removal
    new_brackets = [sanitize(x) for x in new_brackets if x not in (None, '', 'None')]
    new_name_no_ext = "".join(f"[{b}]" for b in new_brackets) + rest
    new_filename = new_name_no_ext + ext
    new_filename = sanitize_chars(new_filename, "")
    new_path = os.path.join(DIR, new_filename)

    if os.path.exists(new_path):
        base, extension = os.path.splitext(new_filename)
        i = 1
        found = False
        while True:
            candidate = f"{base} ({i}){extension}"
            candidate_path = os.path.join(DIR, candidate)
            if not os.path.exists(candidate_path):
                new_path = candidate_path
                new_filename = candidate
                found = True
                break
            i += 1
            if i > 10000:
                conflicts.append(f"Too many conflicts for target {new_filename}; manual intervention required.")
                found = False
                break
        if not found and i > 10000:
            continue

    if os.path.exists(new_path):
        conflicts.append(f"Conflict: target already exists: {new_filename}")
        continue

    print(f"Renaming: {entry} -> {new_filename}")
    try:
        os.rename(path, new_path)
    except Exception as e:
        conflicts.append(f"Failed to rename {entry} -> {new_filename}: {e}")

if conflicts:
    print("\nWarnings/Errors encountered:")
    for c in conflicts:
        print("-", c)
    sys.exit(1)
