import os
import subprocess
import concurrent.futures
import queue
import time

PRESET = 3
CRF = 28
OUTPUT_PREFIX = "av1_opus_"

FFMPEG_PATH = "./ffmpeg.exe" if os.name == "nt" else "./ffmpeg"
MKVMERGE_PATH = "./mkvmerge.exe" if os.name == "nt" else "./mkvmerge"

if os.name == "nt":
    AFFINITY_GROUPS = [
        list(range(0, 16)),
        list(range(16, 32))
    ]
else:
    AFFINITY_GROUPS = [
        list(range(0, 8)) + list(range(16, 24)),
        list(range(8, 16)) + list(range(24, 32))
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
    tmp_all = "tmp_" + out_file 
    
    print("\nStart: " + input_file + " on group " + str(group_idx))
    
    ffmpeg_args = [
        "-y", "-i", input_file,
        "-map", "0", 
        "-c", "copy", 
        "-c:V", "libsvtav1", "-preset", str(PRESET), "-crf", str(CRF),
        "-pix_fmt", "yuv420p10le", "-svtav1-params", "tune=0:keyint=240:enable-overlays=1:scd=1",
        "-c:a", "libopus", "-b:a", "192k",
        "-map_metadata", "0", "-map_chapters", "0",
        tmp_all
    ]
    
    if os.name == "nt":
        cmd1 = ["cmd.exe", "/c", "start", "/b", "/wait", "/affinity", mask_str, FFMPEG_PATH] + ffmpeg_args
    else:
        cmd1 = ["taskset", "-c", mask_str, FFMPEG_PATH] + ffmpeg_args
        
    print("Executing FFmpeg: " + " ".join(cmd1))
    
    t0_ffmpeg = time.time()
    r1 = subprocess.run(cmd1, capture_output=True, text=True, errors="replace")
    t1_ffmpeg = time.time()
    ffmpeg_time = t1_ffmpeg - t0_ffmpeg
    
    if r1.returncode != 0:
        if os.path.exists(tmp_all): os.remove(tmp_all)
        task_queue.put(group_idx)
        return "FFmpeg Error: " + input_file + "\n" + r1.stderr
        
    cmd2 = [MKVMERGE_PATH, "-o", out_file, tmp_all]
    
    print("Executing MKVMerge: " + " ".join(cmd2))
    
    t0_mkvmerge = time.time()
    r2 = subprocess.run(cmd2, capture_output=True, text=True, errors="replace")
    t1_mkvmerge = time.time()
    mkvmerge_time = t1_mkvmerge - t0_mkvmerge
    
    if os.path.exists(tmp_all): os.remove(tmp_all)
    
    task_queue.put(group_idx)
    
    if r2.returncode not in (0, 1):
        if os.path.exists(out_file): os.remove(out_file)
        return "MKVMerge Error: " + input_file + "\n" + r2.stderr
        
    total_task_time = ffmpeg_time + mkvmerge_time
    
    return (f"Done: {input_file} -> {out_file}\n"
            f"  > FFmpeg time: {ffmpeg_time:.2f}s\n"
            f"  > MKVMerge time: {mkvmerge_time:.2f}s\n"
            f"  > Total task time: {total_task_time:.2f}s\n")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    files = [f for f in os.listdir('.') if f.lower().endswith('.mkv') and not f.startswith(OUTPUT_PREFIX)]
    if not files:
        print("No files found to process.")
        input("\nPress Enter to exit...")
        return
        
    global_start = time.time()
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        fs = {executor.submit(process, f): f for f in files}
        for future in concurrent.futures.as_completed(fs):
            print(future.result())

    global_end = time.time()
    total_elapsed = global_end - global_start
    avg_elapsed = total_elapsed / len(files) if files else 0
    
    print("-" * 40)
    print("All tasks completed!")
    print(f"Files processed: {len(files)}")
    print(f"Total time elapsed: {total_elapsed:.2f}s")
    print(f"Average time per file: {avg_elapsed:.2f}s")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()