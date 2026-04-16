import subprocess
from pathlib import Path

EXT_MAP = {
    "mp3": "mp3",
    "flac": "flac",
    "aac": "aac",
    "opus": "opus",
    "vorbis": "ogg",
    "ac3": "ac3",
    "eac3": "eac3",
    "alac": "m4a",
    "wav": "wav",
    "pcm_s16le": "wav",
    "pcm_s24le": "wav",
    # add more mappings if needed
}

def probe_audio_codecs(input_file: Path, ffprobe_path: str = "./ffmpeg.exe"):
    # Use ffprobe bundled with ffmpeg executable; call as ffmpeg.exe -hide_banner -loglevel error -i ...
    # Simpler: call ffprobe if available; otherwise call ffmpeg -hide_banner -loglevel error -show_streams -select_streams a -of default=noprint_wrappers=1:nokey=1
    # Here try ffprobe first (common), fallback to ffmpeg -i parsing.
    probe_cmd = ["./ffprobe.exe", "-v", "error", "-select_streams", "a",
                 "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(input_file)]
    try:
        out = subprocess.check_output(probe_cmd, stderr=subprocess.DEVNULL, text=True)
        codecs = [line.strip() for line in out.splitlines() if line.strip()]
        return codecs
    except (FileNotFoundError, subprocess.CalledProcessError):
        # fallback to ffmpeg - use -hide_banner and -loglevel to suppress extraneous output then parse
        fallback_cmd = ["./ffmpeg.exe", "-hide_banner", "-i", str(input_file)]
        proc = subprocess.run(fallback_cmd, capture_output=True, text=True)
        stderr = proc.stderr
        codecs = []
        for line in stderr.splitlines():
            line = line.strip()
            if line.startswith("Stream") and "Audio:" in line:
                # example: Stream #0:1(eng): Audio: aac (LC), 48000 Hz, stereo, fltp, 192 kb/s
                parts = line.split("Audio:")[1].strip().split()
                if parts:
                    codecs.append(parts[0].strip().strip(','))
        return codecs

def extract_all_audio(input_path: str, ffmpeg_path: str = "./ffmpeg.exe", out_template: str = "audio_{idx}.{ext}"):
    inp = Path(input_path)
    if not inp.exists():
        raise FileNotFoundError(inp)

    codecs = probe_audio_codecs(inp)
    if not codecs:
        raise RuntimeError("No audio streams found")

    outputs = []
    for i, codec in enumerate(codecs):
        ext = EXT_MAP.get(codec, codec)  # fallback to codec name if unknown
        out_name = out_template.format(idx=i, ext=ext)
        cmd = [
            str(Path(ffmpeg_path)),
            "-y",
            "-i", str(inp),
            "-map", f"0:a:{i}",
            "-c", "copy",
            out_name
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for stream {i}: {res.stderr.strip()}")
        outputs.append(out_name)
    return outputs

if __name__ == "__main__":
    print(extract_all_audio("audio.mkv"))
