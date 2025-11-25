#!/bin/bash

# Script para testar conectividade entre NPM e Backend
# Uso: ./testar-conectividade-npm.sh

echo "🔍 TESTANDO CONECTIVIDADE NPM ↔ BACKEND"
echo "========================================"
echo ""

# 1. Verificar nome exato do serviço
echo "1️⃣ Nome do serviço backend:"
SERVICE_NAME=$(docker service ls | grep backend | awk '{print $2}')
echo "   $SERVICE_NAME"
echo ""

# 2. Verificar IP do backend na rede nginx_public
echo "2️⃣ IP do backend na rede nginx_public:"
BACKEND_IP=$(docker service inspect sistema-familiar_backend 2>/dev/null | grep -A 10 "Networks" | grep -A 5 "nginx_public" | grep "IPv4Address" | head -1 | awk -F'"' '{print $4}' | awk -F'/' '{print $1}')
if [ -n "$BACKEND_IP" ]; then
    echo "   IP: $BACKEND_IP"
else
    echo "   ⚠️  Não foi possível obter IP diretamente"
    echo "   Verificando containers na rede..."
    docker network inspect nginx_public 2>/dev/null | grep -A 10 "sistema-familiar" | head -10
fi
echo ""

# 3. Encontrar container do NPM
echo "3️⃣ Container do NPM:"
NPM_CONTAINER=$(docker ps -q -f name=nginx-proxy-manager)
if [ -z "$NPM_CONTAINER" ]; then
    NPM_CONTAINER=$(docker ps | grep nginx | grep proxy | awk '{print $1}' | head -1)
fi

if [ -n "$NPM_CONTAINER" ]; then
    echo "   Container ID: $NPM_CONTAINER"
    echo "   Nome: $(docker ps --format '{{.Names}}' -f id=$NPM_CONTAINER)"
else
    echo "   ❌ Container do NPM não encontrado!"
    echo "   Containers nginx rodando:"
    docker ps | grep nginx
    exit 1
fi
echo ""

# 4. Testar diferentes formas de conexão
echo "4️⃣ Testando conectividade:"
echo ""

echo "   a) Por nome do serviço (sistema-familiar_backend):"
docker exec $NPM_CONTAINER wget -O- http://sistema-familiar_backend:8001/health --timeout=5 2>&1 | head -3
echo ""

echo "   b) Por nome curto (backend):"
docker exec $NPM_CONTAINER wget -O- http://backend:8001/health --timeout=5 2>&1 | head -3
echo ""

if [ -n "$BACKEND_IP" ]; then
    echo "   c) Por IP direto ($BACKEND_IP):"
    docker exec $NPM_CONTAINER wget -O- http://$BACKEND_IP:8001/health --timeout=5 2>&1 | head -3
    echo ""
fi

# 5. Verificar configuração do NPM
echo "5️⃣ Verificando se NPM está na mesma rede:"
NPM_NETWORKS=$(docker inspect $NPM_CONTAINER 2>/dev/null | grep -A 10 "Networks" | grep nginx_public)
if [ -n "$NPM_NETWORKS" ]; then
    echo "   ✅ NPM está na rede nginx_public"
else
    echo "   ❌ NPM NÃO está na rede nginx_public!"
    echo "   Redes do NPM:"
    docker inspect $NPM_CONTAINER 2>/dev/null | grep -A 10 "Networks" | grep -E "NetworkMode|Networks"
fi
echo ""

# 6. Verificar DNS
echo "6️⃣ Testando resolução DNS:"
docker exec $NPM_CONTAINER nslookup sistema-familiar_backend 2>&1 | head -5 || docker exec $NPM_CONTAINER ping -c 1 sistema-familiar_backend 2>&1 | head -3
echo ""

echo "📋 RECOMENDAÇÕES:"
echo "================="
echo ""
echo "Se nenhum teste funcionou:"
echo "  1. Verifique o nome do serviço no NPM (deve ser: sistema-familiar_backend)"
echo "  2. Verifique a porta no NPM (deve ser: 8001)"
echo "  3. Reinicie o NPM: docker restart $NPM_CONTAINER"
echo "  4. Reinicie o backend: docker service update --force sistema-familiar_backend"
echo ""

