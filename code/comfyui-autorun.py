import os
import json
import shutil
from urllib import request, error
from datetime import datetime
from PIL import Image
from pathlib import Path

PYTHON_EXE_PATH = "../ComfyUI_windows_portable/python_embeded/python.exe"

COMFYUI_MAIN_PY_PATH = "../ComfyUI_windows_portable/ComfyUI/main.py"

def extract_key_from_png(img_path: str, key: str) -> str|None:
    try:
        with Image.open(img_path) as img:
            if key in img.info:
                return img.info[key]
            
    except FileNotFoundError:
        print(f"file not found : {img_path}")
    except Exception as e:
        print(f"error loading {key} from {img_path} : {e}")
    return None


def customize_workflow(img_path: str):
    prompt_str = extract_key_from_png(img_path, "prompt")
    workflow_str = extract_key_from_png(img_path, "workflow")

    p = Path(img_path)
    parts = list(p.parts)

    if len(parts) >= 2:
        new_parts = parts[1:]
    else:
        new_parts = parts[:]

    if len(new_parts) >= 1:
        new_parts[-1] = "img"
    out = "/".join(new_parts)

    workflow_str = (
        workflow_str
        .replace("normal quality", ",normal quality,realistic,")
    )

    prompt_str = (
        prompt_str
        .replace("normal quality", ",normal quality,realistic,")
    )

    prompt_dict = json.loads(prompt_str)
    workflow_dict = json.loads(workflow_str)

    payload = {
        "prompt": prompt_dict,
        "client_id": 0,
        "extra_data": {"extra_pnginfo": {"workflow": workflow_dict}},
    }

    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        "http://127.0.0.1:8188/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    for attempt in range(1):
        try:
            resp = request.urlopen(req, timeout=10)
            body = resp.read().decode("utf-8")
            print("Queued prompt, response:", body)
            break
        except error.URLError as e:
            print(f"Connection failed (attempt {attempt+1}): {e}. Retrying in 1s...")
    else:
        print("fail to send request")
    

ERROR_DIR = "./error"
INPUT_IMAGES_DIR = "./images"

def main():
    def make_relative(path):
        return os.path.relpath(path, start=os.getcwd())

    def move_to_error_preserve_structure(src_path):
        rel = make_relative(src_path)
        dest_path = os.path.join(ERROR_DIR, rel)
        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.exists(dest_path):
            os.remove(dest_path)
        shutil.move(src_path, dest_path)
        return dest_path

    if not os.path.exists(PYTHON_EXE_PATH):
        print(f"Error: Specified Python path does not exist: {PYTHON_EXE_PATH}")
        return
    if not os.path.exists(COMFYUI_MAIN_PY_PATH):
        print(f"Error: ComfyUI main.py path does not exist: {COMFYUI_MAIN_PY_PATH}")
        return
    if not os.path.exists(INPUT_IMAGES_DIR):
        print(f"Error: Input images directory does not exist: {INPUT_IMAGES_DIR}")
        return

    image_paths = []
    for root, _, files in os.walk(INPUT_IMAGES_DIR):
        for name in files:
            if name.lower().endswith('.png'):
                full_path = os.path.join(root, name)
                rel_path = make_relative(full_path)
                image_paths.append(rel_path)

    print(f"Found {len(image_paths)} PNG files to process.")

    for rel_img_path in image_paths:
        try:
            customize_workflow(rel_img_path)
        except BaseException as e:
            print(f"Error processing '{rel_img_path}': {e}")
            try:
                abs_src = os.path.abspath(rel_img_path)
                if os.path.exists(abs_src):
                    moved = move_to_error_preserve_structure(abs_src)
                    print(f"Moved error file to: {moved}")
                else:
                    print(f"Source file not found (cannot move): {abs_src}")
            except Exception as mv_e:
                print(f"Failed to move error file '{rel_img_path}': {mv_e}")


        
if __name__ == "__main__":
    main()