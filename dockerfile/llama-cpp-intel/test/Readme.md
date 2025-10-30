# `llama-cpp-intel-builder`

This is an automatic builder to build `llama.cpp:server` for a specific architecture of Intel CPU.

By default it builds a highly‑optimized `llama-server` Docker image for Alder Lake (Intel Core 12th‑gen) and Skylake (Intel Core 6th‑10th‑gen).

Compile from the latest release source code of [llama.cpp](https://github.com/ggml-org/llama.cpp).

Use Intel icx & icpx as the compiler, and use Intel MKL to accelerate vector calculations with the AVX2 instruction set.  

I am not a C++ expert, I cannot successfully compile with `-ipo` enabled, and I also cannot shrink docker image size by removing unused .so files.  

**Reminder:** The text‑generation speed on CPU heavily rely on the memory bandwidth. For dual‑channel DDR4 (about 50 GB/s), you can’t speed up text generation merely by improving CPU vector‑calculation performance. The only way to improve it is to increase memory bandwidth: use DDR5 or quad‑channel memory.

The goal of this project is to optimize **TTFT** for a real‑time translation app.

## Performance test
test scripts and results are in `/test`.

**Hardware**:  
- **CPU:** Intel G7400 (Alder Lake 2C4T)  
- **RAM:** DDR4 2133 MHz dual‑channel  

**Model**: `qwen3:30b-a3b-instruct-2507-q4_K_M`

---

### LLAMA‑CPP official release

| Metric | Average | Std Dev | Min | Max |
|--------|---------|---------|-----|-----|
| Generation Throughput (tokens/s) | 10.44 | 0.14 | 10.29 | 10.69 |
| Prompt Processing Throughput (tokens/s) | 24.12 | 0.28 | 23.73 | 24.58 |
| Time to First Token (TTFT – seconds) | 5.2760 | 1.4223 | 3.4175 | 7.0276 |

---

### LLAMA‑CPP built for Alder Lake

| Metric | Average | Std Dev | Min | Max |
|--------|---------|---------|-----|-----|
| Generation Throughput (tokens/s) | 10.76 | 0.11 | 10.62 | 10.96 |
| Prompt Processing Throughput (tokens/s) | 27.18 | 1.09 | 25.45 | 28.87 |
| Time to First Token (TTFT – seconds) | 4.6558 | 1.1577 | 3.0686 | 6.1316 |

---

### Ollama official release

| Metric | Average | Std Dev | Min | Max |
|--------|---------|---------|-----|-----|
| Generation Throughput (tokens/s) | 10.29 | 0.29 | 9.95 | 10.86 |
| Prompt Processing Throughput (tokens/s) | 21.90 | 0.74 | 20.93 | 22.88 |
| Time to First Token (TTFT – seconds) | 6.0039 | 1.7005 | 3.8455 | 8.1210 |
