# Script para parar Backend e Frontend
# Execute: .\stop.ps1

Write-Host "Parando servicos..." -ForegroundColor Yellow
Write-Host ""

# Parar processos na porta 8001 (Backend)
$backendPort = 8001
$backendStopped = $false

# Função auxiliar para parar processo de forma agressiva
function Stop-ProcessAggressively {
    param([int]$ProcessId)
    
    try {
        $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if (-not $proc) {
            return $true  # Processo já não existe
        }
        
        $procName = $proc.ProcessName
        Write-Host "   Tentando parar processo (PID: $ProcessId, Nome: $procName)..." -ForegroundColor Yellow
        
        # Método 1: Kill direto
        try {
            $proc.Kill()
            Start-Sleep -Milliseconds 500
        } catch {
            Write-Host "     Método 1 (Kill) falhou, tentando próximo..." -ForegroundColor Gray
        }
        
        # Verificar se parou
        $stillExists = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if (-not $stillExists) {
            return $true
        }
        
        # Método 2: Stop-Process com Force
        try {
            Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        } catch {
            Write-Host "     Método 2 (Stop-Process) falhou, tentando próximo..." -ForegroundColor Gray
        }
        
        # Verificar se parou
        $stillExists = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if (-not $stillExists) {
            return $true
        }
        
        # Método 3: Taskkill via cmd (mais agressivo)
        try {
            $result = & cmd.exe /c "taskkill /F /PID $ProcessId /T" 2>&1
            Start-Sleep -Milliseconds 500
        } catch {
            Write-Host "     Método 3 (taskkill) falhou" -ForegroundColor Gray
        }
        
        # Verificar se parou
        $stillExists = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if (-not $stillExists) {
            return $true
        }
        
        # Método 4: Se for Python, tentar parar todos os processos Python relacionados
        if ($procName -like "python*") {
            Write-Host "     Processo Python detectado, tentando parar processos relacionados..." -ForegroundColor Yellow
            try {
                # Obter linha de comando para identificar processos relacionados
                $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
                if ($processInfo) {
                    $commandLine = $processInfo.CommandLine
                    if ($commandLine -like "*uvicorn*" -or $commandLine -like "*app.main*") {
                        # Parar todos os processos Python que podem estar relacionados
                        $allPython = Get-Process python* -ErrorAction SilentlyContinue
                        foreach ($pyProc in $allPython) {
                            if ($pyProc.Id -ne $ProcessId) {
                                try {
                                    $pyProc.Kill()
                                } catch {
                                    # Ignorar
                                }
                            }
                        }
                        Start-Sleep -Milliseconds 500
                    }
                }
            } catch {
                # Ignorar
            }
        }
        
        # Verificação final
        $stillExists = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($stillExists) {
            Write-Host "     Processo ainda existe após todas as tentativas" -ForegroundColor Red
            return $false
        }
        return $true
    } catch {
        return $false
    }
}

try {
    # Buscar apenas conexões em estado Listen (servidor ativo)
    $backendConnections = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
    if ($backendConnections) {
        $backendPIDs = $backendConnections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
        foreach ($processId in $backendPIDs) {
            Write-Host "Parando Backend na porta $backendPort (PID: $processId)..." -ForegroundColor Yellow
            
            # Tentar obter processo
            $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($proc) {
                # Processo normal, usar função auxiliar
                if (Stop-ProcessAggressively -ProcessId $processId) {
                    $backendStopped = $true
                }
            } else {
                # Processo zombie (existe na porta mas não aparece no Get-Process)
                Write-Host "   Processo zombie detectado, usando taskkill direto..." -ForegroundColor Yellow
                try {
                    & cmd.exe /c "taskkill /F /PID $processId /T" 2>$null | Out-Null
                    Start-Sleep -Milliseconds 1000
                    $check = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
                    if (-not $check) {
                        Write-Host "   Processo zombie parado!" -ForegroundColor Green
                        $backendStopped = $true
                    }
                } catch {
                    # Ignorar
                }
            }
        }
    }
} catch {
    # Ignorar erros
}

