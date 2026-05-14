FROM node:20-slim AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM caddy:2-alpine
COPY --from=builder /app/dist /srv
COPY frontend/Caddyfile /etc/caddy/Caddyfile
