# Script para verificar status do Backend e Frontend
# Execute: .\status.ps1

Write-Host "Verificando status dos servicos..." -ForegroundColor Cyan
Write-Host ""

# Verificar Backend (porta 8001)
$backendPort = 8001
$backendConnections = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue

if ($backendConnections) {
    $backendPID = $backendConnections.OwningProcess | Select-Object -First 1 -Unique
    # Filtrar PID 0 (Idle) e PIDs inválidos
    if ($backendPID -and $backendPID -gt 0) {
        $backendProc = Get-Process -Id $backendPID -ErrorAction SilentlyContinue
        if ($backendProc) {
            Write-Host "[OK] Backend: RODANDO" -ForegroundColor Green
            Write-Host "   Porta: $backendPort" -ForegroundColor Gray
            Write-Host "   PID: $backendPID" -ForegroundColor Gray
            $memoriaMB = [math]::Round($backendProc.WorkingSet64 / 1MB, 2)
            Write-Host "   Processo: $($backendProc.ProcessName)" -ForegroundColor Gray
            Write-Host "   Memoria: $memoriaMB MB" -ForegroundColor Gray
            
            # Testar conexao
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$backendPort/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
                Write-Host "   Status API: Respondendo" -ForegroundColor Green
            } catch {
                Write-Host "   Status API: Nao respondeu" -ForegroundColor Yellow
            }
        } else {
            Write-Host "[?] Backend: PORTA EM USO MAS PROCESSO NAO ENCONTRADO" -ForegroundColor Yellow
            Write-Host "   Porta $backendPort esta em uso (PID: $backendPID) mas processo nao existe" -ForegroundColor Gray
            Write-Host "   Pode ser que o processo foi finalizado mas a porta ainda nao foi liberada" -ForegroundColor Gray
            Write-Host "   Aguarde alguns segundos e execute status.ps1 novamente" -ForegroundColor Gray
        }
    } else {
        Write-Host "[X] Backend: PARADO" -ForegroundColor Red
        Write-Host "   Porta $backendPort nao esta em uso (ou apenas em estado TIME_WAIT)" -ForegroundColor Gray
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
