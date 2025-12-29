ARG TARGETARCH=amd64
ARG MARCH=alderlake
ARG VERSION

# Use the same base image
FROM intel/oneapi-basekit:2025.3.0-0-devel-ubuntu22.04 AS build

ARG TARGETARCH
ARG MARCH
ARG VERSION

# Install dependencies (same as before)
RUN apt-get update && \
    apt-get install -y build-essential git cmake libcurl4-openssl-dev jq wget curl

WORKDIR /app

# Logic to fetch source (same as before)
RUN if [ -n "${VERSION}" ]; then \
        SRC_URL="https://github.com/ggml-org/llama.cpp/archive/refs/tags/b7406.tar.gz"; \
    else \
        SRC_URL=$(curl -s "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest" | jq -r .tarball_url); \
    fi && \
    wget -O- "$SRC_URL" | tar -xz --strip-components=1

# OPTIMIZED BUILD STEP
# 1. -march=alderlake / -mtune=alderlake: Optimize instruction scheduling for i5-12400
# 2. -xCORE-AVX2: Intel specific flag to force AVX2 specialization
# 3. -flto: Link Time Optimization for cross-module inlining
# 4. -mno-avx512f: Explicitly disable AVX512 to prevent any auto-vectorization attempts that might crash
# 5. GGML_CPU_ALL_VARIANTS=OFF: Disable runtime dispatch; build ONLY for this CPU
RUN if [ "$TARGETARCH" = "amd64" ]; then \
        cmake -S . -B build \
            -DCMAKE_C_COMPILER=icx \
            -DCMAKE_CXX_COMPILER=icpx \
            -DGGML_BLAS=ON \
            -DGGML_BLAS_VENDOR=Intel10_64lp \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_C_FLAGS="-O3 -march=alderlake -mtune=alderlake -mno-avx512f -fno-math-errno -fno-trapping-math" \
            -DCMAKE_CXX_FLAGS="-O3 -march=alderlake -mtune=alderlake -mno-avx512f -fno-math-errno -fno-trapping-math" \
            -DGGML_NATIVE=OFF \
            -DGGML_CPU_ALL_VARIANTS=OFF \
            -DGGML_AVX=ON \
            -DGGML_AVX2=ON \
            -DGGML_F16C=ON \
            -DGGML_FMA=ON \
            -DLLAMA_BUILD_TESTS=OFF \
            -DGGML_BACKEND_DL=ON; \
    else \
        echo "Unsupported architecture"; \
        exit 1; \
    fi && \
    cmake --build build -j $(nproc)

# Strip debug symbols to reduce size/load time
RUN find /app -type f -name "*.so*" -exec strip --strip-unneeded {} \; 2>/dev/null || true

RUN mkdir -p /app/lib && \
    find build -name "*.so*" -exec cp -P {} /app/lib \;

RUN mkdir -p /app/full \
    && cp build/bin/* /app/full \
    && cp *.py /app/full \
    && cp -r gguf-py /app/full \
    && cp -r requirements /app/full \
    && cp requirements.txt /app/full \
    && cp .devops/tools.sh /app/full/tools.sh

# Final stage (Keep consistent with original)
FROM intel/oneapi-runtime:2025.3.0-0-devel-ubuntu22.04 AS final

RUN apt-get update \
    && apt-get install -y libgomp1 curl \
    && apt autoremove -y \
    && apt clean -y \
    && rm -rf /tmp/* /var/tmp/* \
    && find /var/cache/apt/archives /var/lib/apt/lists -not -name lock -type f -delete \
    && find /var/cache -type f -delete

ENV LLAMA_ARG_HOST=0.0.0.0

# Set MKL threading to 1 for inference (often faster to let llama.cpp manage threads)
# You can override this at runtime if needed.
ENV MKL_NUM_THREADS=1 
ENV MKL_DYNAMIC=FALSE

COPY --from=build /app/lib/ /app
COPY --from=build /app/full/llama-server /app

WORKDIR /app
HEALTHCHECK CMD [ "curl", "-f", "http://localhost:8080/health" ]
ENTRYPOINT [ "/app/llama-server" ]
