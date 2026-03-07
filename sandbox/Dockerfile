FROM ubuntu:22.04

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

# Create non-root user — required for Claude Code's --dangerously-skip-permissions flag
RUN useradd -m -u 1000 -s /bin/bash sandbox-user

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
