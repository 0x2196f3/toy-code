ARG MARCH=alderlake

FROM intel/oneapi-basekit:2025.3.0-0-devel-ubuntu24.04 AS build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential git cmake libcurl4-openssl-dev wget gnupg jq curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN LATEST_RELEASE_URL=$(curl -s "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest" | jq -r .tarball_url) && \
    wget -qO- "$LATEST_RELEASE_URL" | tar -xz --strip-components=1

RUN rm -rf build && \
    cmake -B build \
        -DGGML_BLAS=ON \
        -DGGML_BLAS_VENDOR=Intel10_64lp \
        -DCMAKE_C_COMPILER=icx \
        -DCMAKE_CXX_COMPILER=icpx \
        -DGGML_NATIVE=OFF \
        -DCMAKE_C_FLAGS="-O3 -march=${MARCH}" \
        -DCMAKE_CXX_FLAGS="-O3 -march=${MARCH}" && \
    cmake --build build --config Release

RUN mkdir -p /app/lib && \
    find build -name "*.so*" -exec cp -P {} /app/lib \;


FROM intel/oneapi-runtime:2025.3.0-0-devel-ubuntu24.04 AS final

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && apt autoremove -y \
    && apt clean -y \
    && rm -rf /tmp/* /var/tmp/* \
    && find /var/cache/apt/archives /var/lib/apt/lists -not -name lock -type f -delete \
    && find /var/cache -type f -delete

COPY --from=build /app/lib/ /app
COPY --from=build /app/dist/* /app

ENV LLAMA_ARG_HOST=0.0.0.0

WORKDIR /app

HEALTHCHECK CMD [ "curl", "-f", "http://localhost:8080/health" ]

ENTRYPOINT [ "/app/llama-server" ]
