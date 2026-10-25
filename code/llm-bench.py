#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import math
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple


DEFAULT_CONFIG = {
    "endpoint": "http://192.168.2.2:8080/v1/chat/completions",
    "model": "llama3.2",
    "api_type": "auto",
    "prompt_tokens": 512,
    "max_tokens": 128,
    "concurrency": 1,
    "warmup": 1,
    "repeats": 3,
    "temperature": 0.0,
    "api_key": "",
    "timeout": 300,
}




@dataclass
class SingleRequestMetric:
    ttft_ms: float
    prefill_speed: float
    gen_speed: float
    prompt_tokens: int
    gen_tokens: int
    total_duration_sec: float
    error: Optional[str] = None




def check_curl_installed():
    if not shutil.which("curl"):
        print("Error: 'curl' binary not found. Please install curl.", file=sys.stderr)
        sys.exit(1)




def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cjk_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    words = len(re.findall(r'\b\w+\b', text))
    return max(1, int(words * 1.3 + cjk_chars * 1.2))




def generate_prompt(target_tokens: int) -> str:
    instruction = "Please translate the following text into Japanese:\n\n"
    base_paragraph = (
        "Large language models (LLMs) have revolutionized natural language processing by delivering "
        "state-of-the-art capabilities across translation, summarization, and complex reasoning tasks. "
        "Benchmarking inference speed, latency, prefill throughput, and token generation rates "
        "is critical for evaluating and optimizing model deployment across diverse hardware architectures. "
    )
    inst_tokens = estimate_tokens(instruction)
    base_tokens = estimate_tokens(base_paragraph)
    needed_tokens = max(1, target_tokens - inst_tokens)
    repeats = max(1, needed_tokens // base_tokens)
    return instruction + (base_paragraph * repeats).strip()




def calculate_stats(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) <= 1:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return mean, math.sqrt(variance)




def run_single_request(
    endpoint: str,
    model: str,
    api_type: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    api_key: str,
    timeout: int
) -> SingleRequestMetric:


    resolved_api_type = api_type
    if api_type == "auto":
        resolved_api_type = "ollama" if "/api/" in endpoint else "openai"


    if resolved_api_type == "openai":
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True}
        }
    else:
        payload = {
            "model": model,
            "prompt": prompt,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            },
            "stream": True
        }


    cmd = [
        "curl", "-s", "-N",
        "-X", "POST", endpoint,
        "-H", "Content-Type: application/json",
        "--max-time", str(timeout)
    ]
    if api_key:
        cmd.extend(["-H", f"Authorization: Bearer {api_key}"])
    cmd.extend(["-d", json.dumps(payload)])


    start_time = time.perf_counter()
    first_token_time = None
    gen_text_chunks = []


    api_prompt_tokens = None
    api_gen_tokens = None
    api_prompt_time_sec = None
    api_gen_time_sec = None


    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", bufsize=1
        )


        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue


            now = time.perf_counter()


            if resolved_api_type == "openai":
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        if "usage" in chunk and chunk["usage"]:
                            api_prompt_tokens = chunk["usage"].get("prompt_tokens")
                            api_gen_tokens = chunk["usage"].get("completion_tokens")


                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                if first_token_time is None:
                                    first_token_time = now
                                gen_text_chunks.append(content)
                    except json.JSONDecodeError:
                        continue


            elif resolved_api_type == "ollama":
                try:
                    chunk = json.loads(line)
                    content = chunk.get("response") or chunk.get("message", {}).get("content", "")
                    if content and first_token_time is None:
                        first_token_time = now
                    if content:
                        gen_text_chunks.append(content)


                    if chunk.get("done"):
                        if "prompt_eval_count" in chunk:
                            api_prompt_tokens = chunk["prompt_eval_count"]
                        if "prompt_eval_duration" in chunk:
                            api_prompt_time_sec = chunk["prompt_eval_duration"] / 1e9
                        if "eval_count" in chunk:
                            api_gen_tokens = chunk["eval_count"]
                        if "eval_duration" in chunk:
                            api_gen_time_sec = chunk["eval_duration"] / 1e9
                except json.JSONDecodeError:
                    continue


        proc.wait()
        end_time = time.perf_counter()


        if proc.returncode != 0:
            stderr = proc.stderr.read()
            return SingleRequestMetric(0, 0, 0, 0, 0, 0, error=f"curl error: {stderr.strip()}")


    except Exception as e:
        return SingleRequestMetric(0, 0, 0, 0, 0, 0, error=str(e))


    total_duration = end_time - start_time
    ttft_sec = (first_token_time - start_time) if first_token_time else total_duration
    ttft_ms = ttft_sec * 1000.0


    prompt_tokens = api_prompt_tokens if api_prompt_tokens is not None else estimate_tokens(prompt)
    gen_tokens = api_gen_tokens if api_gen_tokens is not None else estimate_tokens("".join(gen_text_chunks))


    prefill_duration = api_prompt_time_sec if api_prompt_time_sec is not None else ttft_sec
    if api_gen_time_sec is not None:
        gen_duration = api_gen_time_sec
    elif first_token_time is not None:
        gen_duration = end_time - first_token_time
    else:
        gen_duration = total_duration - ttft_sec


    prefill_speed = (prompt_tokens / prefill_duration) if prefill_duration > 0 else 0.0
    gen_speed = (gen_tokens / gen_duration) if gen_duration > 0 else 0.0


    return SingleRequestMetric(
        ttft_ms=ttft_ms,
        prefill_speed=prefill_speed,
        gen_speed=gen_speed,
        prompt_tokens=prompt_tokens,
        gen_tokens=gen_tokens,
        total_duration_sec=total_duration
    )




