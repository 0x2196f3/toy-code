#!/usr/bin/env python3
import sys
import os
import argparse
import math
import shutil

def enable_ansi_colors():
    """Enable ANSI escape sequence support in Windows"""
    if os.name == 'nt':
        os.system('')

def count_diff_bytes(b1, b2):
    """
    Calculate the number of different bytes between two byte strings.
    Optimized: To avoid performance issues with Python's native byte-by-byte loop,
    it is split into 4KB sub-chunks. Byte-by-byte comparison is only performed
    if the sub-chunks are different.
    """
    if b1 == b2:
        return 0
        
    l1, l2 = len(b1), len(b2)
    min_l = min(l1, l2)
    diff = 0
    
    step = 4096
    for i in range(0, min_l, step):
        sub1 = b1[i:i+step]
        sub2 = b2[i:i+step]
        if sub1 != sub2:
            diff += sum(1 for x, y in zip(sub1, sub2) if x != y)
            
    # Add the length difference for unequal parts
    diff += abs(l1 - l2)
    return diff

def parse_chunk_size(size_str):
    """Parse the chunk_size argument, supporting 'auto' or abbreviations like kb, mb, gb"""
    if size_str.lower() == 'auto':
        return 'auto'
    
    s = size_str.lower().strip()
    multiplier = 1
    
    # Remove trailing 'b' (e.g., kb -> k)
    if s.endswith('b'):
        s = s[:-1]
    
    # Determine unit and set multiplier
    if s.endswith('k'):
        multiplier = 1024
        s = s[:-1]
    elif s.endswith('m'):
        multiplier = 1024**2
        s = s[:-1]
    elif s.endswith('g'):
        multiplier = 1024**3
        s = s[:-1]
        
    try:
        val = int(s) * multiplier
    except ValueError:
        raise argparse.ArgumentTypeError(f"Unparseable chunk_size: {size_str}")
        
    # Verify if it's a power of 2 (bitwise trick)
    if val <= 0 or (val & (val - 1)) != 0:
        raise argparse.ArgumentTypeError(f"chunk_size must be a power of 2. Got: {val}")
        
    return val

