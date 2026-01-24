FROM node:22-alpine

WORKDIR /app

# pnpmを有効化
RUN corepack enable && corepack prepare pnpm@latest --activate

CMD ["sh", "-c", "pnpm install && pnpm dev --host"]
