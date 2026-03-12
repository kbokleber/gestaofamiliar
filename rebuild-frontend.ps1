# Script para rebuild apenas do frontend (útil após atualizações)
# Uso: .\rebuild-frontend.ps1

$ErrorActionPreference = "Stop"

Write-Host "🔄 Rebuild do Frontend..." -ForegroundColor Cyan
Write-Host ""

$commitDate = (git show -s --format=%cs HEAD).Trim() -replace '-', '.'
$commitShort = (git rev-parse --short HEAD).Trim()
$appVersion = "$commitDate-$commitShort"

Write-Host "🏷️  Versão calculada para o frontend: $appVersion" -ForegroundColor Green
Write-Host ""

# Verificar se está no diretório correto
if (-not (Test-Path "frontend/Dockerfile")) {
    Write-Host "❌ Erro: frontend/Dockerfile não encontrado!" -ForegroundColor Red
    Write-Host "Execute este script na raiz do projeto."
    exit 1
}

# Verificar se Docker Swarm está ativo
$swarmStatus = docker info 2>&1 | Select-String "Swarm: active"
if ($swarmStatus) {
    Write-Host "📦 Docker Swarm detectado - Rebuild com atualização do stack" -ForegroundColor Green
    Write-Host ""
    
    # Build da imagem do frontend
    Write-Host "🔨 Construindo imagem do frontend..." -ForegroundColor Yellow
    docker build --build-arg VITE_APP_VERSION=$appVersion -t sistema-familiar-frontend:latest ./frontend
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erro ao construir imagem!" -ForegroundColor Red
        exit 1
    }
    
    # Atualizar o serviço no stack
    Write-Host "🚀 Atualizando serviço frontend no stack..." -ForegroundColor Yellow
    docker service update --force --image sistema-familiar-frontend:latest sistema-familiar_frontend
    
    Write-Host ""
    Write-Host "✅ Frontend atualizado com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Para verificar os logs:"
    Write-Host "  docker service logs -f sistema-familiar_frontend" -ForegroundColor Cyan
} else {
    Write-Host "📦 Docker Compose detectado - Rebuild do container" -ForegroundColor Green
    Write-Host ""
    
    # Rebuild apenas do frontend
    Write-Host "🔨 Rebuild do frontend..." -ForegroundColor Yellow
    docker-compose build --no-cache --build-arg VITE_APP_VERSION=$appVersion frontend
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erro ao fazer rebuild!" -ForegroundColor Red
        exit 1
    }
    
    # Reiniciar o container
    Write-Host "🔄 Reiniciando container frontend..." -ForegroundColor Yellow
    docker-compose up -d --force-recreate frontend
    
    Write-Host ""
    Write-Host "✅ Frontend atualizado com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Para verificar os logs:"
    Write-Host "  docker-compose logs -f frontend" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "💡 Dica: Limpe o cache do navegador (Ctrl+Shift+R) para ver as mudanças!" -ForegroundColor Yellow

