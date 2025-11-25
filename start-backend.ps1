# Script para iniciar apenas o Backend
# Execute: .\start-backend.ps1

Write-Host "Iniciando Backend..." -ForegroundColor Cyan
Write-Host ""

# Verificar se já está rodando
$backendPort = 8001
# Verificar apenas estado Listen (servidor ativo), não TimeWait
$backendProcess = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue

if ($backendProcess) {
    $processId = $backendProcess.OwningProcess | Select-Object -First 1
    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    
    if ($proc) {
        Write-Host "Backend ja esta rodando na porta $backendPort (PID: $processId)" -ForegroundColor Yellow
        Write-Host "   Processo: $($proc.ProcessName)" -ForegroundColor Gray
        Write-Host "   Use .\stop.ps1 para parar antes de iniciar novamente" -ForegroundColor Gray
        exit
    } else {
        Write-Host "Porta $backendPort em uso mas processo nao encontrado (zombie)" -ForegroundColor Yellow
        Write-Host "   Tentando limpar processo zombie..." -ForegroundColor Yellow
        try {
            & cmd.exe /c "taskkill /F /PID $processId /T" 2>$null | Out-Null
            Start-Sleep -Seconds 2
            # Verificar se limpou
            $check = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
            if ($check) {
                Write-Host "   Aviso: Porta ainda em uso após tentativa de limpeza" -ForegroundColor Yellow
                Write-Host "   Tentando iniciar mesmo assim (uvicorn pode reutilizar a porta)..." -ForegroundColor Yellow
                Write-Host "   Se falhar, execute: .\limpar-porta-8001.ps1" -ForegroundColor Cyan
            } else {
                Write-Host "   Processo zombie removido! Continuando..." -ForegroundColor Green
            }
        } catch {
            Write-Host "   Erro ao limpar: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "   Tentando iniciar mesmo assim..." -ForegroundColor Yellow
        }
    }
}

# Verificar se o ambiente virtual existe
if (-not (Test-Path "backend\venv\Scripts\Activate.ps1")) {
    Write-Host "Ambiente virtual nao encontrado!" -ForegroundColor Red
    Write-Host "   Execute primeiro: .\setup.ps1" -ForegroundColor Yellow
    exit
}

# Obter o caminho absoluto do diretório do script
if ($PSScriptRoot) {
    $scriptDir = $PSScriptRoot
} else {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$backendDir = Join-Path $scriptDir "backend"
$backendDir = (Resolve-Path $backendDir -ErrorAction SilentlyContinue).Path
if (-not $backendDir) {
    $backendDir = Join-Path (Get-Location).Path "backend"
}

Write-Host "Diretorio do backend: $backendDir" -ForegroundColor Gray

# Script para executar em nova janela
$backendScript = @"
Set-Location '$backendDir'
if (-not (Test-Path '.\venv\Scripts\Activate.ps1')) {
    Write-Host 'ERRO: Ambiente virtual nao encontrado!' -ForegroundColor Red
    Write-Host 'Caminho esperado: $backendDir\venv\Scripts\Activate.ps1' -ForegroundColor Yellow
    Write-Host 'Execute: .\setup.ps1' -ForegroundColor Yellow
    pause
    exit
}
.\venv\Scripts\Activate.ps1
Write-Host 'Backend iniciando em http://localhost:8001' -ForegroundColor Green
Write-Host 'Documentacao: http://localhost:8001/api/v1/docs' -ForegroundColor Cyan
Write-Host ''
# Verificar se uvicorn está disponível
`$uvicornPath = (Get-Command uvicorn -ErrorAction SilentlyContinue)
if (-not `$uvicornPath) {
    Write-Host 'ERRO: uvicorn nao encontrado!' -ForegroundColor Red
    Write-Host 'Instalando dependencias...' -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host 'Tentando novamente...' -ForegroundColor Yellow
}
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
"@

Write-Host "Abrindo terminal para Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript

Write-Host ""
Write-Host "Backend iniciando em nova janela..." -ForegroundColor Green
Write-Host "   URL: http://localhost:8001" -ForegroundColor Cyan
Write-Host "   Docs: http://localhost:8001/api/v1/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Aguarde alguns segundos para o servidor iniciar" -ForegroundColor Yellow

