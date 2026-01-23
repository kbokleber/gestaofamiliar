# Script para testar timezone em ambiente de desenvolvimento (sem Docker)
# Uso: .\testar-timezone-dev.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Teste de Timezone - Desenvolvimento (Sem Docker)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar timezone do Windows
Write-Host "[1/3] Timezone do Windows:" -ForegroundColor Yellow
Get-TimeZone | Format-List Id, DisplayName, StandardName
Write-Host ""

# 2. Testar Python (se backend estiver rodando)
Write-Host "[2/3] Testando Python/Backend..." -ForegroundColor Yellow
$backendPort = 8001
$backendRunning = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue

if ($backendRunning) {
    Write-Host "Backend esta rodando. Testando timezone..." -ForegroundColor Green
    
    # Criar script Python temporario
    $pythonTest = @"
import os
import datetime
import time

print('Variavel TZ:', os.environ.get('TZ', 'NAO DEFINIDA'))
print('Hora atual (datetime.now()):', datetime.datetime.now())
print('Hora atual UTC:', datetime.datetime.now(datetime.timezone.utc))
print('Timezone do sistema:', time.tzname)
"@
    
    $tempFile = [System.IO.Path]::GetTempFileName()
    $pythonFile = $tempFile + ".py"
    Move-Item $tempFile $pythonFile -Force
    $pythonTest | Out-File -FilePath $pythonFile -Encoding UTF8
    
    # Executar dentro do venv do backend
    try {
        Push-Location backend
        & .\venv\Scripts\python.exe $pythonFile
        Pop-Location
    } catch {
        Write-Host "Erro ao executar teste Python: $($_.Exception.Message)" -ForegroundColor Red
    } finally {
        Remove-Item $pythonFile -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Backend nao esta rodando. Inicie com .\start.ps1 primeiro." -ForegroundColor Yellow
}
Write-Host ""

# 3. Verificar PostgreSQL (se estiver rodando localmente)
Write-Host "[3/3] Verificando PostgreSQL local..." -ForegroundColor Yellow
$pgPort = 5432
$pgRunning = Get-NetTCPConnection -LocalPort $pgPort -State Listen -ErrorAction SilentlyContinue

if ($pgRunning) {
    Write-Host "PostgreSQL local detectado na porta 5432" -ForegroundColor Green
    Write-Host "Para verificar timezone do PostgreSQL, execute:" -ForegroundColor Cyan
    Write-Host "  psql -U postgres -c 'SHOW timezone;'" -ForegroundColor Gray
    Write-Host "  psql -U postgres -c 'SELECT NOW();'" -ForegroundColor Gray
} else {
    Write-Host "PostgreSQL local nao detectado (pode estar em outro servidor)" -ForegroundColor Gray
}
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Teste Concluido!" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Resultado Esperado:" -ForegroundColor Yellow
Write-Host "  - TZ deve estar definida como 'America/Sao_Paulo'" -ForegroundColor Gray
Write-Host "  - Hora deve estar no timezone de Sao Paulo (UTC-3)" -ForegroundColor Gray
Write-Host ""
Write-Host "Se TZ estiver 'NAO DEFINIDA':" -ForegroundColor Yellow
Write-Host "  1. Pare o backend: .\stop.ps1" -ForegroundColor Gray
Write-Host "  2. Inicie novamente: .\start.ps1" -ForegroundColor Gray
Write-Host ""

