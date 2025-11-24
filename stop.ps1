# Script para parar Backend e Frontend
# Execute: .\stop.ps1

Write-Host "Parando servicos..." -ForegroundColor Yellow
Write-Host ""

# Parar processos na porta 8001 (Backend)
$backendPort = 8001
$backendStopped = $false

try {
    $backendConnections = Get-NetTCPConnection -LocalPort $backendPort -State Listen,Established -ErrorAction SilentlyContinue
    if ($backendConnections) {
        $backendPIDs = $backendConnections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
        foreach ($processId in $backendPIDs) {
            $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "Parando Backend (PID: $processId, Processo: $($proc.ProcessName))..." -ForegroundColor Yellow
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                $backendStopped = $true
            }
        }
    }
} catch {
    # Ignorar erros
}

# Também tentar parar processos Python que podem estar rodando uvicorn
try {
    $pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*app.main*"
    }
    foreach ($proc in $pythonProcesses) {
        Write-Host "Parando processo Python (PID: $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        $backendStopped = $true
    }
} catch {
    # Ignorar erros
}

if ($backendStopped) {
    Write-Host "Backend parado" -ForegroundColor Green
} else {
    Write-Host "Backend ja esta parado" -ForegroundColor Gray
}

Write-Host ""

# Parar processos na porta 5173 (Frontend)
$frontendPort = 5173
$frontendStopped = $false

try {
    $frontendConnections = Get-NetTCPConnection -LocalPort $frontendPort -State Listen,Established -ErrorAction SilentlyContinue
    if ($frontendConnections) {
        $frontendPIDs = $frontendConnections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
        foreach ($processId in $frontendPIDs) {
            $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "Parando Frontend (PID: $processId, Processo: $($proc.ProcessName))..." -ForegroundColor Yellow
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                $frontendStopped = $true
            }
        }
    }
} catch {
    # Ignorar erros
}

# Também tentar parar processos Node que podem estar rodando vite
try {
    $nodeProcesses = Get-Process node -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -like "*node*" -and (Get-NetTCPConnection -OwningProcess $_.Id -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq 5173 })
    }
    foreach ($proc in $nodeProcesses) {
        Write-Host "Parando processo Node (PID: $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        $frontendStopped = $true
    }
} catch {
    # Ignorar erros
}

if ($frontendStopped) {
    Write-Host "Frontend parado" -ForegroundColor Green
} else {
    Write-Host "Frontend ja esta parado" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Aguardando processos finalizarem..." -ForegroundColor Gray
Start-Sleep -Seconds 2
Write-Host ""
Write-Host "Todos os servicos foram parados" -ForegroundColor Green
