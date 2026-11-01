#!/usr/bin/env python3
import argparse
import gc
import sys

import torch


def timed_ms(fn, warmup, iters):
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(iters):
        fn()
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) / iters


def benchmark_matmul(n, dtype, label, warmup, iters, allow_tf32=None):
    old_tf32 = torch.backends.cuda.matmul.allow_tf32
    try:
        if allow_tf32 is not None:
            torch.backends.cuda.matmul.allow_tf32 = allow_tf32

        a = torch.randn((n, n), device="cuda", dtype=dtype)
        b = torch.randn((n, n), device="cuda", dtype=dtype)
        c = torch.empty((n, n), device="cuda", dtype=dtype)

        ms = timed_ms(lambda: torch.mm(a, b, out=c), warmup, iters)
        tflops = (2.0 * n**3) / (ms / 1000.0) / 1e12
        print(f"matmul {label:>5}  {n:5d} x {n:<5d}  {ms:9.3f} ms  {tflops:8.2f} TFLOP/s")
    finally:
        torch.backends.cuda.matmul.allow_tf32 = old_tf32


def benchmark_memory(warmup, iters):
    free_bytes, _ = torch.cuda.mem_get_info()
    count = min(16_777_216, max(1, free_bytes // 48))
    try:
        a = torch.randn(count, device="cuda", dtype=torch.float32)
        b = torch.randn(count, device="cuda", dtype=torch.float32)
        c = torch.empty_like(a)

        ms = timed_ms(lambda: torch.add(a, b, out=c), warmup, iters)
        gbps = (3 * count * a.element_size()) / (ms / 1000.0) / 1e9
        print(f"memory add  {count:,} float32 elements  {ms:9.3f} ms  {gbps:8.2f} GB/s")
    except RuntimeError as exc:
        print(f"memory test skipped: {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Basic PyTorch CUDA GPU benchmark")
    parser.add_argument("--sizes", nargs="+", type=int, default=[1024, 2048, 4096],
                        help="square matrix sizes (default: 1024 2048 4096)")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iters", type=int, default=10)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("CUDA is unavailable; install a CUDA-enabled PyTorch build and check the NVIDIA driver.")
        return 1

    device = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device)
    print(f"GPU: {props.name}")
    print(f"Compute capability: {props.major}.{props.minor}")
    print(f"PyTorch: {torch.__version__} | CUDA: {torch.version.cuda}")
    print(f"Warmup: {args.warmup} | Timed iterations: {args.iters}")
    print("Matrix results are effective throughput; performance depends on matrix size and GPU load.")
    print()

    tests = [
        ("FP16", torch.float16, None),
        ("BF16", torch.bfloat16, None),
        ("FP32", torch.float32, False),
    ]
    if props.major >= 8:
        tests.append(("TF32", torch.float32, True))
    else:
        print("TF32 skipped (requires compute capability 8.0 or newer).")

    tests.append(("FP64", torch.float64, None))

    for n in args.sizes:
        if n <= 0:
            print(f"Skipping invalid matrix size: {n}")
            continue
        for label, dtype, tf32 in tests:
            if label == "BF16" and not torch.cuda.is_bf16_supported():
                print(f"matmul {label:>5}  {n:5d} x {n:<5d}  skipped (BF16 unsupported)")
                continue
            try:
                benchmark_matmul(n, dtype, label, args.warmup, args.iters, tf32)
            except RuntimeError as exc:
                print(f"matmul {label:>5}  {n:5d} x {n:<5d}  skipped: {exc}",
                      file=sys.stderr)
                gc.collect()
                torch.cuda.empty_cache()

    benchmark_memory(args.warmup, args.iters)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
