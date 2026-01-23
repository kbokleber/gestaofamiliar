# Script PowerShell para aplicar mudancas de timezone
# Uso: .\aplicar-timezone.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Aplicar Configuracao de Timezone" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se Docker esta rodando
Write-Host "[1/5] Verificando Docker..." -ForegroundColor Yellow
$dockerRunning = docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "X Docker nao esta rodando! Inicie o Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "OK Docker esta rodando" -ForegroundColor Green
Write-Host ""

# Confirmar acao
Write-Host "[2/5] ATENCAO: Este script ira:" -ForegroundColor Yellow
Write-Host "   - Parar todos os containers" -ForegroundColor Gray
Write-Host "   - Reconstruir as imagens com novo timezone" -ForegroundColor Gray
Write-Host "   - Iniciar os containers novamente" -ForegroundColor Gray
Write-Host ""
$confirmar = Read-Host "Deseja continuar? (S/N)"
if ($confirmar -ne "S" -and $confirmar -ne "s") {
    Write-Host "X Operacao cancelada pelo usuario" -ForegroundColor Red
    exit 0
}
Write-Host ""

# Parar containers
Write-Host "[3/5] Parando containers..." -ForegroundColor Yellow
docker-compose down
if ($LASTEXITCODE -ne 0) {
    Write-Host "Aviso: Erro ao parar containers (pode ser normal se ja estiverem parados)" -ForegroundColor Yellow
}
Write-Host "OK Containers parados" -ForegroundColor Green
Write-Host ""

# Rebuild e iniciar
Write-Host "[4/5] Reconstruindo e iniciando containers..." -ForegroundColor Yellow
Write-Host "   (Isso pode levar alguns minutos...)" -ForegroundColor Gray
docker-compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "X Erro ao reconstruir/iniciar containers!" -ForegroundColor Red
    exit 1
}
Write-Host "OK Containers reconstruidos e iniciados" -ForegroundColor Green
Write-Host ""

# Aguardar containers iniciarem
Write-Host "[5/5] Aguardando containers iniciarem (20 segundos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 20
Write-Host "OK Pronto!" -ForegroundColor Green
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Configuracao Aplicada com Sucesso!" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proximos Passos:" -ForegroundColor Yellow
Write-Host "   1. Execute: .\testar-timezone.ps1" -ForegroundColor Gray
Write-Host "   2. Verifique se o timezone esta correto" -ForegroundColor Gray
Write-Host "   3. Teste a aplicacao no navegador" -ForegroundColor Gray
Write-Host ""