def main():
    enable_ansi_colors()
    
    parser = argparse.ArgumentParser(description="Binary file chunk comparison tool (Pure Python implementation)")
    parser.add_argument('--file1', required=True, help="Path to the first file")
    parser.add_argument('--file2', required=True, help="Path to the second file")
    parser.add_argument('--chunk_size', required=True, type=parse_chunk_size, 
                        help="Chunk size (e.g., 1024, 1KB, 1MB, 1GB, auto). Must be a power of 2.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file1):
        print(f"Error: File not found '{args.file1}'", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.file2):
        print(f"Error: File not found '{args.file2}'", file=sys.stderr)
        sys.exit(1)
        
    s1 = os.path.getsize(args.file1)
    s2 = os.path.getsize(args.file2)
    s_max = max(s1, s2)
    
    # Get terminal width, ensuring a fallback of at least 80 columns
    term_width = shutil.get_terminal_size((80, 24)).columns
    
    # Find max power of 2 less than or equal to terminal width for grid constraint
    w_max = 1
    while w_max * 2 <= term_width:
        w_max *= 2
        
    if args.chunk_size == 'auto':
        if s_max == 0:
            chunk_size = 1
            w = 1
        else:
            # Calculate optimal chunk size for a roughly square grid
            N_ideal = w_max ** 2
            c_ideal = s_max / N_ideal
            
            if c_ideal > 1:
                chunk_size = 2 ** int(round(math.log2(c_ideal)))
            else:
                chunk_size = 1
                
            N = math.ceil(s_max / chunk_size)
            w_best = 2 ** int(round(math.log2(math.sqrt(max(1, N)))))
            w = min(w_best, w_max)
            w = max(1, w)
    else:
        chunk_size = args.chunk_size
        N = math.ceil(s_max / chunk_size) if chunk_size else 1
        w_best = 2 ** int(round(math.log2(math.sqrt(max(1, N)))))
        w = min(w_best, w_max)
        w = max(1, w)
        
    statuses = []
    problems = []
    total_diff_bytes = 0
    total_compared_bytes = 0
    
    # Performance feature: Fast path triggers when 50% difference is reached
    skip_details = False
    threshold_bytes = s_max * 0.5
    
    try:
        with open(args.file1, 'rb') as f1, open(args.file2, 'rb') as f2:
            chunk_idx = 0
            while True:
                b1 = f1.read(chunk_size)
                b2 = f2.read(chunk_size)
                
                if not b1 and not b2:
                    break
                    
                l1 = len(b1)
                l2 = len(b2)
                chunk_max_len = max(l1, l2)
                total_compared_bytes += chunk_max_len
                
                if b1 == b2:
                    statuses.append('match')
                else:
                    if not b1:
                        statuses.append('f2_only')
                        diff = l2
                        if not skip_details:
                            problems.append((chunk_idx, 'File2 Only', diff, chunk_max_len))
                    elif not b2:
                        statuses.append('f1_only')
                        diff = l1
                        if not skip_details:
                            problems.append((chunk_idx, 'File1 Only', diff, chunk_max_len))
                    else:
                        statuses.append('diff')
                        if skip_details:
                            # Skip exact byte counting for performance since files are vastly different
                            diff = chunk_max_len
                        else:
                            diff = count_diff_bytes(b1, b2)
                            problems.append((chunk_idx, 'Diff', diff, chunk_max_len))
                            
                    if not skip_details:
                        total_diff_bytes += diff
                        # Trigger performance skip if >50% difference
                        if total_diff_bytes >= threshold_bytes:
                            skip_details = True
                            problems.clear() # Clear details to only output visual blocks
                            
                chunk_idx += 1
    except Exception as e:
        print(f"Error reading files: {e}", file=sys.stderr)
        sys.exit(1)
        
    # --- Render TUI ---
    print(f"\nComparing '{args.file1}' and '{args.file2}'")
    print(f"Chunk size: {chunk_size} bytes | Grid width: {w} blocks")
    print("Legend: \033[92m█\033[0m Match  \033[91m█\033[0m Diff  \033[94m█\033[0m Single (One file only)\n")
    
    color_map = {
        'match': '\033[92m█\033[0m',   # Green
        'diff': '\033[91m█\033[0m',    # Red
        'f1_only': '\033[94m█\033[0m', # Blue
        'f2_only': '\033[94m█\033[0m'  # Blue
    }
    
    for i in range(0, len(statuses), w):
        row = statuses[i:i+w]
        print(''.join(color_map[s] for s in row))
        
    # --- Render Summary Statistics ---
    print("\n" + "="*70)
    print(" Summary Statistics")
    print("="*70)
    total_blocks = len(statuses)
    bad_blocks = sum(1 for s in statuses if s != 'match')
    
    print(f" Total Blocks       : {total_blocks}")
    print(f" Problematic Blocks : {bad_blocks}")
    
    if skip_details:
        print(f" Total Diff Bytes   : Exceeded 50% threshold (> {int(threshold_bytes)} bytes)")
        print("\n Note: The files are vastly different. Exact byte comparison and detailed")
        print("       block listings have been skipped for performance.")
    else:
        overall_diff_pct = (total_diff_bytes / total_compared_bytes * 100) if total_compared_bytes > 0 else 0
        print(f" Total Diff Bytes   : {total_diff_bytes} / {total_compared_bytes} bytes ({overall_diff_pct:.4f}%)\n")
        
        if problems:
            print(" Problematic Blocks Details:")
            print(f" {'Index':<8} | {'Status':<12} | {'Diff Bytes':<12} | {'Diff % (in chunk)':<15}")
            print("-" * 65)
            for idx, status, diff_b, max_b in problems:
                pct = (diff_b / max_b * 100) if max_b > 0 else 0
                print(f" {idx:<8} | {status:<12} | {diff_b:<12} | {pct:>6.2f}%")
            print("-" * 65)

if __name__ == '__main__':
    main()