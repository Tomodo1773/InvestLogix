FROM node:22

WORKDIR /app

# pnpmを有効化
RUN corepack enable && corepack prepare pnpm@latest --activate
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL -o /usr/local/bin/sfw \
        https://github.com/SocketDev/sfw-free/releases/latest/download/sfw-free-linux-x86_64 \
    && chmod +x /usr/local/bin/sfw \
    && rm -rf /var/lib/apt/lists/*

CMD ["sh", "-c", "sfw pnpm install && pnpm dev --host"]
