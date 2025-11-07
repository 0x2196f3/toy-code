#!/usr/bin/env python3

import os
import json
from pathlib import Path

ROOT = Path(".").resolve()
DEST_PREFIX = "/data"

def find_gguf_files(root: Path):
    gguf_paths = []
    for p in root.rglob("*.gguf"):
        if p.is_file() and p.name.endswith(".gguf") and "mmproj" not in p.name:
            gguf_paths.append(p)
    return sorted(gguf_paths)

def model_name_from_file(path: Path):
    return path.name[:-5]

def build_models_dict(gguf_paths):
    models = {}
    for p in gguf_paths:
        name = model_name_from_file(p)
        rel = p.resolve().relative_to(ROOT.resolve())
        model_path = DEST_PREFIX + "/" + "/".join(rel.parts)
        cmd = '/app/llama-server --port ${PORT} -m ' + model_path + ' -ngl 99 -c 131072'
        models[name] = {"cmd": cmd}
    return models

def json_to_yaml_manual(data: dict) -> str:
    lines = []
    lines.append("models:")
    models = data.get("models", {})
    for model_name in sorted(models.keys()):
        entry = models[model_name]
        lines.append(f'  "{model_name}":')
        cmd_value = entry.get("cmd", "")
        safe_cmd = cmd_value.replace('"', '\\"')
        lines.append(f'    cmd: "{safe_cmd}"')
    return "\n".join(lines) + "\n"

def main():
    gguf_files = find_gguf_files(ROOT)
    if not gguf_files:
        print("# No .gguf files found under current directory")
        return

    models = build_models_dict(gguf_files)
    payload = {"models": models}

    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    yaml_text = json_to_yaml_manual(payload)

    print("# JSON (intermediate):")
    print(json_text)
    print("\n# Generated llama-swap YAML:")
    print(yaml_text)
    
    out_path = Path("template.yaml")
    out_path.write_text(yaml_text, encoding="utf-8")
    print(f"Saved YAML to {out_path.resolve()}")

if __name__ == "__main__":
    main()
