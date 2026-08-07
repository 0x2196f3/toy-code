# syntax=docker/dockerfile:1

ARG CUDA_VERSION="13.3.1"
ARG UBUNTU_VERSION="26.04"
ARG COMFYUI_VERSION=""


FROM alpine/git AS source

ARG CACHE_BUST=1
ARG COMFYUI_VERSION 

WORKDIR /src
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && \
    if [ -z "$COMFYUI_VERSION" ]; then \
        TARGET_TAG=$(git describe --tags --abbrev=0); \
        echo "Checking out ComfyUI latest release tag: $TARGET_TAG"; \
        git checkout "$TARGET_TAG"; \
    else \
        echo "Checking out ComfyUI tag: $COMFYUI_VERSION"; \
        git checkout "$COMFYUI_VERSION"; \
    fi

WORKDIR /src/ComfyUI/custom_nodes
RUN for repo in \
        https://github.com/Fannovel16/comfyui_controlnet_aux.git \
        https://github.com/kijai/ComfyUI-KJNodes.git \
        https://github.com/city96/ComfyUI-GGUF.git \
    ; do \
        echo "Downloading: $repo" && git clone "$repo"; \
    done

WORKDIR /reqs
RUN mkdir -p ComfyUI && \
    cp /src/ComfyUI/requirements.txt ComfyUI/requirements.txt 2>/dev/null || true && \
    cd /src && \
    find ComfyUI/custom_nodes -name "requirements.txt" -exec sh -c 'mkdir -p "/reqs/$(dirname {})" && cp "{}" "/reqs/{}"' \;

FROM nvidia/cuda:${CUDA_VERSION}-base-ubuntu${UBUNTU_VERSION}

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && \ 
    apt-get install -y --no-install-recommends software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends python3.13 python3.13-venv python3.13-dev git build-essential libgl1 libglib2.0-0 libxcb1 && \ 
    rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN python3.13 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch torchsde torchvision torchaudio

COPY --from=source /reqs/ComfyUI/custom_nodes /app/ComfyUI/custom_nodes
RUN --mount=type=cache,target=/root/.cache/pip \
    find /app/ComfyUI/custom_nodes -name "requirements.txt" -exec pip install -r {} \; || true

COPY --from=source /reqs/ComfyUI/requirements.txt /app/ComfyUI/
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -f "/app/ComfyUI/requirements.txt" ]; then pip install -r /app/ComfyUI/requirements.txt; fi

COPY --from=source /src/ComfyUI /app/ComfyUI

RUN mkdir -p /app/ComfyUI/input /app/ComfyUI/output /app/ComfyUI/models /app/ComfyUI/custom_nodes /app/ComfyUI/user /app/backup_data && \
    cp -a /app/ComfyUI/input /app/ComfyUI/output /app/ComfyUI/models /app/ComfyUI/custom_nodes /app/ComfyUI/user /app/backup_data/ && \
    chmod -R 777 /app/ComfyUI/input /app/ComfyUI/output /app/ComfyUI/models /app/ComfyUI/custom_nodes /app/ComfyUI/user

RUN cat > /app/entrypoint.sh <<'EOF'
#!/bin/bash
umask 000

cp -rn /app/backup_data/input/. /app/ComfyUI/input/ 2>/dev/null || true
cp -rn /app/backup_data/output/. /app/ComfyUI/output/ 2>/dev/null || true
cp -rn /app/backup_data/models/. /app/ComfyUI/models/ 2>/dev/null || true
cp -rn /app/backup_data/user/. /app/ComfyUI/user/ 2>/dev/null || true

cp -rf /app/backup_data/custom_nodes/. /app/ComfyUI/custom_nodes/ 2>/dev/null || true

exec /opt/venv/bin/python /app/ComfyUI/main.py --listen 0.0.0.0
EOF

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]