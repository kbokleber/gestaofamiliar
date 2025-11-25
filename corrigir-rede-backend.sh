#!/bin/bash

# Script para corrigir conexão do backend com a rede nginx_public
# Uso: ./corrigir-rede-backend.sh

echo "🔧 CORRIGINDO CONEXÃO DO BACKEND COM REDE NGINX_PUBLIC"
echo "======================================================"
echo ""

# 1. Verificar se a rede existe
echo "1️⃣ Verificando se a rede nginx_public existe..."
if docker network ls | grep -q nginx_public; then
    echo "✅ Rede nginx_public existe"
else
    echo "❌ Rede nginx_public NÃO existe!"
    echo "   Você precisa criar a rede ou verificar o nome correto"
    echo "   Listando redes disponíveis:"
    docker network ls | grep nginx
    exit 1
fi
echo ""

# 2. Verificar nome exato da rede
echo "2️⃣ Nome exato da rede:"
NGINX_NETWORK=$(docker network ls | grep nginx_public | awk '{print $2}')
echo "   Rede encontrada: $NGINX_NETWORK"
echo ""

# 3. Remover e recriar o stack para forçar conexão à rede
echo "3️⃣ Removendo stack atual..."
docker stack rm sistema-familiar
echo "   Aguardando remoção completa..."
sleep 15

# Verificar se foi removido
if docker service ls | grep -q sistema-familiar; then
    echo "⚠️  Ainda há serviços rodando, aguardando mais..."
    sleep 10
fi
echo ""

# 4. Verificar se o docker-stack.yml está correto
echo "4️⃣ Verificando docker-stack.yml..."
if grep -q "nginx_public" docker-stack.yml; then
    echo "✅ docker-stack.yml tem nginx_public configurado"
else
    echo "❌ docker-stack.yml NÃO tem nginx_public!"
    echo "   Edite o arquivo e adicione nginx_public nas networks do backend"
    exit 1
fi
echo ""

# 5. Fazer deploy novamente
echo "5️⃣ Fazendo deploy novamente..."
./deploy.sh

# 6. Aguardar serviços iniciarem
echo ""
echo "6️⃣ Aguardando serviços iniciarem..."
sleep 15

# 7. Verificar se backend está na rede
echo ""
echo "7️⃣ Verificando se backend está na rede nginx_public..."
if docker service inspect sistema-familiar_backend 2>/dev/null | grep -q nginx_public; then
    echo "✅ Backend está na rede nginx_public!"
else
    echo "❌ Backend AINDA NÃO está na rede nginx_public"
    echo ""
    echo "   Tentando conectar manualmente..."
    docker service update --network-add nginx_public sistema-familiar_backend
    sleep 5
    if docker service inspect sistema-familiar_backend 2>/dev/null | grep -q nginx_public; then
        echo "✅ Conectado manualmente!"
    else
        echo "❌ Falha ao conectar. Verifique o nome da rede."
    fi
fi
echo ""

# 8. Verificar status final
echo "8️⃣ Status final dos serviços:"
docker service ls | grep sistema-familiar
echo ""

echo "✅ Processo concluído!"
echo ""
echo "Para verificar logs:"
echo "  docker service logs -f sistema-familiar_backend"
echo ""

