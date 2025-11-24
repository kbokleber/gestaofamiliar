# Script de deploy para Docker Swarm (PowerShell)
# Uso: .\deploy.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 Iniciando deploy do Sistema Familiar..." -ForegroundColor Green

# Verificar se está no diretório correto
if (-not (Test-Path "docker-stack.yml")) {
    Write-Host "❌ Erro: docker-stack.yml não encontrado!" -ForegroundColor Red
    Write-Host "Execute este script na raiz do projeto."
    exit 1
}

# Verificar se Docker Swarm está inicializado
$swarmStatus = docker info 2>&1 | Select-String "Swarm: active"
if (-not $swarmStatus) {
    Write-Host "⚠️  Docker Swarm não está inicializado." -ForegroundColor Yellow
    Write-Host "Inicializando Docker Swarm..."
    docker swarm init
}

# Build das imagens
Write-Host "📦 Construindo imagens Docker..." -ForegroundColor Green
docker build -t sistema-familiar-backend:latest ./backend
if ($LASTEXITCODE -ne 0) { exit 1 }

docker build -t sistema-familiar-frontend:latest ./frontend
if ($LASTEXITCODE -ne 0) { exit 1 }

# Verificar se .env existe
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  Arquivo .env não encontrado!" -ForegroundColor Yellow
    Write-Host "Copiando .env.example para .env..."
    Copy-Item .env.example .env
    Write-Host "⚠️  IMPORTANTE: Edite o arquivo .env com suas configurações antes de continuar!" -ForegroundColor Red
    Write-Host "⚠️  Especialmente a DATABASE_URL para conectar ao banco existente!" -ForegroundColor Yellow
    exit 1
}

# Verificar se DATABASE_URL está configurada
$envContent = Get-Content .env -Raw
if (-not $envContent -match "DATABASE_URL=" -or $envContent -match "DATABASE_URL=postgresql://usuario:senha") {
    Write-Host "❌ Erro: DATABASE_URL não está configurada corretamente no .env!" -ForegroundColor Red
    Write-Host "Configure a URL de conexão com seu banco de dados PostgreSQL existente."
    exit 1
}

Write-Host "ℹ️  Certifique-se de que a rede do banco de dados está acessível." -ForegroundColor Green
Write-Host "   Se o banco estiver em outra rede Docker, crie uma rede externa ou ajuste o docker-stack.yml" -ForegroundColor Yellow

# Deploy do stack
Write-Host "🚀 Fazendo deploy do stack..." -ForegroundColor Green
docker stack deploy -c docker-stack.yml sistema-familiar

# Aguardar serviços iniciarem
Write-Host "⏳ Aguardando serviços iniciarem..." -ForegroundColor Green
Start-Sleep -Seconds 10

# Verificar status
Write-Host "📊 Status dos serviços:" -ForegroundColor Green
docker stack services sistema-familiar

Write-Host "✅ Deploy concluído!" -ForegroundColor Green
Write-Host ""
Write-Host "Para verificar os logs:"
Write-Host "  docker service logs -f sistema-familiar_backend"
Write-Host "  docker service logs -f sistema-familiar_frontend"
Write-Host ""
Write-Host "Para remover o stack:"
Write-Host "  docker stack rm sistema-familiar"

