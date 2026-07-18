import os
import subprocess
import concurrent.futures
import queue

FFMPEG_PATH = "./ffmpeg.exe" if os.name == "nt" else "./ffmpeg"
MKVMERGE_PATH = "./mkvmerge.exe" if os.name == "nt" else "./mkvmerge"
OUTPUT_PREFIX = "av1_"

AFFINITY_GROUPS = [
    list(range(0, 16)),
    list(range(16, 32))
]
THREADS = len(AFFINITY_GROUPS)

task_queue = queue.Queue()
for i in range(THREADS):
    task_queue.put(i)

def get_mask(cores):
    if os.name == "nt":
        mask = 0
        for c in cores:
            mask |= (1 << c)
        return hex(mask)[2:]
    else:
        return ",".join(map(str, cores))

def process(input_file):
    group_idx = task_queue.get()
    cores = AFFINITY_GROUPS[group_idx]
    mask_str = get_mask(cores)
    
    out_file = OUTPUT_PREFIX + input_file
    tmp_v = "v_" + out_file
    tmp_a = "a_" + out_file[:-4] + ".mka"
    
    print("Start: " + input_file + " on group " + str(group_idx))
    
    ffmpeg_args = [
        "-y", "-i", input_file,
        "-map", "0:v:0", "-c:v", "libsvtav1", "-preset", "3", "-crf", "28",
        "-pix_fmt", "yuv420p10le", "-svtav1-params", "tune=0:keyint=240:enable-overlays=1:scd=1",
        "-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1", tmp_v,
        "-map", "0:a:0", "-c:a", "libopus", "-b:a", "192k",
        "-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1", tmp_a
    ]
    
    if os.name == "nt":
        cmd1 = ["cmd.exe", "/c", "start", "/b", "/wait", "/affinity", mask_str, FFMPEG_PATH] + ffmpeg_args
    else:
        cmd1 = ["taskset", "-c", mask_str, FFMPEG_PATH] + ffmpeg_args
        
    r1 = subprocess.run(cmd1, capture_output=True, text=True, errors="replace")
    
    if r1.returncode != 0:
        if os.path.exists(tmp_v): os.remove(tmp_v)
        if os.path.exists(tmp_a): os.remove(tmp_a)
        task_queue.put(group_idx)
        return "FFmpeg Error: " + input_file + "\n" + r1.stderr
        
    cmd2 = [MKVMERGE_PATH, "-o", out_file, tmp_v, tmp_a]
    r2 = subprocess.run(cmd2, capture_output=True, text=True, errors="replace")
    
    if os.path.exists(tmp_v): os.remove(tmp_v)
    if os.path.exists(tmp_a): os.remove(tmp_a)
    
    task_queue.put(group_idx)
    
    if r2.returncode not in (0, 1):
        if os.path.exists(out_file): os.remove(out_file)
        return "MKVMerge Error: " + input_file + "\n" + r2.stderr
        
    return "Done: " + input_file + " -> " + out_file

def main():
    files = [f for f in os.listdir('.') if f.lower().endswith('.mkv') and not f.startswith(OUTPUT_PREFIX)]
    if not files:
        return
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        fs = {executor.submit(process, f): f for f in files}
        for future in concurrent.futures.as_completed(fs):
            print(future.result())

if __name__ == "__main__":
    main()
