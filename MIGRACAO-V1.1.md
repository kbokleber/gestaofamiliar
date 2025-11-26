# Guia de Migração para Versão 1.1

## ⚠️ IMPORTANTE: Migração do Banco de Dados

A versão 1.1 introduz o sistema multi-tenant com famílias. **É necessário executar scripts de migração ANTES do redeploy** para evitar erros.

## 📋 Checklist Pré-Redeploy

### 1. Backup do Banco de Dados
```bash
# Fazer backup antes de qualquer alteração
pg_dump -h <HOST> -U <USER> -d <DATABASE> > backup_pre_v1.1_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Executar Scripts de Migração (em ordem)

Execute os scripts na seguinte ordem dentro do container do backend:

```bash
# 1. Criar tabela families (se não existir)
docker exec -it <CONTAINER_BACKEND> python scripts/create_tables.py

# 2. Adicionar family_id na tabela auth_user
docker exec -it <CONTAINER_BACKEND> python scripts/add_family_id_to_users.py

# 3. Criar tabela user_families (many-to-many)
docker exec -it <CONTAINER_BACKEND> python scripts/create_user_families_table.py

# 4. Adicionar family_id em healthcare_familymember
docker exec -it <CONTAINER_BACKEND> python scripts/check_family_member_table.py

# 5. Adicionar family_id em outras tabelas (equipment, etc)
docker exec -it <CONTAINER_BACKEND> python scripts/migrate_all_family_tables.py

# 6. Migrar usuários existentes para uma família padrão
docker exec -it <CONTAINER_BACKEND> python scripts/migrate_users_to_family.py
```

### 3. Verificar Migração

Após executar os scripts, verifique se:
- Tabela `families` existe
- Tabela `user_families` existe
- Coluna `family_id` existe em `auth_user`
- Coluna `family_id` existe em `healthcare_familymember`
- Coluna `family_id` existe em `maintenance_equipment`
- Todos os usuários têm `family_id` preenchido

### 4. Redeploy

Após confirmar que as migrações foram aplicadas, execute o redeploy:

```bash
cd /opt/sistema-familiar && git pull origin master && chmod +x redeploy-seguro.sh && ./redeploy-seguro.sh
```

## 🔄 Processo Completo (Script Único)

Se preferir, você pode criar um script que executa tudo:

```bash
#!/bin/bash
# migrar-v1.1.sh

echo "=== Iniciando migração para v1.1 ==="

# Backup
echo "1. Fazendo backup..."
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_pre_v1.1_$(date +%Y%m%d_%H%M%S).sql

# Executar migrações
echo "2. Executando migrações..."
docker exec -it sistema-familiar_backend.1.$(docker service ps -f "name=sistema-familiar_backend" -q | head -1) python scripts/create_tables.py
docker exec -it sistema-familiar_backend.1.$(docker service ps -f "name=sistema-familiar_backend" -q | head -1) python scripts/add_family_id_to_users.py
docker exec -it sistema-familiar_backend.1.$(docker service ps -f "name=sistema-familiar_backend" -q | head -1) python scripts/create_user_families_table.py
docker exec -it sistema-familiar_backend.1.$(docker service ps -f "name=sistema-familiar_backend" -q | head -1) python scripts/check_family_member_table.py
docker exec -it sistema-familiar_backend.1.$(docker service ps -f "name=sistema-familiar_backend" -q | head -1) python scripts/migrate_all_family_tables.py
docker exec -it sistema-familiar_backend.1.$(docker service ps -f "name=sistema-familiar_backend" -q | head -1) python scripts/migrate_users_to_family.py

echo "3. Migração concluída!"
echo "4. Execute o redeploy:"
echo "   cd /opt/sistema-familiar && git pull origin master && chmod +x redeploy-seguro.sh && ./redeploy-seguro.sh"
```

## ⚠️ Problemas Comuns

### Erro: "relation 'families' does not exist"
**Solução:** Execute `create_tables.py` primeiro

### Erro: "column 'family_id' does not exist"
**Solução:** Execute os scripts de migração correspondentes

### Erro: "foreign key constraint fails"
**Solução:** Certifique-se de que a tabela `families` existe e tem dados antes de adicionar foreign keys

## ✅ Verificação Pós-Migração

Após o redeploy, verifique:
1. Login funciona normalmente
2. Usuários podem acessar suas telas
3. Admins podem ver dados de todas as famílias
4. Tela de administração de famílias está acessível
5. Tela de administração de usuários permite gerenciar famílias

## 📞 Suporte

Se encontrar problemas durante a migração:
1. Restaure o backup
2. Verifique os logs: `docker service logs -f sistema-familiar_backend`
3. Verifique se todas as tabelas/colunas foram criadas corretamente

