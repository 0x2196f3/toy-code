# -*- coding: utf-8 -*-
import subprocess
import json
import time
import os
import sys
import math
import shlex

OAI_BASE_URL = "http://192.168.2.2:8080"

OAI_API_KEY = None

MODEL_NAME = "test.gguf"

MAX_TOKENS = 512

NUM_ROUNDS = 2

DELAY_BETWEEN_TESTS = 10

PROMPTS = [
    """Translate the following technical description of a new automotive braking system from German to English. Pay close attention to the precise terminology and ensure the tone is formal and instructive.

Original German Text:
"Das innovative regenerative Bremssystem speichert die beim Bremsen erzeugte kinetische Energie und wandelt sie in elektrische Energie um, die dann in der Hochvoltbatterie des Fahrzeugs gespeichert wird. Dieser Prozess erhöht nicht nur die Gesamteffizienz des Fahrzeugs, sondern reduziert auch den Verschleiß der herkömmlichen Bremsbeläge erheblich. Der Fahrer kann die Stärke der Rekuperation über Schaltwippen am Lenkrad einstellen."
""",
    """Translate the following casual conversation between two friends planning a weekend trip from Japanese to Traditional Chinese. The translation should capture the informal and friendly tone.

Original Japanese Text:
A: 「週末、どこか行かない？最近、仕事ばっかりで疲れちゃって。」
B: 「いいね！温泉とかどうかな？箱根あたりでゆっくりしたい気分。」
A: 「最高じゃん！すぐに旅館予約しなきゃ。おすすめの場所ある？」
B: 「任せて！去年行ったところで、景色がすごく綺麗な露天風呂があるんだ。」
""",
    """Translate the following stanza from a Spanish poem into French. The goal is to preserve the metaphorical language and the melancholic mood, not just the literal meaning.

Original Spanish Text:
"En el lienzo oscuro de la noche,
tus ojos son dos luceros que me guían,
un faro de anhelo en la distancia,
iluminando la soledad de mis días."
"""
]

def calculate_mean(data):
    return sum(data) / len(data) if data else 0.0

def calculate_std_dev(data):
    n = len(data)
    if n < 2:
        return 0.0
    mean = calculate_mean(data)
    variance = sum((x - mean) ** 2 for x in data) / n
    return math.sqrt(variance)

