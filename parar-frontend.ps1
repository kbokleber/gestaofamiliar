# Script para parar frontend na porta 5173
Write-Host "Parando Frontend na porta 5173..." -ForegroundColor Yellow

$port = 5173
$connections = Get-NetTCPConnection -LocalPort $port -State Listen,Established -ErrorAction SilentlyContinue

if ($connections) {
    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
    foreach ($processId in $pids) {
        Write-Host "  Parando processo (PID: $processId)..." -ForegroundColor Yellow
        try {
            $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($proc) {
                $proc.Kill()
            } else {
                & cmd.exe /c "taskkill /F /PID $processId /T" 2>$null
            }
        } catch {
            & cmd.exe /c "taskkill /F /PID $processId /T" 2>$null
        }
    }
    Start-Sleep -Milliseconds 500
    
    # Parar processos Node relacionados
    $nodeProcs = Get-Process node -ErrorAction SilentlyContinue
    foreach ($nodeProc in $nodeProcs) {
        $nodeConn = Get-NetTCPConnection -OwningProcess $nodeProc.Id -ErrorAction SilentlyContinue
        if ($nodeConn | Where-Object { $_.LocalPort -eq $port }) {
            Write-Host "  Parando processo Node (PID: $($nodeProc.Id))..." -ForegroundColor Yellow
            try {
                $nodeProc.Kill()
            } catch {
                & cmd.exe /c "taskkill /F /PID $($nodeProc.Id) /T" 2>$null
            }
        }
    }
    
    Start-Sleep -Milliseconds 500
    $check = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $check) {
        Write-Host "Frontend parado!" -ForegroundColor Green
    } else {
        Write-Host "Aviso: Frontend ainda pode estar rodando" -ForegroundColor Yellow
    }
} else {
    Write-Host "Frontend ja esta parado" -ForegroundColor Green
}