def run_batch(concurrency: int, **kwargs) -> Tuple[List[SingleRequestMetric], float]:
    start_wall = time.perf_counter()
    results = []


    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(run_single_request, **kwargs) for _ in range(concurrency)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())


    end_wall = time.perf_counter()
    return results, end_wall - start_wall




def main():
    check_curl_installed()


    parser = argparse.ArgumentParser(description="Single-file Python LLM Benchmark")
    parser.add_argument("--endpoint", type=str, default=DEFAULT_CONFIG["endpoint"], help="API endpoint URL")
    parser.add_argument("--model", type=str, default=DEFAULT_CONFIG["model"], help="Model name")
    parser.add_argument("--api-type", type=str, choices=["auto", "openai", "ollama"], default=DEFAULT_CONFIG["api_type"], help="API protocol type")
    parser.add_argument("--prompt-tokens", type=int, default=DEFAULT_CONFIG["prompt_tokens"], help="Target prompt token count")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_CONFIG["max_tokens"], help="Max generation tokens")
    parser.add_argument("-c", "--concurrency", type=int, default=DEFAULT_CONFIG["concurrency"], help="Concurrency level")
    parser.add_argument("--warmup", type=int, default=DEFAULT_CONFIG["warmup"], help="Warmup iterations")
    parser.add_argument("-r", "--repeats", type=int, default=DEFAULT_CONFIG["repeats"], help="Test repetitions")
    parser.add_argument("--temperature", type=float, default=DEFAULT_CONFIG["temperature"], help="Sampling temperature")
    parser.add_argument("--api-key", type=str, default=DEFAULT_CONFIG["api_key"], help="API Key")
    parser.add_argument("--timeout", type=int, default=DEFAULT_CONFIG["timeout"], help="Timeout in seconds")
    args = parser.parse_args()


    prompt = generate_prompt(args.prompt_tokens)


    print("=" * 80)
    print("                      LLM INFERENCE BENCHMARK REPORT                      ")
    print("=" * 80)
    print(f"Endpoint      : {args.endpoint}")
    print(f"Model         : {args.model}")
    print(f"API Type      : {args.api_type}")
    print(f"Concurrency   : {args.concurrency}")
    print(f"Target Prompt : ~{args.prompt_tokens} tokens")
    print(f"Target Gen    : {args.max_tokens} tokens")
    print(f"Warmup Runs   : {args.warmup}")
    print(f"Test Repeats  : {args.repeats}")
    print("-" * 80)


    req_kwargs = {
        "endpoint": args.endpoint,
        "model": args.model,
        "api_type": args.api_type,
        "prompt": prompt,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "api_key": args.api_key,
        "timeout": args.timeout
    }


    if args.warmup > 0:
        print(f"[Warmup] Running {args.warmup} warmup run(s)...", end="", flush=True)
        for _ in range(args.warmup):
            _ = run_batch(args.concurrency, **req_kwargs)
        print(" Done.")


    print(f"[Testing] Executing {args.repeats} test runs...")


    all_runs_metrics: List[List[SingleRequestMetric]] = []
    run_wall_times: List[float] = []


    for i in range(args.repeats):
        print(f"  Run {i+1}/{args.repeats}... ", end="", flush=True)
        metrics, wall_time = run_batch(args.concurrency, **req_kwargs)


        errors = [m.error for m in metrics if m.error]
        if errors:
            print(f"FAILED (Error: {errors[0]})")
            sys.exit(1)


        all_runs_metrics.append(metrics)
        run_wall_times.append(wall_time)


        avg_ttft = sum(m.ttft_ms for m in metrics) / len(metrics)
        avg_gen_speed = sum(m.gen_speed for m in metrics) / len(metrics)
        print(f"TTFT: {avg_ttft:.2f} ms | Gen Speed: {avg_gen_speed:.2f} t/s | Wall Time: {wall_time:.2f}s")


    flat_metrics = [m for run in all_runs_metrics for m in run]


    ttft_mean, ttft_std = calculate_stats([m.ttft_ms for m in flat_metrics])
    prefill_mean, prefill_std = calculate_stats([m.prefill_speed for m in flat_metrics])
    gen_mean, gen_std = calculate_stats([m.gen_speed for m in flat_metrics])
    prompt_tok_mean, _ = calculate_stats([m.prompt_tokens for m in flat_metrics])
    gen_tok_mean, _ = calculate_stats([m.gen_tokens for m in flat_metrics])
    latency_mean, latency_std = calculate_stats([m.total_duration_sec for m in flat_metrics])


    throughputs = [
        sum(m.gen_tokens for m in run_metrics) / wall_time
        for run_metrics, wall_time in zip(all_runs_metrics, run_wall_times)
    ]
    tp_mean, tp_std = calculate_stats(throughputs)


    # Output Table Alignment Setup
    w1, w2, w3 = 30, 20, 20
    sep_line = "+" + "-" * (w1 + 2) + "+" + "-" * (w2 + 2) + "+" + "-" * (w3 + 2) + "+"


    print("\n" + "=" * 80)
    print("                              BENCHMARK RESULTS                           ")
    print("=" * 80)
    print(f"| {'Metric':<{w1}} | {'Mean':<{w2}} | {'StdDev':<{w3}} |")
    print(sep_line)
    print(f"| {'Prompt Tokens':<{w1}} | {f'{prompt_tok_mean:.1f}':<{w2}} | {'-':<{w3}} |")
    print(f"| {'Generated Tokens':<{w1}} | {f'{gen_tok_mean:.1f}':<{w2}} | {'-':<{w3}} |")
    print(f"| {'Time to First Token (TTFT)':<{w1}} | {f'{ttft_mean:.2f} ms':<{w2}} | {f'± {ttft_std:.2f}':<{w3}} |")
    print(f"| {'Prefill Speed':<{w1}} | {f'{prefill_mean:.2f} tok/s':<{w2}} | {f'± {prefill_std:.2f}':<{w3}} |")
    print(f"| {'Generation Speed':<{w1}} | {f'{gen_mean:.2f} tok/s':<{w2}} | {f'± {gen_std:.2f}':<{w3}} |")
    print(f"| {'Single Request Latency':<{w1}} | {f'{latency_mean:.2f} s':<{w2}} | {f'± {latency_std:.2f}':<{w3}} |")
    print(f"| {'Total Throughput':<{w1}} | {f'{tp_mean:.2f} tok/s':<{w2}} | {f'± {tp_std:.2f}':<{w3}} |")
    print("=" * 80)


    print("\n[llama-bench Style Summary Line]")
    print(f"| model: {args.model} | threads/c: {args.concurrency} | pp: {int(prompt_tok_mean)} | tg: {int(gen_tok_mean)} | ttft: {ttft_mean:.2f} ms | prefill: {prefill_mean:.2f} t/s | decode: {gen_mean:.2f} t/s |")
    print()




if __name__ == "__main__":
    main()