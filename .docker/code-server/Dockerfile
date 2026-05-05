#
# Code-Server — VS Code in Browser with Sandboxes access
# Build: docker build -t rain-code-server .docker/code-server
#

FROM codercom/code-server:4.97.2

USER root

# Install Node.js tools for workshop projects
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Bun for fast package management in sandboxes
RUN npm install -g bun@1.3.12

# Install common VS Code extensions useful for workshop
RUN code-server --install-extension dbaeumer.vscode-eslint \
    && code-server --install-extension esbenp.prettier-vscode \
    && code-server --install-extension bradlc.vscode-tailwindcss \
    && code-server --install-extension ms-vscode.vscode-typescript-next \
    && code-server --install-extension prisma.prisma \
    && code-server --install-extension ms-python.python \
    && code-server --install-extension github.copilot \
    && code-server --install-extension github.copilot-chat

# Sandboxes directory — shared with rain-api
RUN mkdir -p /home/coder/sandboxes && chown -R coder:coder /home/coder/sandboxes

# code-server settings: disable telemetry, enable iframe, disable auth for local use
RUN mkdir -p /home/coder/.config/code-server && \
    echo '{"enable": true}' > /home/coder/.config/code-server/coder.json && \
    chown -R coder:coder /home/coder/.config

USER coder

WORKDIR /home/coder

EXPOSE 8080

# --disable-workspace-trust: don't prompt about workspace trust
# --disable-telemetry: disable data collection
ENTRYPOINT ["/usr/bin/entrypoint.sh", \
    "--disable-workspace-trust", \
    "--disable-telemetry", \
    "--bind-addr", "0.0.0.0:8080", \
    "."]
