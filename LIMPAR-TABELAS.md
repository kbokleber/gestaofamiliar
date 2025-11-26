# Limpeza de Tabelas Não Utilizadas

Este documento lista as tabelas que devem existir no sistema e fornece instruções para remover tabelas não utilizadas.

## Tabelas que DEVEM existir (definidas nos modelos):

### Autenticação e Usuários
- `auth_user` - Usuários do sistema
- `accounts_profile` - Perfis estendidos dos usuários
- `user_families` - Relacionamento many-to-many entre usuários e famílias

### Famílias
- `families` - Famílias (multi-tenancy)

### Dashboard
- `dashboard_dashboardpreference` - Preferências do dashboard

### Healthcare (Saúde)
- `healthcare_familymember` - Membros da família
- `healthcare_medicalappointment` - Consultas médicas
- `healthcare_medicalprocedure` - Procedimentos médicos
- `healthcare_medication` - Medicamentos

### Maintenance (Manutenção)
- `maintenance_equipment` - Equipamentos
- `maintenance_equipmentattachment` - Anexos de equipamentos
- `maintenance_maintenanceorder` - Ordens de manutenção
- `maintenance_maintenanceimage` - Imagens de manutenção

## Tabelas do sistema PostgreSQL (NÃO REMOVER):
- `spatial_ref_sys` - PostGIS (se instalado)
- Qualquer tabela que comece com `pg_` ou `information_schema`

## Tabelas do Django (podem ser removidas se não estiver usando Django):
- `django_migrations`
- `django_content_type`
- `django_session`
- `django_admin_log`
- Qualquer outra tabela que comece com `django_`

## Como verificar e limpar:

### Opção 1: Executar script dentro do container Docker

```bash
# Listar tabelas
docker exec -it <container_backend> python /app/scripts/list_tables.py

# Remover tabelas não utilizadas (com confirmação)
docker exec -it <container_backend> python /app/scripts/drop_unused_tables.py
```

### Opção 2: Executar SQL diretamente

Conecte-se ao banco de dados e execute:

```sql
-- Listar todas as tabelas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Para cada tabela não listada acima, execute:
DROP TABLE IF EXISTS <nome_da_tabela> CASCADE;
```

### Opção 3: Usar o script Python localmente

```bash
# Ativar ambiente virtual (se houver)
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Executar
python backend/scripts/list_tables.py
python backend/scripts/drop_unused_tables.py
```

## ⚠️ ATENÇÃO

- **SEMPRE faça backup do banco antes de remover tabelas!**
- Verifique cuidadosamente quais tabelas serão removidas
- Algumas tabelas podem ter sido criadas por migrações antigas do Django
- Tabelas com dados importantes devem ser migradas antes de remover