def check_curl_exists():
    try:
        subprocess.run(["which", "curl"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: `curl` command not found.")
        print("Please install curl and ensure it is in your system's PATH to run this script.")
        sys.exit(1)

def run_warmup():
    print("🚀 Performing a warm-up run to load the model...")
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "Hello!"}],
            "max_tokens": 32,
            "temperature": 0.0,
            "stream": False
        }
        headers = ""
        if OAI_API_KEY:
            headers = f"-H 'Authorization: Bearer {OAI_API_KEY}'"
        json_payload = shlex.quote(json.dumps(payload))
        command = f"curl -s {headers} -H 'Content-Type: application/json' {OAI_BASE_URL}/v1/chat/completions -d {json_payload}"
        subprocess.run(command, shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
        print("✅ Warm-up complete. Model is now loaded.\n")
        time.sleep(DELAY_BETWEEN_TESTS)
    except subprocess.CalledProcessError as e:
        print("❌ Warm-up run failed. Please check if the server is running and the model name is correct.")
        print(f"Error details:\n{e.stderr or e.stdout}")
        sys.exit(1)

def parse_openai_timing_fields(resp_json):
    """
    Parse timing fields from llama.cpp OpenAI-compatible response JSON.
    Returns (eval_count, eval_duration_ns, prompt_eval_count, prompt_eval_duration_ns).
    Uses these mappings based on the provided example:
      - timings.predicted_n -> eval_count
      - timings.predicted_ms -> eval_duration_ns (ms -> ns)
      - timings.prompt_n -> prompt_eval_count
      - timings.prompt_ms -> prompt_eval_duration_ns (ms -> ns)
    Falls back to sensible defaults if fields are missing.
    """
    eval_count = 0
    eval_duration_ns = 1
    prompt_eval_count = 0
    prompt_eval_duration_ns = 1

    if not isinstance(resp_json, dict):
        return eval_count, eval_duration_ns, prompt_eval_count, prompt_eval_duration_ns

    timings = resp_json.get("timings") or {}
    if isinstance(timings, dict):
        # predicted -> generation/completion metrics
        predicted_n = timings.get("predicted_n")
        predicted_ms = timings.get("predicted_ms")
        if isinstance(predicted_n, (int, float)):
            eval_count = int(predicted_n)
        if isinstance(predicted_ms, (int, float)):
            eval_duration_ns = int(predicted_ms * 1_000_000)  # ms -> ns

        # prompt -> prompt-processing metrics
        prompt_n = timings.get("prompt_n")
        prompt_ms = timings.get("prompt_ms")
        if isinstance(prompt_n, (int, float)):
            prompt_eval_count = int(prompt_n)
        if isinstance(prompt_ms, (int, float)):
            prompt_eval_duration_ns = int(prompt_ms * 1_000_000)  # ms -> ns

    # If predicted fields missing, try fallback to usage token counts
    if eval_count == 0:
        usage = resp_json.get("usage") or {}
        completion_tokens = usage.get("completion_tokens")
        if isinstance(completion_tokens, int):
            eval_count = completion_tokens

    if prompt_eval_count == 0:
        usage = resp_json.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        if isinstance(prompt_tokens, int):
            prompt_eval_count = prompt_tokens

    return eval_count, eval_duration_ns, prompt_eval_count, prompt_eval_duration_ns

def run_single_test(prompt):
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
            "stream": False
        }
        headers = ""
        if OAI_API_KEY:
            headers = f"-H 'Authorization: Bearer {OAI_API_KEY}'"
        json_payload = shlex.quote(json.dumps(payload))
        command = f"curl -s {headers} -H 'Content-Type: application/json' {OAI_BASE_URL}/v1/chat/completions -d {json_payload}"

        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
        data = json.loads(result.stdout)

        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", completion_tokens + prompt_tokens)

        eval_count, eval_duration_ns, prompt_eval_count, prompt_eval_duration_ns = parse_openai_timing_fields(data)

        if eval_duration_ns == 1 and prompt_eval_duration_ns == 1:
            print("time calculated by client")
            timed_command = (
                f"/usr/bin/time -f '%e' -o /tmp/llama_time.txt curl -s {headers} -H 'Content-Type: application/json' "
                f"{OAI_BASE_URL}/v1/chat/completions -d {json_payload} >/dev/null 2>&1 && cat /tmp/llama_time.txt"
            )
            try:
                timed = subprocess.run(timed_command, shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
                wall_seconds = float(timed.stdout.strip() or "0.0")
            except Exception:
                wall_seconds = 0.0
            prompt_eval_duration_ns = int(wall_seconds * 1_000_000_000) if wall_seconds > 0 else 1
            prompt_eval_count = total_tokens if total_tokens else 1
            eval_duration_ns = prompt_eval_duration_ns
            eval_count = completion_tokens if completion_tokens else prompt_eval_count

        eval_seconds = eval_duration_ns / 1_000_000_000
        prompt_eval_seconds = prompt_eval_duration_ns / 1_000_000_000

        return {
            "gen_throughput": (eval_count / eval_seconds) if eval_seconds > 0 else 0,
            "prompt_throughput": (prompt_eval_count / prompt_eval_seconds) if prompt_eval_seconds > 0 else 0,
            "ttft": prompt_eval_seconds
        }

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Test execution failed.")
        print(f"Error output:\n{e.stderr or e.stdout}")
        return None
    except json.JSONDecodeError:
        print(f"\n❌ Failed to parse JSON response from server.")
        print(f"Raw output:\n{result.stdout}")
        return None
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        return None

def main():
    check_curl_exists()

    print("=" * 60)
    print("OpenAI-compatible API Performance Test Script (via curl)")
    print("=" * 60)
    print(f"  Target URL: {OAI_BASE_URL}/v1/chat/completions")
    print(f"  Test Model: {MODEL_NAME}")
    print(f"  Max Tokens: {MAX_TOKENS}")
    print(f"  Test Rounds: {NUM_ROUNDS}")
    print(f"  Prompt Count: {len(PROMPTS)}")
    print("-" * 60)

    run_warmup()

    all_results = []
    total_tests = NUM_ROUNDS * len(PROMPTS)

    print(f"🔬 Starting main tests, with a total of {total_tests} requests...")

    for i in range(NUM_ROUNDS):
        print(f"\n--- Round {i + 1}/{NUM_ROUNDS} ---")
        for j, prompt in enumerate(PROMPTS):
            test_num = i * len(PROMPTS) + j + 1
            print(f"  ({test_num}/{total_tests}) Testing Prompt #{j+1}...")
            result = run_single_test(prompt)
            if result:
                all_results.append(result)
            if test_num < total_tests:
                time.sleep(DELAY_BETWEEN_TESTS)

    if not all_results:
        print("\n🚫 No valid test results were collected. Cannot generate a summary.")
        sys.exit(1)

    gen_throughputs = [r["gen_throughput"] for r in all_results]
    prompt_throughputs = [r["prompt_throughput"] for r in all_results]
    ttfts = [r["ttft"] for r in all_results]

    print("\n\n" + "=" * 60)
    print("📊 Performance Test Summary Report")
    print("=" * 60)
    print(f"Successfully collected data points: {len(all_results)} / {total_tests}")
    print("-" * 60)

    print("🔑 Core Metrics (Single-User Performance):")
    print("\n1. Generation Throughput (tokens/s)")
    print(f"   - Average: {calculate_mean(gen_throughputs):.2f}")
    print(f"   - Std Dev: {calculate_std_dev(gen_throughputs):.2f} (lower is more stable)")
    print(f"   - Min:     {min(gen_throughputs):.2f}")
    print(f"   - Max:     {max(gen_throughputs):.2f}")

    print("\n2. Prompt Processing Throughput (tokens/s)")
    print(f"   - Average: {calculate_mean(prompt_throughputs):.2f}")
    print(f"   - Std Dev: {calculate_std_dev(prompt_throughputs):.2f}")
    print(f"   - Min:     {min(prompt_throughputs):.2f}")
    print(f"   - Max:     {max(prompt_throughputs):.2f}")

    print("\n3. Time to First Token (TTFT - seconds)")
    print("   (Note: Approximated by prompt evaluation time)")
    print(f"   - Average: {calculate_mean(ttfts):.4f}")
    print(f"   - Std Dev: {calculate_std_dev(ttfts):.4f}")
    print(f"   - Min:     {min(ttfts):.4f} (fastest response)")
    print(f"   - Max:     {max(ttfts):.4f} (slowest response)")

    print("\n" + "=" * 60)
    print("✅ Testing complete.")

if __name__ == "__main__":
    main()
