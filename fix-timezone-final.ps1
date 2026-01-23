# Script para corrigir definitivamente o problema de timezone
# Este script aplica a solução estrutural no banco de dados

Write-Host "`n===========================================" -ForegroundColor Cyan
Write-Host "  CORREÇÃO DEFINITIVA DE TIMEZONE" -ForegroundColor Yellow
Write-Host "===========================================`n" -ForegroundColor Cyan

# 1. Verificar se o banco está rodando
Write-Host "🔍 Verificando PostgreSQL..." -ForegroundColor Cyan
try {
    docker exec sistema-postgres psql -U sistema_user -d sistema_db -c "SELECT version();" | Out-Null
    Write-Host "✅ PostgreSQL está rodando" -ForegroundColor Green
} catch {
    Write-Host "❌ PostgreSQL não está acessível!" -ForegroundColor Red
    Write-Host "   Execute: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

# 2. Fazer backup
Write-Host "`n💾 Criando backup do banco..." -ForegroundColor Cyan
$backupFile = "backup_antes_fix_timezone_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
docker exec sistema-postgres pg_dump -U sistema_user sistema_db > $backupFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Backup criado: $backupFile" -ForegroundColor Green
} else {
    Write-Host "❌ Erro ao criar backup!" -ForegroundColor Red
    exit 1
}

# 3. Criar SQL de migração
Write-Host "`n📝 Criando script SQL..." -ForegroundColor Cyan
$sqlContent = @"
-- Remover timezone das colunas de datetime
-- Isso faz com que o PostgreSQL armazene como TIMESTAMP WITHOUT TIME ZONE

ALTER TABLE healthcare_medicalappointment 
    ALTER COLUMN appointment_date TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalappointment 
    ALTER COLUMN next_appointment TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalappointment 
    ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalappointment 
    ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;

-- Repetir para procedures
ALTER TABLE healthcare_medicalprocedure 
    ALTER COLUMN procedure_date TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalprocedure 
    ALTER COLUMN next_procedure_date TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalprocedure 
    ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalprocedure 
    ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;

-- Medications
ALTER TABLE healthcare_medication 
    ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medication 
    ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
"@

$sqlFile = "backend\migrations\remove_timezone.sql"
New-Item -ItemType Directory -Force -Path "backend\migrations" | Out-Null
$sqlContent | Out-File -FilePath $sqlFile -Encoding UTF8
Write-Host "✅ SQL criado: $sqlFile" -ForegroundColor Green

# 4. Copiar SQL para dentro do container
Write-Host "`n📦 Copiando SQL para container..." -ForegroundColor Cyan
docker cp $sqlFile sistema-postgres:/tmp/remove_timezone.sql
Write-Host "✅ SQL copiado" -ForegroundColor Green

# 5. Aplicar migration
Write-Host "`n🔧 Aplicando migration no banco..." -ForegroundColor Cyan
Write-Host "   ATENÇÃO: Isso vai alterar a estrutura do banco!" -ForegroundColor Yellow
Write-Host "   Pressione ENTER para continuar ou CTRL+C para cancelar..." -ForegroundColor Yellow
Read-Host

docker exec -it sistema-postgres psql -U sistema_user -d sistema_db -f /tmp/remove_timezone.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Migration aplicada com sucesso!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Erro ao aplicar migration!" -ForegroundColor Red
    Write-Host "   Você pode restaurar o backup:" -ForegroundColor Yellow
    Write-Host "   docker exec -i sistema-postgres psql -U sistema_user -d sistema_db < $backupFile" -ForegroundColor Gray
    exit 1
}

# 6. Modificar modelo SQLAlchemy
Write-Host "`n📝 Modificando modelo SQLAlchemy..." -ForegroundColor Cyan

# Backup do arquivo de modelo
Copy-Item "backend\app\models\healthcare.py" "backend\app\models\healthcare.py.bak"

# Substituir timezone=True por timezone=False
(Get-Content "backend\app\models\healthcare.py") -replace 'DateTime\(timezone=True\)', 'DateTime(timezone=False)' | 
    Set-Content "backend\app\models\healthcare.py"

Write-Host "✅ Modelo atualizado" -ForegroundColor Green

# 7. Reiniciar aplicação
Write-Host "`n🔄 Reiniciando aplicação..." -ForegroundColor Cyan
.\stop.ps1
Start-Sleep -Seconds 2
.\start.ps1
Start-Sleep -Seconds 10

Write-Host "`n===========================================" -ForegroundColor Green
Write-Host "  ✅ CORREÇÃO APLICADA COM SUCESSO!" -ForegroundColor Yellow
Write-Host "===========================================`n" -ForegroundColor Green

Write-Host "🎯 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host "   1. Acesse: http://localhost:5173/healthcare/appointments" -ForegroundColor White
Write-Host "   2. Atualize com CTRL+SHIFT+R" -ForegroundColor White
Write-Host "   3. Verifique se agora mostra 15:30 (correto)" -ForegroundColor White
Write-Host "   4. Crie uma NOVA consulta para validar" -ForegroundColor White

Write-Host "`n📋 BACKUP CRIADO:" -ForegroundColor Yellow
Write-Host "   $backupFile" -ForegroundColor White
Write-Host "   Guarde este arquivo em local seguro!" -ForegroundColor White

Write-Host "`n==========================================`n" -ForegroundColor Green

