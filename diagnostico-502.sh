#!/bin/bash

# Script de diagnóstico para erro 502 Bad Gateway
# Uso: ./diagnostico-502.sh

echo "🔍 DIAGNÓSTICO: Erro 502 Bad Gateway"
echo "===================================="
echo ""

# 1. Verificar se os serviços estão rodando
echo "1️⃣ Verificando serviços Docker Swarm..."
echo "----------------------------------------"
docker service ls | grep sistema-familiar || echo "❌ Nenhum serviço encontrado!"
echo ""

# 2. Verificar status do backend
echo "2️⃣ Status do Backend..."
echo "----------------------------------------"
docker service ps sistema-familiar_backend --no-trunc 2>/dev/null || echo "❌ Serviço backend não encontrado!"
echo ""

# 3. Ver logs do backend
echo "3️⃣ Últimas 30 linhas dos logs do Backend..."
echo "----------------------------------------"
docker service logs --tail 30 sistema-familiar_backend 2>/dev/null || echo "❌ Não foi possível ler os logs!"
echo ""

# 4. Verificar se backend está na rede nginx_public
echo "4️⃣ Verificando rede do Backend..."
echo "----------------------------------------"
docker service inspect sistema-familiar_backend 2>/dev/null | grep -A 5 "Networks" | grep nginx_public && echo "✅ Backend está na rede nginx_public" || echo "❌ Backend NÃO está na rede nginx_public!"
echo ""

# 5. Testar conectividade do backend
echo "5️⃣ Testando conectividade do Backend..."
echo "----------------------------------------"
BACKEND_CONTAINER=$(docker ps -q -f name=sistema-familiar-backend)
if [ -n "$BACKEND_CONTAINER" ]; then
    echo "Container encontrado: $BACKEND_CONTAINER"
    docker exec $BACKEND_CONTAINER curl -s http://localhost:8001/health 2>/dev/null && echo "✅ Backend responde localmente" || echo "❌ Backend NÃO responde localmente"
else
    echo "❌ Container do backend não encontrado!"
fi
echo ""

# 6. Verificar configuração do docker-stack.yml
echo "6️⃣ Verificando configuração do docker-stack.yml..."
echo "----------------------------------------"
if grep -q "nginx_public" docker-stack.yml; then
    echo "✅ docker-stack.yml tem nginx_public configurado"
else
    echo "❌ docker-stack.yml NÃO tem nginx_public configurado!"
fi
echo ""

# 7. Verificar se NPM consegue alcançar o backend
echo "7️⃣ Testando do container do NPM..."
echo "----------------------------------------"
NPM_CONTAINER=$(docker ps -q -f name=nginx-proxy-manager)
if [ -n "$NPM_CONTAINER" ]; then
    echo "Container NPM encontrado: $NPM_CONTAINER"
    docker exec $NPM_CONTAINER wget -O- http://sistema-familiar_backend:8001/health --timeout=5 2>&1 | head -5 && echo "✅ NPM consegue alcançar o backend" || echo "❌ NPM NÃO consegue alcançar o backend"
else
    echo "⚠️ Container do NPM não encontrado (pode estar com outro nome)"
fi
echo ""

# 8. Resumo e recomendações
echo "📋 RESUMO E RECOMENDAÇÕES"
echo "===================================="
echo ""
echo "Se o backend não está rodando:"
echo "  docker service update --force sistema-familiar_backend"
echo ""
echo "Se o backend não está na rede nginx_public:"
echo "  - Verifique o docker-stack.yml"
echo "  - Execute: docker stack rm sistema-familiar"
echo "  - Execute: ./deploy.sh"
echo ""
echo "Se o backend está rodando mas não responde:"
echo "  docker service logs -f sistema-familiar_backend"
echo "  (Procure por erros de conexão com banco de dados)"
echo ""
echo "Para recriar tudo:"
echo "  docker stack rm sistema-familiar"
echo "  sleep 10"
echo "  ./deploy.sh"
echo ""

