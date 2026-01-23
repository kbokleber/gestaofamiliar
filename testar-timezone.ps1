# Script PowerShell para testar timezone nos containers Docker
# Uso: .\testar-timezone.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Teste de Timezone - Sistema Familiar" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se Docker esta rodando
Write-Host "[1/4] Verificando se Docker esta rodando..." -ForegroundColor Yellow
$dockerRunning = docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "X Docker nao esta rodando! Inicie o Docker Desktop e tente novamente." -ForegroundColor Red
    exit 1
}
Write-Host "OK Docker esta rodando" -ForegroundColor Green
Write-Host ""

# Testar Backend
Write-Host "[2/4] Testando timezone no Backend..." -ForegroundColor Yellow
Write-Host "Comando 'date':" -ForegroundColor Gray
docker exec sistema-familiar-backend date
Write-Host ""
Write-Host "Python datetime:" -ForegroundColor Gray
docker exec sistema-familiar-backend python -c "import datetime; print('Hora atual:', datetime.datetime.now()); import time; print('Timezone:', time.tzname)"
Write-Host ""

# Testar Frontend
Write-Host "[3/4] Testando timezone no Frontend..." -ForegroundColor Yellow
Write-Host "Comando 'date':" -ForegroundColor Gray
docker exec sistema-familiar-frontend date
Write-Host ""

# Testar PostgreSQL
Write-Host "[4/4] Testando timezone no PostgreSQL..." -ForegroundColor Yellow
Write-Host "SHOW timezone:" -ForegroundColor Gray
docker exec sistema-familiar-db psql -U postgres -d sistema_familiar -c "SHOW timezone;"
Write-Host ""
Write-Host "Hora atual do PostgreSQL:" -ForegroundColor Gray
docker exec sistema-familiar-db psql -U postgres -d sistema_familiar -c "SELECT NOW();"
Write-Host ""
Write-Host "Comando 'date':" -ForegroundColor Gray
docker exec sistema-familiar-db date
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Teste Concluido!" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Resultado Esperado:" -ForegroundColor Yellow
Write-Host "   - Todos os comandos devem mostrar horario de Sao Paulo" -ForegroundColor Gray
Write-Host "   - Formato: -03 (horario padrao) ou -02 (horario de verao)" -ForegroundColor Gray
Write-Host "   - PostgreSQL timezone: America/Sao_Paulo" -ForegroundColor Gray
Write-Host ""
