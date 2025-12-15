import os
import time
from collections import defaultdict

def get_file_creation_time(file_path):
    return os.path.getctime(file_path)

def list_files_and_summarize_sizes(directory):
    file_sizes_by_hour = defaultdict(int)
    file_counts_by_hour = defaultdict(int)

    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            if os.path.isfile(file_path):
                creation_time = get_file_creation_time(file_path)
                file_size = os.path.getsize(file_path)

                creation_hour = time.strftime('%Y-%m-%d %H:00', time.localtime(creation_time))
                file_sizes_by_hour[creation_hour] += file_size
                file_counts_by_hour[creation_hour] += 1
    return file_sizes_by_hour, file_counts_by_hour


def print_chart(file_sizes_by_hour, file_counts_by_hour):
    print("Hour             | Size (GB)  | Avg Speed (MB/s) | File Count")
    print("-----------------|------------|------------------|------------")
    
    for hour in sorted(file_sizes_by_hour.keys()):
        total_size = file_sizes_by_hour[hour]
        file_count = file_counts_by_hour[hour]
        
        avg_speed = (total_size / (1024 * 1024)) / 3600 if file_count > 0 else 0  # MB/s
        
        print(f"{hour} | {total_size / (1024 * 1024 * 1024):<10.2f} | {avg_speed:<16.2f} | {file_count:<10}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    directory = './download'
    file_sizes_by_hour, file_counts_by_hour = list_files_and_summarize_sizes(directory)
    print_chart(file_sizes_by_hour, file_counts_by_hour)
    input()
