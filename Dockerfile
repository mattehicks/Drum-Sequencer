# D20 Synth Workbench server image. Build from the repo root:
#   docker build -t d20-synth .
FROM node:22-alpine

ENV NODE_ENV=production \
    PORT=8080 \
    APP_ROOT=/app \
    DB_FILE=/data/d20.db

WORKDIR /app/server
COPY server/package.json server/package-lock.json* ./
RUN npm ci --omit=dev --no-audit --no-fund || npm install --omit=dev --no-audit --no-fund

COPY server/src ./src
COPY server/public ./public
COPY V2 /app/V2
COPY browser /app/browser

RUN mkdir -p /data && chown -R node:node /data
USER node
VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

CMD ["node", "--disable-warning=ExperimentalWarning", "src/server.js"]
