# Script para iniciar Backend e Frontend simultaneamente
# Execute: .\start.ps1

Write-Host "Iniciando Sistema Familiar..." -ForegroundColor Cyan
Write-Host ""

# Verificar status atual
$backendPort = 8001
$frontendPort = 5173
$backendRunning = Get-NetTCPConnection -LocalPort $backendPort -ErrorAction SilentlyContinue
$frontendRunning = Get-NetTCPConnection -LocalPort $frontendPort -ErrorAction SilentlyContinue

if ($backendRunning) {
    Write-Host "Backend ja esta rodando na porta $backendPort" -ForegroundColor Yellow
} else {
    Write-Host "Iniciando Backend..." -ForegroundColor Green
}

if ($frontendRunning) {
    Write-Host "Frontend ja esta rodando na porta $frontendPort" -ForegroundColor Yellow
} else {
    Write-Host "Iniciando Frontend..." -ForegroundColor Green
}

Write-Host ""

# Obter caminhos absolutos
$scriptRoot = $PSScriptRoot
$backendPath = Join-Path $scriptRoot "backend"
$frontendPath = Join-Path $scriptRoot "frontend"

# Verificar se os diretórios existem
if (-not (Test-Path $backendPath)) {
    Write-Host "ERRO: Diretorio backend nao encontrado!" -ForegroundColor Red
    exit
}

if (-not (Test-Path $frontendPath)) {
    Write-Host "ERRO: Diretorio frontend nao encontrado!" -ForegroundColor Red
    exit
}

# Verificar ambiente virtual do backend
if (-not (Test-Path (Join-Path $backendPath "venv\Scripts\Activate.ps1"))) {
    Write-Host "ERRO: Ambiente virtual do backend nao encontrado!" -ForegroundColor Red
    Write-Host "   Execute primeiro: .\setup.ps1" -ForegroundColor Yellow
    exit
}

# Verificar package.json do frontend
if (-not (Test-Path (Join-Path $frontendPath "package.json"))) {
    Write-Host "ERRO: package.json nao encontrado no frontend!" -ForegroundColor Red
    exit
}

Write-Host "Abrindo terminais..." -ForegroundColor Yellow

# Iniciar Backend em nova janela do PowerShell (se não estiver rodando)
if (-not $backendRunning) {
    $backendCommand = @"
Set-Location '$backendPath'
if (Test-Path '.\venv\Scripts\Activate.ps1') {
    .\venv\Scripts\Activate.ps1
}
Write-Host 'Backend iniciando em http://localhost:8001' -ForegroundColor Green
Write-Host 'Documentacao: http://localhost:8001/api/v1/docs' -ForegroundColor Cyan
Write-Host ''
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand
    Start-Sleep -Seconds 2
}

# Iniciar Frontend em nova janela do PowerShell (se não estiver rodando)
if (-not $frontendRunning) {
    $frontendCommand = @"
Set-Location '$frontendPath'
Write-Host 'Frontend iniciando em http://localhost:5173' -ForegroundColor Green
Write-Host ''
npm run dev
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand
}

Write-Host ""
Write-Host "Servidores iniciados!" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Backend: http://localhost:8001" -ForegroundColor Cyan
Write-Host "Docs: http://localhost:8001/api/v1/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para verificar status: .\status.ps1" -ForegroundColor Yellow
Write-Host "Para parar: .\stop.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Para parar os servidores, feche as janelas do PowerShell ou execute .\stop.ps1" -ForegroundColor Yellow
