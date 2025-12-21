ARG MARCH=alderlake
ARG TARGETARCH=amd64

FROM intel/oneapi-basekit:2025.3.0-0-devel-ubuntu22.04 AS build

RUN apt-get update && \
    apt-get install -y build-essential git cmake libcurl4-openssl-dev jq wget

WORKDIR /app

RUN for i in 1 2 3; do \
      LATEST_RELEASE_URL=$(curl -s "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest" | jq -r .tarball_url) && \
      wget -qO- "$LATEST_RELEASE_URL" | tar -xz --strip-components=1 && break || \
      { echo "Attempt $i failed, retrying..."; sleep 2; }; \
    done
    
RUN  cmake -S . -B build -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Intel10_64lp -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx -DCMAKE_C_FLAGS="-O3 -march=${MARCH}" -DCMAKE_CXX_FLAGS="-O3 -march=${MARCH}" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DLLAMA_BUILD_TESTS=OFF -DGGML_BACKEND_DL=ON -DGGML_CPU_ALL_VARIANTS=ON; cmake --build build -j $(nproc)

RUN mkdir -p /app/lib && \
    find build -name "*.so*" -exec cp -P {} /app/lib \;

RUN mkdir -p /app/full \
    && cp build/bin/* /app/full \
    && cp *.py /app/full \
    && cp -r gguf-py /app/full \
    && cp -r requirements /app/full \
    && cp requirements.txt /app/full \
    && cp .devops/tools.sh /app/full/tools.sh

FROM intel/oneapi-runtime:2025.3.0-0-devel-ubuntu22.04 AS final

RUN apt-get update \
    && apt-get install -y libgomp1 curl\
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
