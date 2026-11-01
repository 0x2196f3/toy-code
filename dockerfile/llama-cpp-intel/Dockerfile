ARG UBUNTU_VERSION=24.04
ARG MARCH=alderlake
ARG APP_VERSION=b10156

FROM docker.io/intel/oneapi-toolkit:2026.2.0-devel-ubuntu$UBUNTU_VERSION AS build

ARG MARCH
ARG APP_VERSION

RUN apt-get update && \
    apt-get install -y gcc-14 g++-14 build-essential git cmake libssl-dev jq wget curl

ENV CC=gcc-14 CXX=g++-14

WORKDIR /app

RUN if [ -n "${APP_VERSION}" ]; then \
      TAG="${APP_VERSION}"; \
    else \
      TAG=$(curl -s "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest" | jq -r .tag_name); \
    fi && \
    git clone https://github.com/ggml-org/llama.cpp.git . && \
        git fetch --tags && \
        git checkout "tags/${TAG}"

RUN cmake -S . -B build \
            -DCMAKE_C_COMPILER=icx \
            -DCMAKE_CXX_COMPILER=icpx \
            -DCMAKE_C_FLAGS="-O3 -march=${MARCH}" \
            -DCMAKE_CXX_FLAGS="-O3 -march=${MARCH}" \
            -DCMAKE_BUILD_TYPE=Release \
            -DGGML_NATIVE=OFF \
            -DGGML_LTO=ON \
            -DLLAMA_BUILD_TESTS=OFF \
            -DGGML_BACKEND_DL=ON \
            -DGGML_CPU_ALL_VARIANTS=OFF && \
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

FROM docker.io/intel/oneapi-toolkit:2026.2.0-devel-ubuntu$UBUNTU_VERSION AS final

RUN apt-get update \
    && apt-get install -y libgomp1 curl ffmpeg \
    && apt autoremove -y \
    && apt clean -y \
    && rm -rf /tmp/* /var/tmp/* \
    && find /var/cache/apt/archives /var/lib/apt/lists -not -name lock -type f -delete \
    && find /var/cache -type f -delete

ENV LLAMA_ARG_HOST=0.0.0.0

COPY --from=build /app/lib/ /app
COPY --from=build /app/full/llama /app/full/llama-server /app

WORKDIR /app

HEALTHCHECK CMD [ "curl", "-f", "http://localhost:8080/health" ]

ENTRYPOINT [ "/app/llama-server" ]
