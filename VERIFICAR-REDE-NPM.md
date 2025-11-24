# 🔍 Verificar e Conectar Serviços à Rede do NPM

## Problema: Bad Gateway

O erro "Bad Gateway" geralmente significa que o Nginx Proxy Manager não consegue acessar o serviço Docker. Isso acontece quando os serviços não estão na mesma rede Docker.

## Passo 1: Descobrir a rede do NPM

Execute no servidor:

```bash
# Ver todas as redes Docker
docker network ls

# Ver qual rede o NPM está usando
docker ps | grep nginx-proxy-manager
docker inspect $(docker ps -q -f name=nginx-proxy-manager) | grep -A 10 "Networks"
```

Anote o nome da rede (geralmente algo como: `nginx-proxy-manager_default`, `nginx_public`, `npm_default`, etc.)

## Passo 2: Verificar se os serviços estão nessa rede

```bash
# Ver em qual rede os serviços estão
docker service inspect sistema-familiar_frontend --format '{{range .Spec.TaskTemplate.Networks}}{{.Target}}{{end}}'
docker service inspect sistema-familiar_backend --format '{{range .Spec.TaskTemplate.Networks}}{{.Target}}{{end}}'
```

## Passo 3: Conectar os serviços à rede do NPM

Se os serviços NÃO estiverem na rede do NPM, conecte-os:

```bash
# Substitua NOME_DA_REDE_NPM pelo nome real da rede do NPM
docker service update --network-add NOME_DA_REDE_NPM sistema-familiar_frontend
docker service update --network-add NOME_DA_REDE_NPM sistema-familiar_backend
```

## Passo 4: Verificar se funcionou

```bash
# Verificar se os serviços estão na rede
docker network inspect NOME_DA_REDE_NPM | grep sistema-familiar
```

## Passo 5: Testar no NPM

1. No NPM, configure:
   - **Domain Names:** `gestaofamiliar.kbosolucoes.com.br`
   - **Forward Hostname/IP:** `sistema-familiar_frontend` (nome completo, sem erros)
   - **Forward Port:** `80`
   - ✅ Marque **"Websockets Support"**

2. Salve e teste

## Alternativa: Usar IP do container

Se ainda não funcionar, você pode usar o IP do container diretamente:

```bash
# Descobrir IP do container frontend
docker inspect $(docker ps -q -f name=sistema-familiar-frontend) | grep IPAddress

# Usar esse IP no NPM ao invés do nome do serviço
```

Mas usar o nome do serviço é melhor porque funciona mesmo se o container reiniciar.

