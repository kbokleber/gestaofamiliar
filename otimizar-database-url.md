# Guia: Otimizar Conexão com Banco de Dados

## Problema Identificado

Se a aplicação está lenta em produção, pode ser porque a conexão com o banco de dados está saindo pela **internet** em vez de usar a **rede interna** do Docker.

## Como Verificar

Execute os scripts de diagnóstico:

```powershell
# Verificar configuração atual e latência
.\diagnostico-rede.ps1

# Verificar redes Docker e containers
.\verificar-redes-docker.ps1
```

## Soluções

### Opção 1: Usar Nome do Container (Recomendado)

Se o PostgreSQL está rodando em um container Docker na mesma rede:

1. **Identifique o nome do container PostgreSQL:**
   ```powershell
   docker ps --filter "ancestor=postgres" --format "{{.Names}}"
   ```

2. **Atualize o DATABASE_URL no `.env`:**
   ```env
   # ANTES (usando IP público - LENTO)
   DATABASE_URL=postgresql://postgres:senha@89.116.186.192:5432/sistema_familiar_db
   
   # DEPOIS (usando nome do container - RÁPIDO)
   DATABASE_URL=postgresql://postgres:senha@nome-container-postgres:5432/sistema_familiar_db
   ```

### Opção 2: Usar IP Privado da Rede Docker

Se os containers estão na mesma rede Docker:

1. **Descubra o IP privado do container PostgreSQL:**
   ```powershell
   docker inspect nome-container-postgres | Select-String "IPAddress"
   ```

2. **Use o IP privado na DATABASE_URL:**
   ```env
   DATABASE_URL=postgresql://postgres:senha@172.x.x.x:5432/sistema_familiar_db
   ```

### Opção 3: Conectar Containers na Mesma Rede

Se o PostgreSQL está em outra rede Docker:

1. **Verifique se a rede `db_network` existe:**
   ```powershell
   docker network ls | Select-String "db_network"
   ```

2. **Se não existir, crie:**
   ```powershell
   docker network create db_network
   ```

3. **Conecte o container PostgreSQL à rede:**
   ```powershell
   docker network connect db_network nome-container-postgres
   ```

4. **Certifique-se que o `docker-stack.yml` está configurado:**
   ```yaml
   networks:
     - sistema-familiar-network
     - db_network  # Rede do banco
   ```

5. **Use o nome do container na DATABASE_URL:**
   ```env
   DATABASE_URL=postgresql://postgres:senha@nome-container-postgres:5432/sistema_familiar_db
   ```

## Verificação de Performance

### Antes da Otimização

Execute o diagnóstico e anote a latência:
```powershell
.\diagnostico-rede.ps1
```

### Depois da Otimização

1. **Reinicie os containers:**
   ```powershell
   docker stack rm sistema-familiar
   docker stack deploy -c docker-stack.yml sistema-familiar
   ```

2. **Execute o diagnóstico novamente:**
   ```powershell
   .\diagnostico-rede.ps1
   ```

3. **Compare as latências:**
   - **Rede interna:** < 5ms (excelente)
   - **Internet:** > 50ms (pode ser lento)

## Exemplo de Configuração Otimizada

### Arquivo `.env` (backend/.env)
```env
# Usando nome do container PostgreSQL
DATABASE_URL=postgresql://postgres:Azpmmxbr2412@postgres-container:5432/sistema_familiar_db

# Ou se estiver na mesma rede Docker
DATABASE_URL=postgresql://postgres:Azpmmxbr2412@postgres:5432/sistema_familiar_db
```

### Arquivo `docker-stack.yml`
```yaml
services:
  backend:
    networks:
      - sistema-familiar-network
      - db_network  # Rede compartilhada com PostgreSQL
    environment:
      DATABASE_URL: ${DATABASE_URL}  # Usa o .env
```

## Benefícios da Otimização

- ✅ **Latência reduzida:** De ~100-200ms para < 5ms
- ✅ **Maior throughput:** Sem limitações de banda da internet
- ✅ **Mais seguro:** Tráfego não sai da rede interna
- ✅ **Mais confiável:** Menos pontos de falha

## Troubleshooting

### Container não consegue resolver o hostname

1. Verifique se estão na mesma rede:
   ```powershell
   docker network inspect db_network
   ```

2. Teste a conectividade do container:
   ```powershell
   docker exec sistema-familiar-backend ping nome-container-postgres
   ```

### Ainda está lento após otimização

1. Verifique pool de conexões no SQLAlchemy
2. Adicione índices no banco de dados
3. Verifique queries N+1
4. Considere usar connection pooling

