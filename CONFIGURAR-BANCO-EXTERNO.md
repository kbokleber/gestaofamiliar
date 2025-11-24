# 🔌 Configurar Conexão com Banco de Dados Existente

Este guia explica como configurar o sistema para usar um banco de dados PostgreSQL que já está rodando em Docker separado.

## 📋 Passo a Passo

### 1. Descobrir Informações do Banco Existente

```bash
# Listar containers PostgreSQL
docker ps | grep postgres

# Ver detalhes do container do banco
docker inspect nome-container-postgres

# Descobrir a rede do banco
docker inspect nome-container-postgres | grep -A 10 "Networks"

# Ou verificar qual rede o container está usando
docker inspect nome-container-postgres --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}}{{end}}'
```

### 2. Configurar DATABASE_URL no .env

Edite o arquivo `.env` com a URL de conexão correta:

**Se o banco estiver na mesma rede Docker:**
```env
DATABASE_URL=postgresql://usuario:senha@nome-container-postgres:5432/sistema_familiar
```

**Se o banco estiver em outro servidor:**
```env
DATABASE_URL=postgresql://usuario:senha@ip-servidor:5432/sistema_familiar
```

**Se o banco estiver acessível via hostname:**
```env
DATABASE_URL=postgresql://usuario:senha@hostname-banco:5432/sistema_familiar
```

### 3. Configurar Rede Externa no docker-stack.yml

Abra o arquivo `docker-stack.yml` ou `docker-stack-simple.yml` e ajuste o nome da rede:

```yaml
networks:
  sistema-familiar-network:
    driver: overlay
    attachable: true
  # Ajuste este nome para a rede do seu banco de dados
  external_db_network:
    external: true
    name: nome-da-rede-do-banco  # Substitua pelo nome real da rede
```

**Para descobrir o nome exato da rede:**
```bash
# Listar todas as redes
docker network ls

# Ver detalhes da rede do banco
docker network inspect nome-da-rede-do-banco
```

### 4. Alternativa: Conectar Backend à Rede do Banco

Se preferir não modificar o docker-stack.yml, você pode conectar o container do backend à rede do banco após o deploy:

```bash
# Após fazer o deploy
docker service update --network-add nome-da-rede-do-banco sistema-familiar_backend
```

### 5. Verificar Conexão

Após o deploy, verifique os logs do backend:

```bash
docker service logs -f sistema-familiar_backend
```

Procure por mensagens de erro de conexão com o banco. Se tudo estiver correto, você verá a aplicação iniciando normalmente.

## 🔍 Exemplo Prático

Suponha que seu banco está rodando assim:

```bash
# Container do banco
docker ps
# Nome: postgres-prod
# Rede: bridge (padrão)

# Para conectar, você tem duas opções:
```

**Opção 1: Usar IP do container**
```env
# Descobrir IP do container
docker inspect postgres-prod | grep IPAddress

# No .env
DATABASE_URL=postgresql://postgres:senha@172.17.0.2:5432/sistema_familiar
```

**Opção 2: Conectar à mesma rede**
```bash
# Criar uma rede compartilhada
docker network create sistema-familiar-network

# Conectar o banco à rede
docker network connect sistema-familiar-network postgres-prod

# No docker-stack.yml, usar essa rede como external
external_db_network:
  external: true
  name: sistema-familiar-network

# No .env
DATABASE_URL=postgresql://postgres:senha@postgres-prod:5432/sistema_familiar
```

## ⚠️ Importante

- Certifique-se de que o banco está acessível do container do backend
- Verifique se as credenciais estão corretas
- Se o banco estiver em outra máquina, verifique firewall e portas
- Para produção, use variáveis de ambiente seguras, não hardcode senhas

## 🐛 Troubleshooting

**Erro: "could not translate host name"**
- Verifique se o nome do host está correto
- Se usar nome de container, certifique-se de que estão na mesma rede

**Erro: "connection refused"**
- Verifique se a porta 5432 está aberta
- Verifique se o PostgreSQL está aceitando conexões externas

**Erro: "password authentication failed"**
- Verifique usuário e senha no .env
- Verifique se o usuário tem permissões no banco

