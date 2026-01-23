# Configuração de Timezone - São Paulo

## 📅 Mudanças Implementadas

Foi configurado o timezone de São Paulo (America/Sao_Paulo) em todos os containers Docker do sistema.

## 🔧 Arquivos Modificados

### 1. docker-compose.yml
- Adicionadas variáveis de ambiente `TZ` em todos os serviços
- Adicionada variável `PGTZ` no PostgreSQL para garantir timezone correto no banco
- Montados volumes `/etc/timezone` e `/etc/localtime` em todos os containers

### 2. backend/Dockerfile
- Instalado pacote `tzdata`
- Configurado timezone via variável de ambiente e symlink

### 3. frontend/Dockerfile
- Instalado pacote `tzdata` (Alpine Linux)
- Configurado timezone via variável de ambiente e symlink

## 🚀 Como Aplicar as Mudanças

### Opção 1: Rebuild dos Containers (Recomendado)

```bash
# Parar containers atuais
docker-compose down

# Rebuild e iniciar containers com novo timezone
docker-compose up -d --build
```

### Opção 2: Para Ambiente de Produção (Docker Swarm)

```bash
# Rebuild das imagens
docker-compose build

# Atualizar o stack
docker stack deploy -c docker-compose.yml sistema-familiar
```

## ✅ Verificar Timezone

### Backend (Python)
```bash
docker exec -it sistema-familiar-backend date
docker exec -it sistema-familiar-backend python -c "import datetime; print(datetime.datetime.now())"
```

### Frontend (Nginx)
```bash
docker exec -it sistema-familiar-frontend date
```

### PostgreSQL
```bash
docker exec -it sistema-familiar-db psql -U postgres -d sistema_familiar -c "SHOW timezone;"
docker exec -it sistema-familiar-db date
```

## 🐛 Troubleshooting

### Timezone ainda aparece como UTC

**Solução:** A configuração já está otimizada para Windows. O timezone é definido através de:
1. Variável de ambiente `TZ=America/Sao_Paulo` no docker-compose.yml
2. Instalação do pacote `tzdata` nos Dockerfiles
3. Configuração via symlink nos Dockerfiles

Se ainda assim o timezone não estiver correto, verifique se os containers foram reconstruídos com `--build`.

### Verificar logs dos containers

```bash
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres
```

## 📝 Notas Importantes

1. **Todas as datas no banco** agora serão armazenadas considerando o timezone de São Paulo
2. **Logs do sistema** terão horários corretos (UTC-3 no horário padrão, UTC-2 no horário de verão)
3. **APIs** retornarão timestamps no timezone configurado
4. **Backup e restore** devem considerar o timezone para evitar inconsistências

## 🔄 Rollback (Se Necessário)

Se precisar voltar à configuração anterior:

```bash
# Fazer checkout da versão anterior
git checkout HEAD~1 docker-compose.yml backend/Dockerfile frontend/Dockerfile

# Rebuild containers
docker-compose up -d --build
```

