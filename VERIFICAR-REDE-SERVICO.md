# 🔍 Verificar Rede do Serviço

## Comando para verificar qual rede o serviço está usando

```bash
# Ver todas as redes e seus IDs
docker network ls

# Ver qual rede o serviço está usando (comparar o ID)
docker service inspect sistema-familiar_frontend --format '{{range .Spec.TaskTemplate.Networks}}{{.Target}}{{end}}'

# Ver nome da rede pelo ID
docker network inspect 708c4wz6s3c2qrk5f1n9iz2xo --format '{{.Name}}'

# Verificar se está na rede nginx_public
docker network inspect nginx_public | grep -A 10 "sistema-familiar"
```

## Se NÃO estiver na rede nginx_public

```bash
# Conectar o serviço à rede nginx_public
docker service update --network-add nginx_public sistema-familiar_frontend

# Aguardar alguns segundos
sleep 5

# Verificar novamente
docker service inspect sistema-familiar_frontend | grep -A 5 "Networks"
```

## Verificar se o NPM consegue acessar

```bash
# Testar do container do NPM
docker exec $(docker ps -q -f name=nginx-proxy-manager) ping -c 2 sistema-familiar_frontend

# Ou testar com wget
docker exec $(docker ps -q -f name=nginx-proxy-manager) wget -O- http://sistema-familiar_frontend:80 --timeout=5
```

