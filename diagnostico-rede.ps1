# Script de Diagnóstico de Rede - Sistema Familiar
# Verifica se a conexão com o banco está usando rede interna ou internet

Write-Host "🔍 Diagnóstico de Conectividade com Banco de Dados" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Verificar se o arquivo .env existe
if (-not (Test-Path "backend\.env")) {
    Write-Host "❌ Arquivo backend\.env não encontrado!" -ForegroundColor Red
    exit 1
}

# Ler DATABASE_URL do .env
$envContent = Get-Content "backend\.env" -Raw
$dbUrlMatch = $envContent -match "DATABASE_URL=(.+)"
if (-not $dbUrlMatch) {
    Write-Host "❌ DATABASE_URL não encontrado no .env!" -ForegroundColor Red
    exit 1
}

$dbUrl = ($envContent | Select-String "DATABASE_URL=(.+)" | ForEach-Object { $_.Matches.Groups[1].Value }).Trim()

Write-Host "📋 Configuração Atual:" -ForegroundColor Yellow
Write-Host "   DATABASE_URL: $dbUrl" -ForegroundColor White
Write-Host ""

# Extrair informações da URL
if ($dbUrl -match "postgresql://[^:]+:[^@]+@([^:]+):(\d+)/(.+)") {
    $dbHost = $Matches[1]
    $dbPort = $Matches[2]
    $dbName = $Matches[3]
    
    Write-Host "📊 Informações Extraídas:" -ForegroundColor Yellow
    Write-Host "   Host: $dbHost" -ForegroundColor White
    Write-Host "   Porta: $dbPort" -ForegroundColor White
    Write-Host "   Database: $dbName" -ForegroundColor White
    Write-Host ""
    
    # Verificar se é IP público ou privado
    $isPublicIP = $false
    $isPrivateIP = $false
    $isHostname = $false
    
    if ($dbHost -match "^\d+\.\d+\.\d+\.\d+$") {
        # É um IP
        $ipParts = $dbHost -split "\."
        $firstOctet = [int]$ipParts[0]
        $secondOctet = [int]$ipParts[1]
        
        # Verificar se é IP privado
        if ($firstOctet -eq 10 -or 
            ($firstOctet -eq 172 -and $secondOctet -ge 16 -and $secondOctet -le 31) -or
            ($firstOctet -eq 192 -and $secondOctet -eq 168)) {
            $isPrivateIP = $true
            Write-Host "✅ IP PRIVADO detectado - Usando rede interna" -ForegroundColor Green
        } else {
            $isPublicIP = $true
            Write-Host "⚠️  IP PÚBLICO detectado - Saindo pela INTERNET" -ForegroundColor Red
        }
    } else {
        # É um hostname
        $isHostname = $true
        Write-Host "📝 Hostname detectado: $dbHost" -ForegroundColor Yellow
        
        # Tentar resolver o hostname
        try {
            $resolvedIP = [System.Net.Dns]::GetHostAddresses($dbHost) | Select-Object -First 1
            Write-Host "   IP Resolvido: $($resolvedIP.IPAddressToString)" -ForegroundColor White
            
            $ipParts = $resolvedIP.IPAddressToString -split "\."
            $firstOctet = [int]$ipParts[0]
            $secondOctet = [int]$ipParts[1]
            
            if ($firstOctet -eq 10 -or 
                ($firstOctet -eq 172 -and $secondOctet -ge 16 -and $secondOctet -le 31) -or
                ($firstOctet -eq 192 -and $secondOctet -eq 168)) {
                Write-Host "✅ Hostname resolve para IP PRIVADO - Usando rede interna" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Hostname resolve para IP PÚBLICO - Saindo pela INTERNET" -ForegroundColor Red
            }
        } catch {
            Write-Host "⚠️  Não foi possível resolver o hostname" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "🔬 Testando Conectividade:" -ForegroundColor Yellow
    
    # Testar conectividade básica
    $pingResult = Test-Connection -ComputerName $dbHost -Count 2 -Quiet -ErrorAction SilentlyContinue
    if ($pingResult) {
        Write-Host "   ✅ Ping bem-sucedido" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Ping falhou (pode ser normal se ICMP estiver bloqueado)" -ForegroundColor Yellow
    }
    
    # Testar porta
    Write-Host "   Testando porta $dbPort..." -ForegroundColor White
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connect = $tcpClient.BeginConnect($dbHost, $dbPort, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne(3000, $false)
        
        if ($wait) {
            $tcpClient.EndConnect($connect)
            Write-Host "   ✅ Porta $dbPort está acessível" -ForegroundColor Green
            $tcpClient.Close()
        } else {
            Write-Host "   ❌ Porta $dbPort não está acessível (timeout)" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ❌ Erro ao conectar na porta $dbPort : $_" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "⏱️  Testando Latência:" -ForegroundColor Yellow
    
    # Medir latência
    $latencies = @()
    for ($i = 1; $i -le 5; $i++) {
        try {
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
            $connect = $tcpClient.BeginConnect($dbHost, $dbPort, $null, $null)
            $wait = $connect.AsyncWaitHandle.WaitOne(5000, $false)
            $stopwatch.Stop()
            
            if ($wait) {
                $tcpClient.EndConnect($connect)
                $latency = $stopwatch.ElapsedMilliseconds
                $latencies += $latency
                Write-Host "   Teste $i : $latency ms" -ForegroundColor White
                $tcpClient.Close()
            } else {
                Write-Host "   Teste $i : Timeout" -ForegroundColor Red
            }
        } catch {
            Write-Host "   Teste $i : Erro" -ForegroundColor Red
        }
    }
    
    if ($latencies.Count -gt 0) {
        $avgLatency = ($latencies | Measure-Object -Average).Average
        $minLatency = ($latencies | Measure-Object -Minimum).Minimum
        $maxLatency = ($latencies | Measure-Object -Maximum).Maximum
        
        Write-Host ""
        Write-Host "📊 Estatísticas de Latência:" -ForegroundColor Yellow
        Write-Host "   Média: $([math]::Round($avgLatency, 2)) ms" -ForegroundColor White
        Write-Host "   Mínima: $minLatency ms" -ForegroundColor White
        Write-Host "   Máxima: $maxLatency ms" -ForegroundColor White
        Write-Host ""
        
        if ($avgLatency -lt 5) {
            Write-Host "   ✅ Latência EXCELENTE - Provavelmente rede interna" -ForegroundColor Green
        } elseif ($avgLatency -lt 50) {
            Write-Host "   ✅ Latência BOA - Pode ser rede interna ou internet rápida" -ForegroundColor Green
        } elseif ($avgLatency -lt 200) {
            Write-Host "   ⚠️  Latência MÉDIA - Pode ser internet" -ForegroundColor Yellow
        } else {
            Write-Host "   ❌ Latência ALTA - Provavelmente internet ou rede lenta" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host ""
    
    # Recomendações
    Write-Host "💡 Recomendações:" -ForegroundColor Cyan
    if ($isPublicIP -or ($isHostname -and $resolvedIP -and $resolvedIP.IPAddressToString -notmatch "^(10|172\.(1[6-9]|2[0-9]|3[01])|192\.168)")) {
        Write-Host "   1. Se o banco está no mesmo servidor/rede Docker, use o nome do container ou IP privado" -ForegroundColor Yellow
        Write-Host "   2. Verifique se existe uma rede Docker compartilhada (db_network)" -ForegroundColor Yellow
        Write-Host "   3. Use o hostname do container PostgreSQL em vez do IP público" -ForegroundColor Yellow
        Write-Host "   4. Exemplo: postgresql://postgres:senha@nome-container-postgres:5432/database" -ForegroundColor White
    } else {
        Write-Host "   ✅ Configuração parece estar usando rede interna" -ForegroundColor Green
    }
    
} else {
    Write-Host "❌ Formato de DATABASE_URL inválido!" -ForegroundColor Red
    Write-Host "   Formato esperado: postgresql://usuario:senha@host:porta/database" -ForegroundColor Yellow
}

Write-Host ""

