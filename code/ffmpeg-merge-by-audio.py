"""
根据两个视频共有的日语音轨同步时间轴,自动移植国语音轨
"""
import os
import json
import subprocess
import shutil
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile


CACHE_FILE = "offsets.json"
DIR1 = "1"
DIR2 = "2"
OUT_DIR = "merged"
TEMP_DIR = "temp"


def get_executable(name):
    path = shutil.which(name)
    if path:
        return path
    
    local_exe = f"./{name}.exe"
    if os.path.exists(local_exe):
        return local_exe
        
    local_bin = f"./{name}"
    if os.path.exists(local_bin):
        return local_bin
        
    return None


FFMPEG_CMD = get_executable("ffmpeg")
MKVMERGE_CMD = get_executable("mkvmerge")


if not FFMPEG_CMD or not MKVMERGE_CMD:
    print("Error: ffmpeg or mkvmerge not found in system PATH or local directory.")
    sys.exit(1)


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def extract_audio(mkv_path, track_idx, out_wav):
    if os.path.exists(out_wav):
        os.remove(out_wav)
    
    cmd = [
        FFMPEG_CMD, '-y',
        '-i', mkv_path,
        '-map', f'0:a:{track_idx}',
        '-ac', '1', 
        '-ar', '8000', 
        '-c:a', 'pcm_s16le',
        out_wav
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(out_wav) and os.path.getsize(out_wav) > 0


def find_offset(ref_wav, target_wav):
    if not os.path.exists(ref_wav) or not os.path.exists(target_wav):
        return 0.0, -1.0


    sr1, sig1 = wavfile.read(ref_wav)
    sr2, sig2 = wavfile.read(target_wav)


    if sr1 != sr2:
        raise ValueError("Sample rates do not match")


    sig1 = sig1.astype(np.float32)
    sig2 = sig2.astype(np.float32)
    sig1 /= (np.max(np.abs(sig1)) + 1e-9)
    sig2 /= (np.max(np.abs(sig2)) + 1e-9)


    max_samples = 25 * 60 * sr1
    sig1 = sig1[:max_samples]
    sig2 = sig2[:max_samples]


    correlation = signal.fftconvolve(sig1, sig2[::-1], mode='full')
    peak_idx = np.argmax(correlation)
    peak_val = correlation[peak_idx]


    delay_samples = peak_idx - len(sig2) + 1
    delay_seconds = delay_samples / sr1


    return delay_seconds, peak_val


def get_mkvmerge_track_ids(mkv_path):
    cmd = [MKVMERGE_CMD, '--identify', '-J', mkv_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, encoding='utf-8')
    data = json.loads(result.stdout)
    audio_ids = []
    sub_ids = []
    for track in data.get('tracks', []):
        if track.get('type') == 'audio':
            audio_ids.append(track['id'])
        elif track.get('type') == 'subtitles':
            sub_ids.append(track['id'])
    return audio_ids, sub_ids


def main():
    ensure_dir(OUT_DIR)
    ensure_dir(TEMP_DIR)


    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            offsets_cache = json.load(f)
    else:
        offsets_cache = {}


    if not os.path.exists(DIR1) or not os.path.exists(DIR2):
        print("Error: Directory 1 or 2 does not exist.")
        return


    files1 = set(f for f in os.listdir(DIR1) if f.lower().endswith('.mkv'))
    files2 = set(f for f in os.listdir(DIR2) if f.lower().endswith('.mkv'))
    common_files = sorted(list(files1.intersection(files2)))


    for fname in common_files:
        path1 = os.path.join(DIR1, fname)
        path2 = os.path.join(DIR2, fname)


        print(f"[{fname}] Processing...")


        if fname not in offsets_cache:
            safe_name = os.path.splitext(fname)[0]
            ref_wav = os.path.join(TEMP_DIR, f"ref_{safe_name}.wav")
            targ0_wav = os.path.join(TEMP_DIR, f"targ0_{safe_name}.wav")
            targ1_wav = os.path.join(TEMP_DIR, f"targ1_{safe_name}.wav")


            print(f"[{fname}] Extracting audio waveforms...")
            extract_audio(path1, 0, ref_wav)
            has_targ0 = extract_audio(path2, 0, targ0_wav)
            has_targ1 = extract_audio(path2, 1, targ1_wav)


            print(f"[{fname}] Calculating offset...")
            delay0, peak0 = find_offset(ref_wav, targ0_wav) if has_targ0 else (0.0, -1.0)
            delay1, peak1 = find_offset(ref_wav, targ1_wav) if has_targ1 else (0.0, -1.0)


            if peak1 > peak0:
                jp_track_idx = 1
                man_track_idx = 0
                final_delay = delay1
            else:
                jp_track_idx = 0
                man_track_idx = 1
                final_delay = delay0


            offsets_cache[fname] = {
                "man_track_idx": man_track_idx,
                "jp_track_idx": jp_track_idx,
                "delay_sec": final_delay,
                "peak_val": float(max(peak1, peak0))
            }


            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(offsets_cache, f, indent=4)


            for wav_f in [ref_wav, targ0_wav, targ1_wav]:
                if os.path.exists(wav_f):
                    os.remove(wav_f)

        info = offsets_cache[fname]
        man_track_idx = info["man_track_idx"]
        delay_sec = info["delay_sec"]
        print(f"[{fname}] Analysis complete: Mandarin track index {man_track_idx}, offset {delay_sec:.3f} sec")


        audio_ids, sub_ids = get_mkvmerge_track_ids(path2)
        if man_track_idx >= len(audio_ids):
            print(f"[{fname}] Error: Target track not found in {path2}")
            continue


        actual_track_id = audio_ids[man_track_idx]
        
        out_path = os.path.join(OUT_DIR, fname)
        delay_ms = int(delay_sec * 1000)


        mkvmerge_cmd = [
            MKVMERGE_CMD,
            '-o', out_path,
            path1,
            '--no-video',
            '--no-chapters',
            '--audio-tracks', str(actual_track_id),
            '--sync', f'{actual_track_id}:{delay_ms}',
            '--track-name', f'{actual_track_id}:Mandarin',
            '--language', f'{actual_track_id}:chi'
        ]


        for sub_id in sub_ids:
            mkvmerge_cmd.extend(['--sync', f'{sub_id}:{delay_ms}'])


        mkvmerge_cmd.append(path2)


        print(f"[{fname}] Merging...")
        subprocess.run(mkvmerge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


        print(f"[{fname}] Done! Output saved to {out_path}\n")
        

if __name__ == '__main__':
    main()