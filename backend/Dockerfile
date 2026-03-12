FROM python:3.11-slim

WORKDIR /app

ARG APP_VERSION=dev
ARG APP_COMMIT_SHORT=local
ARG APP_RELEASE_NAME=dev
ENV APP_VERSION=$APP_VERSION
ENV APP_COMMIT_SHORT=$APP_COMMIT_SHORT
ENV APP_RELEASE_NAME=$APP_RELEASE_NAME

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Expor porta
EXPOSE 8001

# Comando para iniciar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

