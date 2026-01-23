# Script para iniciar Backend e Frontend simultaneamente
# Execute: .\start.ps1

Write-Host "Iniciando Sistema Familiar..." -ForegroundColor Cyan
Write-Host ""

# Verificar status atual
$backendPort = 8001
$frontendPort = 5173

# Função para verificar se porta está realmente em uso por processo válido
function Test-PortInUse {
    param([int]$Port)
    
    # Verificar apenas estado Listen (servidor ativo), não TimeWait
    # TimeWait é normal após parar um processo e não impede iniciar um novo
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        # Verificar se há conexões em TimeWait (isso é OK, não impede iniciar)
        $timeWaitConnections = Get-NetTCPConnection -LocalPort $Port -State TimeWait -ErrorAction SilentlyContinue
        if ($timeWaitConnections) {
            Write-Host "   Porta $Port em estado TIME_WAIT (normal após parar processo)" -ForegroundColor Gray
            Write-Host "   Isso não impede iniciar o servidor - continuando..." -ForegroundColor Gray
        }
        return $false
    }
    
    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
    $hasValidProcess = $false
    
    foreach ($processId in $pids) {
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($proc) {
            $hasValidProcess = $true
            break
        }
    }
    
    if ($hasValidProcess) {
        return $true  # Processo válido encontrado
    }
    
    # Se chegou aqui, são processos zombie - limpar
    Write-Host "Limpando processos zombie na porta $Port..." -ForegroundColor Yellow
    foreach ($processId in $pids) {
        try {
            & cmd.exe /c "taskkill /F /PID $processId /T" 2>$null | Out-Null
        } catch {
            # Ignorar
        }
    }
    Start-Sleep -Milliseconds 1000
    
    # Verificar novamente após limpar
    $finalCheck = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return (-not $finalCheck)  # Retorna false se não há mais nada na porta
}

# Verificar se portas estão realmente em uso
$backendRunning = Test-PortInUse -Port $backendPort
$frontendRunning = Test-PortInUse -Port $frontendPort

if ($backendRunning) {
    Write-Host "Backend ja esta rodando na porta $backendPort" -ForegroundColor Yellow
    Write-Host "   Se houver erro ao iniciar, execute: .\limpar-porta-8001.ps1" -ForegroundColor Gray
} else {
    # Verificar se há conexões em TimeWait (isso é OK)
    $timeWait = Get-NetTCPConnection -LocalPort $backendPort -State TimeWait -ErrorAction SilentlyContinue
    if ($timeWait) {
        Write-Host "Porta $backendPort em estado TIME_WAIT (normal após parar processo)" -ForegroundColor Gray
        Write-Host "   Isso não impede iniciar o servidor - continuando..." -ForegroundColor Gray
    }
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
`$env:TZ = 'America/Sao_Paulo'
Write-Host 'Timezone configurado: America/Sao_Paulo' -ForegroundColor Cyan
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
