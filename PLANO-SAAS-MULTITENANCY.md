# Plano de Implementação: SaaS Multi-Tenancy por Família

## ✅ O que já foi feito:

1. ✅ Modelo `Family` criado com `name` e `codigo_unico`
2. ✅ Relacionamento `User -> Family` adicionado (`family_id` no User)
3. ✅ Relacionamento `FamilyMember -> Family` adicionado
4. ✅ Relacionamento `Equipment -> Family` adicionado
5. ✅ Modelos atualizados no `__init__.py`

## 📋 O que ainda precisa ser feito:

### Backend:

1. **Schemas para Family:**
   - `FamilyBase`, `FamilyCreate`, `FamilyUpdate`, `Family`
   - Adicionar `family_id` nos schemas de `UserCreate`

2. **Endpoints para Family (CRUD):**
   - `GET /families/` - Listar famílias (apenas admins)
   - `POST /families/` - Criar família (apenas admins)
   - `GET /families/{id}` - Obter família (apenas admins)
   - `PUT /families/{id}` - Atualizar família (apenas admins)
   - `DELETE /families/{id}` - Deletar família (apenas admins)

3. **Atualizar dependências (deps.py):**
   - Criar função `get_current_family()` que retorna a família do usuário atual
   - Para admins: permitir escolher família via query param `?family_id=X`
   - Para usuários normais: usar `current_user.family_id`

4. **Filtrar todos os endpoints por família:**
   - **Healthcare:**
     - `GET /healthcare/members` - filtrar por `family_id`
     - `GET /healthcare/appointments` - filtrar por `family_id` (através do member)
     - `GET /healthcare/procedures` - filtrar por `family_id`
     - `GET /healthcare/medications` - filtrar por `family_id`
     - `POST /healthcare/*` - garantir que `family_id` seja definido
   
   - **Maintenance:**
     - `GET /maintenance/equipment` - filtrar por `family_id`
     - `GET /maintenance/orders` - filtrar por `family_id` (através do equipment)
     - `POST /maintenance/*` - garantir que `family_id` seja definido

5. **Atualizar criação de usuário:**
   - `POST /users/` - exigir `family_id` (ou criar família automaticamente)
   - `POST /auth/register` - criar família automaticamente ou exigir código

### Frontend:

1. **Store para família atual:**
   - Adicionar `currentFamily` no `authStore`
   - Salvar no localStorage
   - Atualizar ao fazer login

2. **Seletor de família (apenas admins):**
   - Componente no header/layout
   - Dropdown para escolher família
   - Atualizar todas as requisições com `?family_id=X`

3. **Tela de gerenciamento de famílias:**
   - Listar famílias
   - Criar nova família
   - Editar família
   - Deletar família
   - Ver usuários da família

4. **Atualizar criação de usuário:**
   - Campo para selecionar família
   - Ou campo para código único da família

5. **Atualizar registro:**
   - Campo para código único da família
   - Ou criar nova família

## 🔄 Migração de Dados:

1. Criar script de migração para:
   - Criar família padrão para dados existentes
   - Associar usuários existentes à família padrão
   - Associar dados existentes à família padrão

## 🎯 Fluxo de Uso:

### Para Usuários Normais:
1. Fazem login
2. Sistema usa automaticamente `user.family_id`
3. Veem apenas dados da sua família

### Para Admins:
1. Fazem login
2. Podem escolher qual família visualizar (dropdown)
3. Veem dados da família selecionada
4. Podem gerenciar famílias (CRUD)
5. Podem criar usuários e associar à família

## 📝 Notas Importantes:

- **Segurança:** Sempre validar que o usuário tem acesso à família
- **Performance:** Índices em `family_id` já foram adicionados
- **Compatibilidade:** Manter `family_id` como nullable temporariamente para migração
- **Validação:** Não permitir que usuário normal acesse dados de outra família