# Também tentar parar processos Python que podem estar rodando uvicorn
try {
    # Buscar processos Python usando CIM para obter CommandLine
    $allPythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
    foreach ($proc in $allPythonProcesses) {
        try {
            $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue
            if ($processInfo) {
                $commandLine = $processInfo.CommandLine
                if ($commandLine -and ($commandLine -like "*uvicorn*" -or $commandLine -like "*app.main*")) {
                    Write-Host "Parando processo Python uvicorn (PID: $($proc.Id))..." -ForegroundColor Yellow
                    if (Stop-ProcessAggressively -ProcessId $proc.Id) {
                        $backendStopped = $true
                    }
                }
            }
        } catch {
            # Se não conseguir obter CommandLine, verificar se está na porta 8001
            try {
                $procConnections = Get-NetTCPConnection -OwningProcess $proc.Id -ErrorAction SilentlyContinue
                if ($procConnections) {
                    $hasBackendPort = $procConnections | Where-Object { $_.LocalPort -eq $backendPort }
                    if ($hasBackendPort) {
                        Write-Host "Parando processo Python na porta $backendPort (PID: $($proc.Id))..." -ForegroundColor Yellow
                        if (Stop-ProcessAggressively -ProcessId $proc.Id) {
                            $backendStopped = $true
                        }
                    }
                }
            } catch {
                # Ignorar erros individuais
            }
        }
    }
} catch {
    # Ignorar erros
}

# Verificação final: se ainda houver algo na porta 8001, tentar parar novamente de forma mais agressiva
Start-Sleep -Milliseconds 1000
try {
    # Verificar apenas estado Listen (servidor ativo), não Established (conexões)
    $stillRunning = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
    if ($stillRunning) {
        Write-Host "Ainda ha processos na porta $backendPort, tentando parar novamente..." -ForegroundColor Yellow
        $remainingPIDs = $stillRunning | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
        foreach ($processId in $remainingPIDs) {
            Write-Host "Forcando parada do processo Backend (PID: $processId)..." -ForegroundColor Yellow
            if (Stop-ProcessAggressively -ProcessId $processId) {
                $backendStopped = $true
            } else {
                # Tentar parar o processo pai se existir
                try {
                    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
                    if ($processInfo) {
                        $parentProc = $processInfo.ParentProcessId
                        if ($parentProc) {
                            $parent = Get-Process -Id $parentProc -ErrorAction SilentlyContinue
                            if ($parent) {
                                Write-Host "   Processo pai encontrado (PID: $parentProc, Nome: $($parent.ProcessName))" -ForegroundColor Yellow
                                Write-Host "   Tentando parar processo pai..." -ForegroundColor Yellow
                                
                                # Parar processo pai de forma agressiva
                                try {
                                    $parent.Kill()
                                    Start-Sleep -Milliseconds 500
                                } catch {
                                    try {
                                        Stop-Process -Id $parentProc -Force -ErrorAction SilentlyContinue
                                        Start-Sleep -Milliseconds 500
                                    } catch {
                                        & cmd.exe /c "taskkill /F /PID $parentProc /T" 2>$null
                                        Start-Sleep -Milliseconds 500
                                    }
                                }
                                
                                # Verificar se o processo filho foi parado
                                $childStillExists = Get-Process -Id $processId -ErrorAction SilentlyContinue
                                if (-not $childStillExists) {
                                    Write-Host "   Processo filho parado apos parar processo pai" -ForegroundColor Green
                                    $backendStopped = $true
                                } else {
                                    Write-Host "   Processo filho ainda existe" -ForegroundColor Red
                                }
                            }
                        }
                    }
                } catch {
                    # Ignorar
                }
                
                # Última tentativa: usar taskkill com /T (tree) para parar processo e filhos
                if (-not $backendStopped) {
                    Write-Host "   Tentando ultimo metodo: taskkill com arvore de processos..." -ForegroundColor Yellow
                    try {
                        & cmd.exe /c "taskkill /F /PID $processId /T" 2>$null | Out-Null
                        Start-Sleep -Milliseconds 1000
                        $finalCheck = Get-Process -Id $processId -ErrorAction SilentlyContinue
                        if (-not $finalCheck) {
                            Write-Host "   Processo parado com taskkill /T" -ForegroundColor Green
                            $backendStopped = $true
                        }
                    } catch {
                        # Ignorar
                    }
                }
            }
        }
    }
} catch {
    # Ignorar
}

