# Script para verificar status do Backend e Frontend
# Execute: .\status.ps1

Write-Host "Verificando status dos servicos..." -ForegroundColor Cyan
Write-Host ""

# Verificar Backend (porta 8001)
$backendPort = 8001
$backendProcess = Get-NetTCPConnection -LocalPort $backendPort -ErrorAction SilentlyContinue

if ($backendProcess) {
    $backendPID = $backendProcess.OwningProcess | Select-Object -First 1
    $backendProc = Get-Process -Id $backendPID -ErrorAction SilentlyContinue
    Write-Host "[OK] Backend: RODANDO" -ForegroundColor Green
    Write-Host "   Porta: $backendPort" -ForegroundColor Gray
    Write-Host "   PID: $backendPID" -ForegroundColor Gray
    if ($backendProc) {
        $memoriaMB = [math]::Round($backendProc.WorkingSet64 / 1MB, 2)
        Write-Host "   Processo: $($backendProc.ProcessName)" -ForegroundColor Gray
        Write-Host "   Memoria: $memoriaMB MB" -ForegroundColor Gray
    }
    
    # Testar conexao
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$backendPort/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "   Status API: Respondendo" -ForegroundColor Green
    } catch {
        Write-Host "   Status API: Nao respondeu" -ForegroundColor Yellow
    }
} else {
    Write-Host "[X] Backend: PARADO" -ForegroundColor Red
    Write-Host "   Porta $backendPort nao esta em uso" -ForegroundColor Gray
}

Write-Host ""

# Verificar Frontend (porta 5173)
$frontendPort = 5173
$frontendProcess = Get-NetTCPConnection -LocalPort $frontendPort -ErrorAction SilentlyContinue

if ($frontendProcess) {
    $frontendPID = $frontendProcess.OwningProcess | Select-Object -First 1
    $frontendProc = Get-Process -Id $frontendPID -ErrorAction SilentlyContinue
    Write-Host "[OK] Frontend: RODANDO" -ForegroundColor Green
    Write-Host "   Porta: $frontendPort" -ForegroundColor Gray
    Write-Host "   PID: $frontendPID" -ForegroundColor Gray
    if ($frontendProc) {
        $memoriaMB = [math]::Round($frontendProc.WorkingSet64 / 1MB, 2)
        Write-Host "   Processo: $($frontendProc.ProcessName)" -ForegroundColor Gray
        Write-Host "   Memoria: $memoriaMB MB" -ForegroundColor Gray
    }
    
    # Testar conexao
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$frontendPort" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        Write-Host "   Status Web: Respondendo" -ForegroundColor Green
    } catch {
        Write-Host "   Status Web: Nao respondeu" -ForegroundColor Yellow
    }
} else {
    Write-Host "[X] Frontend: PARADO" -ForegroundColor Red
    Write-Host "   Porta $frontendPort nao esta em uso" -ForegroundColor Gray
}

Write-Host ""
Write-Host "URLs:" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host "   Backend:  http://localhost:8001" -ForegroundColor Gray
Write-Host "   Docs:     http://localhost:8001/api/v1/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "Comandos uteis:" -ForegroundColor Cyan
Write-Host "   Iniciar:  .\start.ps1" -ForegroundColor Gray
Write-Host "   Status:   .\status.ps1" -ForegroundColor Gray
Write-Host "   Parar:    .\stop.ps1" -ForegroundColor Gray
