# Resumo: Otimização de Performance - Conexão com Banco de Dados

## 🔍 Problema Identificado

A aplicação está lenta em produção porque a conexão com o banco de dados está usando **IP público** (`89.116.186.192`), fazendo o tráfego sair pela **internet** em vez de usar a **rede interna** do Docker.

## ✅ Soluções Implementadas

### 1. Scripts de Diagnóstico

Criados 3 scripts para ajudar a identificar e resolver o problema:

- **`diagnostico-rede.ps1`** - Verifica configuração atual, testa conectividade e mede latência
- **`verificar-redes-docker.ps1`** - Lista redes Docker e containers PostgreSQL disponíveis
- **`otimizar-database-url.md`** - Guia completo de otimização

### 2. Otimização do Pool de Conexões

Otimizado o SQLAlchemy para melhor performance:

- **Pool size:** 10 conexões (configurável)
- **Max overflow:** 20 conexões adicionais
- **Pool pre-ping:** Verifica conexões antes de usar
- **Pool recycle:** Recicla conexões após 1 hora
- **Configurável via variáveis de ambiente**

### 3. Configurações Adicionadas

Novas variáveis de ambiente opcionais no `.env`:

```env
# Pool de conexões (opcional - valores padrão já otimizados)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
```

## 🚀 Como Usar

### Passo 1: Executar Diagnóstico

```powershell
# Verificar configuração atual e latência
.\diagnostico-rede.ps1

# Verificar redes Docker
.\verificar-redes-docker.ps1
```

### Passo 2: Identificar o Nome do Container PostgreSQL

```powershell
docker ps --filter "ancestor=postgres" --format "{{.Names}}"
```

### Passo 3: Atualizar DATABASE_URL

Edite o arquivo `backend/.env`:

```env
# ANTES (usando IP público - LENTO)
DATABASE_URL=postgresql://postgres:Azpmmxbr2412@89.116.186.192:5432/sistema_familiar_db

# DEPOIS (usando nome do container - RÁPIDO)
DATABASE_URL=postgresql://postgres:Azpmmxbr2412@nome-container-postgres:5432/sistema_familiar_db
```

**OU se o container PostgreSQL estiver na mesma rede Docker:**

```env
DATABASE_URL=postgresql://postgres:Azpmmxbr2412@postgres:5432/sistema_familiar_db
```

### Passo 4: Verificar Redes Docker

Certifique-se que os containers estão na mesma rede:

```powershell
# Verificar se a rede db_network existe
docker network ls | Select-String "db_network"

# Se não existir, criar
docker network create db_network

# Conectar container PostgreSQL à rede
docker network connect db_network nome-container-postgres
```

### Passo 5: Reiniciar Aplicação

```powershell
# Se usando Docker Swarm
docker stack rm sistema-familiar
docker stack deploy -c docker-stack.yml sistema-familiar

# Se usando docker-compose
docker-compose down
docker-compose up -d
```

### Passo 6: Verificar Melhoria

Execute o diagnóstico novamente e compare a latência:

```powershell
.\diagnostico-rede.ps1
```

**Resultados esperados:**
- **Antes:** 100-200ms (internet)
- **Depois:** < 5ms (rede interna) ✅

## 📊 Benefícios Esperados

- ✅ **Latência reduzida:** De ~100-200ms para < 5ms
- ✅ **Maior throughput:** Sem limitações de banda da internet
- ✅ **Mais seguro:** Tráfego não sai da rede interna
- ✅ **Mais confiável:** Menos pontos de falha
- ✅ **Pool otimizado:** Melhor gerenciamento de conexões

## 🔧 Arquivos Modificados

1. `backend/app/db/base.py` - Pool de conexões otimizado
2. `backend/app/core/config.py` - Configurações de pool adicionadas

## 📝 Arquivos Criados

1. `diagnostico-rede.ps1` - Script de diagnóstico
2. `verificar-redes-docker.ps1` - Script para verificar redes Docker
3. `otimizar-database-url.md` - Guia completo de otimização
4. `RESUMO-OTIMIZACAO.md` - Este arquivo

## ⚠️ Importante

- Se o PostgreSQL está em outro servidor físico, você precisará usar VPN ou rede privada
- Se está no mesmo servidor mas em container diferente, use nome do container
- Se está no mesmo container/compose, use `postgres` como hostname

## 🆘 Troubleshooting

Se após a otimização ainda estiver lento:

1. Verifique se os containers estão na mesma rede Docker
2. Teste conectividade: `docker exec sistema-familiar-backend ping nome-container-postgres`
3. Verifique logs: `docker logs sistema-familiar-backend`
4. Considere adicionar índices no banco de dados
5. Verifique queries N+1 no código

