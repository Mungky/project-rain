#
# Workshop-Web — Next.js 16 Frontend
# Build: docker build -t workshop-web apps/workshop-web
#

FROM node:20-slim AS deps

WORKDIR /app

# Bun for package management
RUN npm install -g bun@1.3.12

COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile --ignore-scripts

FROM node:20-slim AS builder

WORKDIR /app

# Copy bun binary from deps
COPY --from=deps /usr/local/bin/bun /usr/local/bin/bun
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /root/.bun /root/.bun

# Copy workspace deps (needed at build time)
COPY apps/workshop-web/package.json apps/workshop-web/next.config.ts apps/workshop-web/tsconfig.json apps/workshop-web/postcss.config.mjs apps/workshop-web/eslint.config.mjs ./apps/workshop-web/

# Install workspace-web deps
WORKDIR /app/apps/workshop-web
RUN bun install --frozen-lockfile --ignore-scripts 2>/dev/null || true

# Copy source
COPY apps/workshop-web/src/ ./src/
COPY apps/workshop-web/public/ ./public/

# Build Next.js
RUN bun run build

FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/apps/workshop-web/.next/standalone ./
COPY --from=builder /app/apps/workshop-web/.next/static ./.next/static
COPY --from=builder /app/apps/workshop-web/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
