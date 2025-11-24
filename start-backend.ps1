# Script para iniciar apenas o Backend
# Execute: .\start-backend.ps1

Write-Host "Iniciando Backend..." -ForegroundColor Cyan
Write-Host ""

# Verificar se já está rodando
$backendPort = 8001
$backendProcess = Get-NetTCPConnection -LocalPort $backendPort -ErrorAction SilentlyContinue

if ($backendProcess) {
    Write-Host "Backend ja esta rodando na porta $backendPort" -ForegroundColor Yellow
    Write-Host "   Use .\stop.ps1 para parar antes de iniciar novamente" -ForegroundColor Gray
    exit
}

# Verificar se o ambiente virtual existe
if (-not (Test-Path "backend\venv\Scripts\Activate.ps1")) {
    Write-Host "Ambiente virtual nao encontrado!" -ForegroundColor Red
    Write-Host "   Execute primeiro: .\setup.ps1" -ForegroundColor Yellow
    exit
}

# Script para executar em nova janela
$backendScript = {
    Set-Location "$PSScriptRoot\backend"
    if (Test-Path ".\venv\Scripts\Activate.ps1") {
        .\venv\Scripts\Activate.ps1
    }
    Write-Host "Backend iniciando em http://localhost:8001" -ForegroundColor Green
    Write-Host "Documentacao: http://localhost:8001/api/v1/docs" -ForegroundColor Cyan
    Write-Host ""
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
}

Write-Host "Abrindo terminal para Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {$($backendScript.ToString())}"

Write-Host ""
Write-Host "Backend iniciando em nova janela..." -ForegroundColor Green
Write-Host "   URL: http://localhost:8001" -ForegroundColor Cyan
Write-Host "   Docs: http://localhost:8001/api/v1/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Aguarde alguns segundos para o servidor iniciar" -ForegroundColor Yellow

