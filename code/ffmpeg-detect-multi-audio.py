import os
import subprocess

MIN_AUDIO_STREAM_COUNT = 2

def print_video_files_with_multiple_audio_streams(root='.'):
    video_files = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(('.mkv', '.mp4')):
                video_files.append(os.path.join(dirpath, name))
    video_files.sort()

    for path in video_files:
        try:
            result = subprocess.run(
                ['ffmpeg', '-i', path],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            audio_streams = [line for line in result.stderr.splitlines() if 'Audio:' in line]
            stream_count = len(audio_streams)
            if stream_count >= MIN_AUDIO_STREAM_COUNT:
                print(f"{path} has {stream_count} audio streams.")
        except Exception as e:
            print(f"Error processing file {path}: {e}")

if __name__ == "__main__":
    print_video_files_with_multiple_audio_streams('.')
