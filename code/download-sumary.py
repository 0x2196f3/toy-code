import os
import time
from collections import defaultdict
import datetime

def get_file_creation_time(file_path):
    return os.path.getctime(file_path)

def format_size(size_bytes):
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / 1024:.2f} KB"

def list_files_and_summarize_sizes(directory):
    file_sizes_by_hour = defaultdict(int)
    file_counts_by_hour = defaultdict(int)
    
    global_stats = {
        'total_count': 0,
        'total_size': 0,
        'min_ts': None,
        'max_ts': None
    }

    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            if os.path.isfile(file_path):
                try:
                    creation_time = get_file_creation_time(file_path)
                    file_size = os.path.getsize(file_path)

                    creation_hour = time.strftime('%Y-%m-%d %H:00', time.localtime(creation_time))
                    file_sizes_by_hour[creation_hour] += file_size
                    file_counts_by_hour[creation_hour] += 1
                    
                    global_stats['total_count'] += 1
                    global_stats['total_size'] += file_size
                    
                    if global_stats['min_ts'] is None or creation_time < global_stats['min_ts']:
                        global_stats['min_ts'] = creation_time
                    
                    if global_stats['max_ts'] is None or creation_time > global_stats['max_ts']:
                        global_stats['max_ts'] = creation_time
                        
                except OSError:
                    continue
                    
    return file_sizes_by_hour, file_counts_by_hour, global_stats

def print_chart(file_sizes_by_hour, file_counts_by_hour, global_stats):
    total_files = global_stats['total_count']
    total_size = global_stats['total_size']
    
    if total_files > 0:
        start_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(global_stats['min_ts']))
        end_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(global_stats['max_ts']))
        
        duration_seconds = global_stats['max_ts'] - global_stats['min_ts']
        if duration_seconds < 1: 
            duration_seconds = 1
        
        duration_str = str(datetime.timedelta(seconds=int(duration_seconds)))
        
        total_avg_speed_mb = (total_size / (1024 * 1024)) / duration_seconds
        
        avg_file_size = total_size / total_files
    else:
        start_date = "N/A"
        end_date = "N/A"
        duration_str = "0:00:00"
        total_avg_speed_mb = 0
        avg_file_size = 0
    
    print("="*70)
    print(f" DOWNLOAD SUMMARY: {directory}")
    print("="*70)

    print("Hour             | Size (GB)  | Avg Speed (MB/s) | File Count")
    print("-----------------|------------|------------------|------------")
    
    for hour in sorted(file_sizes_by_hour.keys()):
        h_total_size = file_sizes_by_hour[hour]
        h_file_count = file_counts_by_hour[hour]
        
        h_avg_speed = (h_total_size / (1024 * 1024)) / 3600 if h_file_count > 0 else 0
        
        print(f"{hour} | {h_total_size / (1024 * 1024 * 1024):<10.2f} | {h_avg_speed:<16.2f} | {h_file_count:<10}")
    
    print("="*70)
    print(f" Total Files      : {total_files:,}")
    print(f" Total Size       : {format_size(total_size)}")
    print(f" Avg File Size    : {format_size(avg_file_size)}")
    print("-" * 30)
    print(f" First File       : {start_date}")
    print(f" Last File        : {end_date}")
    print(f" Total Duration   : {duration_str}")
    print("-" * 30)
    print(f" Overall Speed    : {total_avg_speed_mb:.2f} MB/s")
    print("="*70)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    directory = './' 
    
    if os.path.exists(directory):
        file_sizes, file_counts, stats = list_files_and_summarize_sizes(directory)
        print_chart(file_sizes, file_counts, stats)
    else:
        print(f"Error: Directory '{directory}' not found.")
    
    input("Press Enter to exit...")
