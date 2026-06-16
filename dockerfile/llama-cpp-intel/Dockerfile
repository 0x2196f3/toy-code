ARG TARGETARCH=amd64
ARG MARCH=alderlake
ARG VERSION=b9592

FROM docker.io/intel/oneapi-toolkit:2026.0.0-devel-ubuntu24.04 AS build

ARG TARGETARCH
ARG MARCH
ARG VERSION

RUN apt-get update && \
    apt-get install -y gcc-14 g++-14 build-essential git cmake libssl-dev jq wget curl

ENV CC=gcc-14 CXX=g++-14

WORKDIR /app

RUN if [ -n "${VERSION}" ]; then \
      TAG="${VERSION}"; \
    else \
      TAG=$(curl -s "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest" | jq -r .tag_name); \
    fi && \
    git clone --branch "$TAG" https://github.com/ggml-org/llama.cpp.git . || ( \
      rm -rf ./* ./.git && \
      git clone https://github.com/ggml-org/llama.cpp.git . && \
      git fetch --tags && \
      git checkout "tags/${TAG}" -b "build-${TAG}" \
    )

RUN if [ "$TARGETARCH" = "amd64" ]; then \
        cmake -S . -B build \
            -DCMAKE_C_COMPILER=icx \
            -DCMAKE_CXX_COMPILER=icpx \
            -DGGML_BLAS=ON \
            -DGGML_BLAS_VENDOR=Intel10_64lp \
            -DCMAKE_C_FLAGS="-O3 -x${MARCH} -mtune=${MARCH}" \
            -DCMAKE_CXX_FLAGS="-O3 -x${MARCH} -mtune=${MARCH}" \
            -DGGML_AVX=ON \
            -DGGML_AVX2=ON \
            -DGGML_AVX512=OFF \
            -DGGML_F16C=ON \
            -DGGML_FMA=ON \
            -DCMAKE_BUILD_TYPE=Release \
            -DGGML_NATIVE=OFF \
            -DLLAMA_BUILD_TESTS=OFF \
            -DGGML_BACKEND_DL=ON \
            -DGGML_CPU_ALL_VARIANTS=OFF; \
    else \
        echo "Unsupported architecture"; \
        exit 1; \
    fi && \
    cmake --build build -j $(nproc)

RUN find /app -type f -name "*.so*" -exec strip --strip-unneeded {} \; 2>/dev/null || true

RUN mkdir -p /app/lib && \
    find build -name "*.so*" -exec cp -P {} /app/lib \;

RUN mkdir -p /app/full \
    && cp build/bin/* /app/full \
    && cp *.py /app/full \
    && cp -r conversion /app/full \
    && cp -r gguf-py /app/full \
    && cp -r requirements /app/full \
    && cp requirements.txt /app/full \
    && cp .devops/tools.sh /app/full/tools.sh

FROM docker.io/intel/oneapi-runtime:2026.0.0-devel-ubuntu24.04 AS final

RUN apt-get update \
    && apt-get install -y libgomp1 curl ffmpeg \
    && apt autoremove -y \
    && apt clean -y \
    && rm -rf /tmp/* /var/tmp/* \
    && find /var/cache/apt/archives /var/lib/apt/lists -not -name lock -type f -delete \
    && find /var/cache -type f -delete

ENV LLAMA_ARG_HOST=0.0.0.0

COPY --from=build /app/lib/ /app
COPY --from=build /app/full/llama-server /app

WORKDIR /app
HEALTHCHECK CMD [ "curl", "-f", "http://localhost:8080/health" ]
ENTRYPOINT [ "/app/llama-server" ]
