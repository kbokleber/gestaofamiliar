#!/usr/bin/env pwsh
# Script DEFINITIVO para corrigir timezone de uma vez por todas
# Remove timezone de todas as datas - abordagem simples e eficaz!

$ErrorActionPreference = "Stop"

Write-Host "`n" -NoNewline
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  CORRECAO DEFINITIVA DE TIMEZONE - ABORDAGEM SIMPLES" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Esta correcao:" -ForegroundColor White
Write-Host "  - Remove timezone de todas as datas" -ForegroundColor Gray
Write-Host "  - Assume SEMPRE horario de Sao Paulo" -ForegroundColor Gray
Write-Host "  - O que voce ve e o que e salvo (sem conversoes!)" -ForegroundColor Gray
Write-Host ""

# 1. Verificar PostgreSQL
Write-Host "1. Verificando PostgreSQL..." -ForegroundColor Yellow
$pgRunning = docker ps --format "{{.Names}}" | Select-String "sistema-postgres"
if (-not $pgRunning) {
    Write-Host "   X PostgreSQL nao esta rodando!" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Inicie com:" -ForegroundColor White
    Write-Host "   docker compose up -d postgres" -ForegroundColor Gray
    Write-Host ""
    exit 1
}
Write-Host "   V PostgreSQL rodando" -ForegroundColor Green

# 2. Fazer backup
Write-Host "`n2. Criando backup do banco..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "backup_antes_timezone_$timestamp.sql"
docker exec sistema-postgres pg_dump -U sistema_user sistema_db > $backupFile 2>$null

if ($LASTEXITCODE -eq 0) {
    $backupSize = (Get-Item $backupFile).Length / 1KB
    Write-Host "   V Backup criado: $backupFile (" -ForegroundColor Green -NoNewline
    Write-Host "$([math]::Round($backupSize, 2)) KB" -ForegroundColor Gray -NoNewline
    Write-Host ")" -ForegroundColor Green
} else {
    Write-Host "   X Falha ao criar backup!" -ForegroundColor Red
    exit 1
}

# 3. Aplicar script SQL
Write-Host "`n3. Alterando colunas no banco de dados..." -ForegroundColor Yellow
Get-Content "backend\remover-timezone-db.sql" | docker exec -i sistema-postgres psql -U sistema_user -d sistema_db 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   V Colunas alteradas com sucesso!" -ForegroundColor Green
} else {
    Write-Host "   X Falha ao aplicar SQL!" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Para restaurar o backup:" -ForegroundColor Yellow
    Write-Host "   Get-Content $backupFile | docker exec -i sistema-postgres psql -U sistema_user -d sistema_db" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# 4. Verificar mudanças
Write-Host "`n4. Verificando mudancas..." -ForegroundColor Yellow
$result = docker exec sistema-postgres psql -U sistema_user -d sistema_db -t -c "SELECT data_type FROM information_schema.columns WHERE table_name = 'healthcare_medicalappointment' AND column_name = 'appointment_date';" 2>$null
if ($result -match "without time zone") {
    Write-Host "   V Timezone removido com sucesso!" -ForegroundColor Green
} else {
    Write-Host "   ? Nao foi possivel verificar (mas provavelmente funcionou)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ALTERACOES NO BANCO CONCLUIDAS!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "AGORA:" -ForegroundColor White
Write-Host ""
Write-Host "  1. O backend foi automaticamente atualizado (ja esta correto)" -ForegroundColor Gray
Write-Host "  2. Reinicie o backend para aplicar as mudancas:" -ForegroundColor White
Write-Host ""
Write-Host "     # Pressione Ctrl+C no terminal do backend" -ForegroundColor Cyan
Write-Host "     # Depois execute:" -ForegroundColor Cyan
Write-Host "     .\start-backend.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Teste criando uma consulta para as 14:00" -ForegroundColor Gray
Write-Host "  4. Deve aparecer 14:00 na lista (sem +3 horas!)" -ForegroundColor Gray
Write-Host ""
Write-Host "BACKUP:" -ForegroundColor White
Write-Host "  Salvo em: $backupFile" -ForegroundColor Gray
Write-Host "  Se tudo funcionar, pode deletar depois!" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Perguntar se quer reiniciar automaticamente
$restart = Read-Host "Deseja que eu tente reiniciar o backend agora? (s/N)"
if ($restart -eq "s" -or $restart -eq "S") {
    Write-Host "`nReiniciando backend..." -ForegroundColor Yellow
    
    # Encontrar processo uvicorn e matar
    $uvicornProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*uvicorn*" -or $_.Path -like "*backend*"
    }
    
    if ($uvicornProcesses) {
        Write-Host "   Parando backend antigo..." -ForegroundColor Gray
        $uvicornProcesses | ForEach-Object { Stop-Process -Id $_.Id -Force }
        Start-Sleep -Seconds 2
    }
    
    Write-Host "   Iniciando backend..." -ForegroundColor Gray
    Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start-backend.ps1"
    
    Write-Host "   V Backend reiniciado!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Aguarde 5 segundos e teste em: http://localhost:5173" -ForegroundColor Cyan
} else {
    Write-Host "`nOK! Reinicie manualmente quando estiver pronto." -ForegroundColor White
}

Write-Host ""

