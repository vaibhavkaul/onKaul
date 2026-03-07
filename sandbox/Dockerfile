FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Node.js LTS (needed for static serving, Vite dev servers, and other npm-based apps)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install serve globally
RUN npm install -g serve

# Python 3.12 (default on Ubuntu 24.04) + pre-installed FastAPI deps for fullstack-python-vite sandboxes
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir --break-system-packages fastapi "uvicorn[standard]"

# Ubuntu 24.04 ships with an 'ubuntu' user at UID 1000 — rename it to sandbox-user
RUN usermod -l sandbox-user -d /home/sandbox-user -m ubuntu && \
    groupmod -n sandbox-user ubuntu

# Install Claude Code as sandbox-user so it lands in their home dir
USER sandbox-user
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH="/home/sandbox-user/.local/bin:$PATH"

# Back to root to set up workspace dir and copy entrypoint
USER root
RUN mkdir -p /workspace && chown sandbox-user:sandbox-user /workspace

WORKDIR /workspace

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run everything as the non-root user
USER sandbox-user

ENTRYPOINT ["/entrypoint.sh"]
