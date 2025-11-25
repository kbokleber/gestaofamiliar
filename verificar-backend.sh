#!/bin/bash

# Script rápido para verificar status do backend
# Uso: ./verificar-backend.sh

echo "🔍 VERIFICAÇÃO RÁPIDA DO BACKEND"
echo "================================"
echo ""

# 1. Verificar se o serviço existe
echo "1️⃣ Serviço backend existe?"
if docker service ls | grep -q sistema-familiar_backend; then
    echo "✅ Sim"
else
    echo "❌ Não - Backend não está rodando!"
    exit 1
fi
echo ""

# 2. Verificar status do serviço
echo "2️⃣ Status do serviço:"
docker service ps sistema-familiar_backend --no-trunc | head -3
echo ""

# 3. Ver logs recentes (últimas 20 linhas)
echo "3️⃣ Últimas 20 linhas dos logs:"
echo "----------------------------------------"
docker service logs --tail 20 sistema-familiar_backend 2>&1
echo ""

# 4. Verificar se há erros nos logs
echo "4️⃣ Procurando erros nos logs:"
echo "----------------------------------------"
docker service logs sistema-familiar_backend 2>&1 | grep -i "error\|exception\|traceback\|failed" | tail -10 || echo "Nenhum erro encontrado nos logs recentes"
echo ""

# 5. Verificar se o container está rodando
echo "5️⃣ Container está rodando?"
CONTAINER=$(docker ps -q -f name=sistema-familiar-backend)
if [ -n "$CONTAINER" ]; then
    echo "✅ Sim - Container ID: $CONTAINER"
    
    # Testar health check
    echo ""
    echo "6️⃣ Testando health check:"
    docker exec $CONTAINER curl -s http://localhost:8001/health 2>/dev/null && echo "✅ Backend responde" || echo "❌ Backend não responde"
else
    echo "❌ Não - Container não está rodando!"
    echo ""
    echo "Verificando containers parados:"
    docker ps -a | grep sistema-familiar-backend
fi
echo ""

# 7. Verificar conectividade na rede
echo "7️⃣ Verificando rede nginx_public:"
docker service inspect sistema-familiar_backend 2>/dev/null | grep -q nginx_public && echo "✅ Backend está na rede nginx_public" || echo "❌ Backend NÃO está na rede nginx_public"
echo ""

echo "📋 PRÓXIMOS PASSOS:"
echo "==================="
echo ""
echo "Se o backend não está rodando:"
echo "  docker service update --force sistema-familiar_backend"
echo ""
echo "Se há erros nos logs, verifique:"
echo "  - Conexão com banco de dados (DATABASE_URL no .env)"
echo "  - Dependências Python instaladas"
echo "  - Erros de sintaxe no código"
echo ""
echo "Para ver logs em tempo real:"
echo "  docker service logs -f sistema-familiar_backend"
echo ""

