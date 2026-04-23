# Estágio 1: Build (Node 20 requerido por vite-plugin-pwa/workbox e outras deps)
FROM node:20-alpine AS builder

WORKDIR /app

# Aceitar argumento para URL da API
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
ARG VITE_APP_VERSION
ENV VITE_APP_VERSION=$VITE_APP_VERSION
ARG SOURCE_COMMIT
ENV SOURCE_COMMIT=$SOURCE_COMMIT
ARG COMMIT_SHA
ENV COMMIT_SHA=$COMMIT_SHA
ARG VITE_BUILD_TIME
ENV VITE_BUILD_TIME=$VITE_BUILD_TIME

# Copiar arquivos de dependências
COPY package*.json ./

# Instalar dependências
RUN npm ci

# Copiar código fonte
COPY . .

# Build da aplicação com versionamento em cascata
RUN set -eu; \
    RESOLVED_VERSION="${VITE_APP_VERSION:-}"; \
    if [ -z "$RESOLVED_VERSION" ] && [ -n "${SOURCE_COMMIT:-}" ]; then \
      RESOLVED_VERSION="$(echo "$SOURCE_COMMIT" | cut -c1-7)"; \
    fi; \
    if [ -z "$RESOLVED_VERSION" ] && [ -n "${COMMIT_SHA:-}" ]; then \
      RESOLVED_VERSION="$(echo "$COMMIT_SHA" | cut -c1-7)"; \
    fi; \
    if [ -z "$RESOLVED_VERSION" ] && command -v git >/dev/null 2>&1 && [ -d .git ]; then \
      RESOLVED_VERSION="$(git rev-parse --short HEAD || true)"; \
    fi; \
    if [ -z "$RESOLVED_VERSION" ]; then \
      RESOLVED_VERSION="dev"; \
    fi; \
    RESOLVED_BUILD_TIME="${VITE_BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; \
    export VITE_APP_VERSION="$RESOLVED_VERSION"; \
    export VITE_BUILD_TIME="$RESOLVED_BUILD_TIME"; \
    echo "Building frontend version=$VITE_APP_VERSION build_time=$VITE_BUILD_TIME"; \
    npm run build

# Estágio 2: Servir arquivos estáticos (sem Nginx, pois será usado Nginx externo)
FROM nginx:alpine

# Copiar arquivos buildados
COPY --from=builder /app/dist /usr/share/nginx/html

# Configuração básica do Nginx (será sobrescrita pelo proxy reverso externo)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expor porta (será acessada pelo Nginx externo via rede Docker)
EXPOSE 80

# Iniciar Nginx
CMD ["nginx", "-g", "daemon off;"]

