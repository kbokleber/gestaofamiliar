# Estágio 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Copiar arquivos de dependências
COPY package*.json ./

# Instalar dependências
RUN npm ci

# Copiar código fonte
COPY . .

# Build da aplicação
RUN npm run build

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

