import os
import subprocess

# Define a constant for the minimum number of audio streams required
MIN_AUDIO_STREAM_COUNT = 2

def print_mkv_files_with_multiple_audio_streams():
    # Get a sorted list of MKV files in the current directory
    mkv_files = sorted([file for file in os.listdir('.') if file.endswith('.mkv')])

    for file in mkv_files:
        try:
            # Call ffmpeg to get the audio stream information
            result = subprocess.run(
                ['./ffmpeg.exe', '-i', file],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding='utf-8'  # Ensure we use utf-8 encoding
            )

            # Count the number of audio streams
            audio_streams = [line for line in result.stderr.splitlines() if 'Audio:' in line]

            # Print the file name and exact audio stream count
            stream_count = len(audio_streams)
            if stream_count >= MIN_AUDIO_STREAM_COUNT:
                print(f"{file} has {stream_count} audio streams.")
        except Exception as e:
            print(f"Error processing file {file}: {e}")

if __name__ == "__main__":
    print_mkv_files_with_multiple_audio_streams()