if ($backendStopped) {
    # Verificar se realmente parou (apenas estado Listen)
    Start-Sleep -Milliseconds 800
    $checkPort = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
    if (-not $checkPort) {
        Write-Host "Backend parado" -ForegroundColor Green
    } else {
        $remainingPID = $checkPort.OwningProcess | Select-Object -First 1 -Unique
        if ($remainingPID -and $remainingPID -gt 0) {
            Write-Host "Backend ainda rodando (PID: $remainingPID)" -ForegroundColor Yellow
            Write-Host "   Tente fechar manualmente a janela do PowerShell que iniciou o backend" -ForegroundColor Gray
            Write-Host "   Ou execute: Get-Process -Id $remainingPID | Stop-Process -Force" -ForegroundColor Cyan
        } else {
            Write-Host "Backend parado (porta pode estar em estado TIME_WAIT)" -ForegroundColor Yellow
            Write-Host "   Aguarde alguns segundos e execute status.ps1 novamente" -ForegroundColor Gray
        }
    }
} else {
    # Verificar se realmente não há nada rodando (apenas estado Listen)
    $checkPort = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
    if (-not $checkPort) {
        Write-Host "Backend ja esta parado" -ForegroundColor Gray
    } else {
        $remainingPID = $checkPort.OwningProcess | Select-Object -First 1 -Unique
        if ($remainingPID -and $remainingPID -gt 0) {
            Write-Host "Aviso: Processo ainda rodando na porta $backendPort (PID: $remainingPID)" -ForegroundColor Yellow
            Write-Host "   Tente fechar manualmente as janelas do PowerShell que iniciaram o backend" -ForegroundColor Gray
            Write-Host "   Ou execute: Get-Process -Id $remainingPID | Stop-Process -Force" -ForegroundColor Cyan
        } else {
            Write-Host "Backend ja esta parado (porta pode estar em estado TIME_WAIT)" -ForegroundColor Gray
        }
    }
}

Write-Host ""

# Parar processos na porta 5173 (Frontend)
$frontendPort = 5173
$frontendStopped = $false

# Primeiro: parar processos que estão usando a porta 5173
try {
    $frontendConnections = Get-NetTCPConnection -LocalPort $frontendPort -State Listen,Established -ErrorAction SilentlyContinue
    if ($frontendConnections) {
        $frontendPIDs = $frontendConnections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
        foreach ($processId in $frontendPIDs) {
            Write-Host "Parando Frontend na porta $frontendPort (PID: $processId)..." -ForegroundColor Yellow
            
            # Tentar obter processo
            $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($proc) {
                # Processo normal
                Write-Host "   Processo: $($proc.ProcessName)" -ForegroundColor Gray
                try {
                    $proc.Kill()
                } catch {
                    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                }
                $frontendStopped = $true
                Start-Sleep -Milliseconds 300
            } else {
                # Processo zombie (existe na porta mas não aparece no Get-Process)
                Write-Host "   Processo zombie detectado, usando taskkill direto..." -ForegroundColor Yellow
                try {
                    & cmd.exe /c "taskkill /F /PID $processId /T" 2>$null | Out-Null
                    Start-Sleep -Milliseconds 500
                    $check = Get-NetTCPConnection -LocalPort $frontendPort -State Listen -ErrorAction SilentlyContinue
                    if (-not $check) {
                        Write-Host "   Processo zombie parado!" -ForegroundColor Green
                        $frontendStopped = $true
                    }
                } catch {
                    # Ignorar
                }
            }
        }
    }
} catch {
    $errorMsg = $_.Exception.Message
    Write-Host ("Erro ao verificar porta " + $frontendPort + ": " + $errorMsg) -ForegroundColor Red
}

