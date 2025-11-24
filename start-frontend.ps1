# Script para iniciar apenas o Frontend
# Execute: .\start-frontend.ps1

Write-Host "Iniciando Frontend..." -ForegroundColor Cyan
Write-Host ""

# Verificar se já está rodando
$frontendPort = 5173
$frontendProcess = Get-NetTCPConnection -LocalPort $frontendPort -ErrorAction SilentlyContinue

if ($frontendProcess) {
    Write-Host "Frontend ja esta rodando na porta $frontendPort" -ForegroundColor Yellow
    Write-Host "   Use .\stop.ps1 para parar antes de iniciar novamente" -ForegroundColor Gray
    exit
}

# Verificar se o diretório frontend existe
if (-not (Test-Path "frontend")) {
    Write-Host "ERRO: Diretorio frontend nao encontrado!" -ForegroundColor Red
    exit
}

# Verificar se package.json existe
if (-not (Test-Path "frontend\package.json")) {
    Write-Host "ERRO: package.json nao encontrado no diretorio frontend!" -ForegroundColor Red
    exit
}

# Verificar se node_modules existe
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Dependencias nao instaladas!" -ForegroundColor Yellow
    Write-Host "   Instalando dependencias..." -ForegroundColor Gray
    Set-Location frontend
    npm install
    Set-Location ..
}

# Mudar para o diretório do frontend
Set-Location frontend

Write-Host "Iniciando servidor Frontend..." -ForegroundColor Green
Write-Host "   URL: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pressione Ctrl+C para parar" -ForegroundColor Yellow
Write-Host ""

npm run dev

