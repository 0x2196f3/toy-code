from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(".")
DB = ROOT / "sha256.json"

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

def build_db():
    data = {}
    for p in ROOT.iterdir():
        if p.is_file() and p.name != DB.name:
            data[p.name] = sha256_file(p)

    with DB.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"saved {DB}")

def restore_names():
    print(1)
    with DB.open("r", encoding="utf-8") as f:
        data = json.load(f)
    print(2)

    sha_to_name = {sha: name for name, sha in data.items()}
    print(3)

    for p in ROOT.iterdir():
        if not p.is_file() or p.name == DB.name:
            continue
        print(4)

        current_sha = sha256_file(p)
        new_name = sha_to_name.get(current_sha)
        if not new_name or new_name == p.name:
            continue
        print(5)

        target = p.with_name(new_name)
        if target.exists() and target.resolve() != p.resolve():
            print(f"skip (target exists): {p.name} -> {new_name}")
            continue
        print(6)

        os.rename(p, target)
        print(f"renamed: {p.name} -> {new_name}")

if __name__ == "__main__":
    # usage:
    #   python script.py hash
    #   python script.py restore
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "hash"

    if mode == "hash":
        build_db()
    elif mode == "restore":
        print(0)

        restore_names()
    else:
        print("use: hash | restore")