# Segundo: parar processos Node que podem estar rodando vite
try {
    $allNodeProcesses = Get-Process node -ErrorAction SilentlyContinue
    foreach ($proc in $allNodeProcesses) {
        try {
            # Verificar se o processo está usando a porta 5173
            $procConnections = Get-NetTCPConnection -OwningProcess $proc.Id -ErrorAction SilentlyContinue
            $usingFrontendPort = $procConnections | Where-Object { $_.LocalPort -eq $frontendPort }
            
            if ($usingFrontendPort) {
                Write-Host "Parando processo Node na porta $frontendPort (PID: $($proc.Id))..." -ForegroundColor Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                $frontendStopped = $true
            } else {
                # Verificar linha de comando para processos vite
                $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue
                if ($processInfo) {
                    $commandLine = $processInfo.CommandLine
                    if ($commandLine -and ($commandLine -like "*vite*" -or $commandLine -like "*npm*run*dev*")) {
                        Write-Host "Parando processo Node Vite (PID: $($proc.Id))..." -ForegroundColor Yellow
                        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                        $frontendStopped = $true
                    }
                }
            }
        } catch {
            # Se falhar, tentar parar o processo Node de qualquer forma se estiver na porta
            try {
                $procConnections = Get-NetTCPConnection -OwningProcess $proc.Id -ErrorAction SilentlyContinue
                if ($procConnections) {
                    $hasPort = $procConnections | Where-Object { $_.LocalPort -eq $frontendPort }
                    if ($hasPort) {
                        Write-Host "Parando processo Node (PID: $($proc.Id))..." -ForegroundColor Yellow
                        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                        $frontendStopped = $true
                    }
                }
            } catch {
                # Ignorar erros individuais
            }
        }
    }
} catch {
    $errorMsg = $_.Exception.Message
    Write-Host ("Erro ao verificar processos Node: " + $errorMsg) -ForegroundColor Red
}

# Verificação final: se ainda houver algo na porta 5173, tentar parar novamente
Start-Sleep -Milliseconds 500
try {
    $stillRunning = Get-NetTCPConnection -LocalPort $frontendPort -State Listen,Established -ErrorAction SilentlyContinue
    if ($stillRunning) {
        Write-Host "Ainda ha processos na porta $frontendPort, tentando parar novamente..." -ForegroundColor Yellow
        $remainingPIDs = $stillRunning | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
        foreach ($processId in $remainingPIDs) {
            try {
                $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "Forcando parada do processo (PID: $processId)..." -ForegroundColor Yellow
                    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                    $frontendStopped = $true
                }
            } catch {
                # Ignorar
            }
        }
    }
} catch {
    # Ignorar
}

if ($frontendStopped) {
    Write-Host "Frontend parado" -ForegroundColor Green
} else {
    # Verificar se realmente não há nada rodando
    $checkPort = Get-NetTCPConnection -LocalPort $frontendPort -ErrorAction SilentlyContinue
    if (-not $checkPort) {
        Write-Host "Frontend ja esta parado" -ForegroundColor Gray
    } else {
        Write-Host "Aviso: Pode haver processos ainda rodando na porta $frontendPort" -ForegroundColor Yellow
        Write-Host "   Tente fechar manualmente as janelas do PowerShell ou reinicie o terminal" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Aguardando processos finalizarem..." -ForegroundColor Gray
Start-Sleep -Seconds 2
Write-Host ""
Write-Host "Todos os servicos foram parados" -ForegroundColor Green
