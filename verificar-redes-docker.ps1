# Script para verificar redes Docker e identificar o hostname do banco

Write-Host "🐳 Verificando Redes Docker e Containers PostgreSQL" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Verificar se Docker está rodando
try {
    $dockerVersion = docker version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker não está rodando ou não está instalado!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Docker não está disponível!" -ForegroundColor Red
    exit 1
}

Write-Host "📋 Redes Docker Disponíveis:" -ForegroundColor Yellow
Write-Host ""
docker network ls
Write-Host ""

# Procurar containers PostgreSQL
Write-Host "🔍 Procurando containers PostgreSQL:" -ForegroundColor Yellow
Write-Host ""

$postgresContainers = docker ps -a --filter "ancestor=postgres" --format "{{.Names}}\t{{.Image}}\t{{.Status}}"
if ($postgresContainers) {
    Write-Host $postgresContainers -ForegroundColor White
    Write-Host ""
    
    # Listar detalhes de cada container
    $containerNames = docker ps -a --filter "ancestor=postgres" --format "{{.Names}}"
    foreach ($containerName in $containerNames) {
        Write-Host "📦 Container: $containerName" -ForegroundColor Cyan
        Write-Host "   Redes conectadas:" -ForegroundColor Yellow
        
        $networks = docker inspect $containerName --format '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' 2>$null
        if ($networks) {
            foreach ($network in $networks.Trim() -split '\s+') {
                if ($network) {
                    Write-Host "      - $network" -ForegroundColor White
                    
                    # Obter IP do container na rede
                    $ip = docker inspect $containerName --format "{{range .NetworkSettings.Networks}}{{if eq .NetworkID (index (docker network ls -q --filter name=$network) 0)}}{{.IPAddress}}{{end}}{{end}}" 2>$null
                    if ($ip) {
                        Write-Host "        IP: $ip" -ForegroundColor Gray
                    }
                }
            }
        }
        
        # Obter todas as informações de rede
        Write-Host "   Informações completas:" -ForegroundColor Yellow
        $networkInfo = docker inspect $containerName --format '{{json .NetworkSettings.Networks}}' 2>$null | ConvertFrom-Json
        if ($networkInfo) {
            $networkInfo.PSObject.Properties | ForEach-Object {
                $netName = $_.Name
                $netData = $_.Value
                Write-Host "      Rede: $netName" -ForegroundColor White
                Write-Host "        IP: $($netData.IPAddress)" -ForegroundColor Gray
                Write-Host "        Gateway: $($netData.Gateway)" -ForegroundColor Gray
            }
        }
        
        Write-Host ""
    }
} else {
    Write-Host "⚠️  Nenhum container PostgreSQL encontrado" -ForegroundColor Yellow
    Write-Host ""
}

# Verificar rede db_network especificamente
Write-Host "🔍 Verificando rede 'db_network':" -ForegroundColor Yellow
$dbNetwork = docker network inspect db_network 2>$null
if ($dbNetwork) {
    Write-Host "   ✅ Rede db_network encontrada" -ForegroundColor Green
    $dbNetworkJson = $dbNetwork | ConvertFrom-Json
    if ($dbNetworkJson) {
        Write-Host "   Containers conectados:" -ForegroundColor Yellow
        $dbNetworkJson[0].Containers.PSObject.Properties | ForEach-Object {
            $containerId = $_.Name
            $containerData = $_.Value
            $containerName = docker inspect $containerId --format "{{.Name}}" 2>$null
            Write-Host "      - $containerName (IP: $($containerData.IPv4Address))" -ForegroundColor White
        }
    }
} else {
    Write-Host "   ⚠️  Rede db_network não encontrada" -ForegroundColor Yellow
    Write-Host "   Para criar: docker network create db_network" -ForegroundColor Gray
}
Write-Host ""

# Verificar se há containers do sistema familiar
Write-Host "🔍 Procurando containers do Sistema Familiar:" -ForegroundColor Yellow
$sistemaContainers = docker ps -a --filter "name=sistema-familiar" --format "{{.Names}}\t{{.Image}}\t{{.Status}}"
if ($sistemaContainers) {
    Write-Host $sistemaContainers -ForegroundColor White
} else {
    Write-Host "   Nenhum container do sistema encontrado" -ForegroundColor Gray
}
Write-Host ""

Write-Host "💡 Dica: Use o nome do container PostgreSQL como hostname na DATABASE_URL" -ForegroundColor Cyan
Write-Host "   Exemplo: postgresql://postgres:senha@nome-container:5432/database" -ForegroundColor White
Write-Host ""

