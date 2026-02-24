# Deploy do Sistema Familiar no Coolify

Este guia explica como publicar a aplicação no [Coolify](https://coolify.io/) (PaaS self-hosted).

## Visão geral

A aplicação tem **3 partes**:

| Serviço   | Descrição                    | Porta  |
|-----------|------------------------------|--------|
| **PostgreSQL** | Banco de dados               | 5432   |
| **Backend**    | API FastAPI                  | 8001   |
| **Frontend**   | React (Nginx servindo build) | 80     |

---

## Banco novo ou banco externo?

| Arquivo | Quando usar |
|---------|-------------|
| **`docker-compose.yml`** | Cria um **PostgreSQL novo** dentro do projeto (container + volume). Use quando quiser tudo no mesmo stack. |
| **`docker-compose.external-db.yml`** | **Não** sobe Postgres. O backend usa a variável **`DATABASE_URL`** apontando para um banco **já existente** (PostgreSQL do Coolify, outro servidor, etc.). O frontend usa a **porta 3000** (evita conflito com a porta 80 já usada no servidor). |

No Coolify você pode criar um **Database** (PostgreSQL) e depois usar `docker-compose.external-db.yml` com a URL que o Coolify fornece. Ao configurar o domínio do frontend no Coolify, use a **porta 3000** (não 80).

**Variáveis para banco externo** (`docker-compose.external-db.yml`): defina `DATABASE_URL` (ex.: `postgresql://usuario:senha@host:5432/banco`), `SECRET_KEY` e, se quiser, `VITE_API_URL`.

---

## Variáveis para copiar e colar

O **host do banco** fica dentro da `DATABASE_URL`: `postgresql://usuario:senha@HOST:porta/nome_do_banco`. No Coolify, ao criar um Database PostgreSQL, ele informa o host (pode ser um hostname interno, ex.: `postgres.instancia` ou um IP).

### Se usar `docker-compose.yml` (banco novo criado pelo próprio compose)

Cole no Coolify em **Environment Variables** (uma linha por variável, no formato `NOME=valor`):

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=coloque_uma_senha_forte_aqui
POSTGRES_DB=sistema_familiar
SECRET_KEY=cole_aqui_uma_chave_gerada_com_openssl_rand_hex_32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Para gerar `SECRET_KEY`: no terminal execute `openssl rand -hex 32` e use o resultado.

---

### Se usar `docker-compose.external-db.yml` (banco externo, ex.: PostgreSQL do Coolify)

Substitua pelos dados reais que o Coolify (ou seu provedor) fornece: **host**, **porta**, **usuário**, **senha** e **nome do banco**. Cole no Coolify em **Environment Variables**:

```
DATABASE_URL=postgresql://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO
SECRET_KEY=cole_aqui_uma_chave_gerada_com_openssl_rand_hex_32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
VITE_API_URL=https://api.seudominio.com
```

**Exemplo** (troque pelos seus dados):

```
DATABASE_URL=postgresql://postgres:minhasenha123@postgres.meuprojeto.svc:5432/sistema_familiar
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
VITE_API_URL=https://api.seudominio.com
```

- **USUARIO** / **SENHA**: usuário e senha do PostgreSQL.
- **HOST**: hostname ou IP do servidor do banco (no Coolify aparece na tela do recurso Database).
- **5432**: porta padrão do PostgreSQL (ajuste se for outra).
- **NOME_DO_BANCO**: nome do banco criado (ex.: `sistema_familiar`).
- **VITE_API_URL**: URL pública do backend (para o frontend chamar a API). Se o front e a API forem no mesmo domínio com proxy em `/api`, use: `VITE_API_URL=/api`.

---

## Opção 1: Deploy com Docker Compose (recomendado)

Coolify consegue subir o repositório inteiro como um **stack Docker Compose**.

### 1. Criar novo recurso no Coolify

1. No Coolify: **Project** → **Add Resource** → **Docker Compose**.
2. Conecte o repositório Git (GitHub/GitLab) com o projeto **SistemaFamiliar2.0**.
3. Defina o **Docker Compose Location**:
   - **Banco novo (tudo no projeto):** `docker-compose.yml`
   - **Banco externo (Coolify DB ou outro):** `docker-compose.external-db.yml`

### 2. Variáveis de ambiente

No Coolify, na tela do recurso, em **Environment Variables**, defina (ou use um arquivo `.env` no repositório, sem segredos):

| Variável | Obrigatório | Exemplo | Descrição |
|----------|-------------|---------|-----------|
| `POSTGRES_USER` | Sim | `postgres` | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | Sim | **(senha forte)** | Senha do PostgreSQL |
| `POSTGRES_DB` | Sim | `sistema_familiar` | Nome do banco |
| `SECRET_KEY` | Sim | **(gerar com `openssl rand -hex 32`)** | Chave JWT |
| `ALGORITHM` | Não | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Não | `30` | Expiração do token (min) |

O backend usa `DATABASE_URL` montada no `docker-compose` a partir dessas variáveis. Não é obrigatório definir `DATABASE_URL` manualmente se o compose já fizer isso.

### 3. URL da API no frontend (importante)

O frontend precisa saber o endereço do backend **no momento do build** (variável `VITE_API_URL`).

- Se no Coolify você expõe o **backend** em um domínio, por exemplo:  
  `https://api.seudominio.com`
- Então o build do frontend deve usar essa URL.

No Coolify, no serviço do **frontend** (ou no build do Compose):

1. Adicione um **Build Argument**:
   - Nome: `VITE_API_URL`
   - Valor: `https://api.seudominio.com` (ou a URL real do backend)

Se o frontend e o backend forem servidos pelo **mesmo domínio** (ex.: `https://app.seudominio.com` e `https://app.seudominio.com/api`), use:

- `VITE_API_URL=/api`

Assim o frontend fará requisições relativas para `/api`, e o proxy reverso do Coolify/Nginx pode encaminhar `/api` para o container do backend.

### 4. Domínios e proxy no Coolify

- Crie um **domínio** para o frontend (ex.: `app.seudominio.com`) e aponte para o serviço **frontend** (porta **80** no `docker-compose.yml`; porta **3000** no `docker-compose.external-db.yml`).
- Se quiser subdomínio para a API, crie outro domínio (ex.: `api.seudominio.com`) apontando para o **backend** (porta 8001).
- Ou use um único domínio e configure no Coolify/Nginx um proxy:  
  `https://app.seudominio.com/api` → container backend:8001.

### 5. Produção: remover volume do backend (opcional)

O `docker-compose.yml` atual monta `./backend:/app` no backend (útil em dev). Em produção no Coolify é melhor **não** montar o código; usar só a imagem buildada.

Você pode:

- Criar um `docker-compose.coolify.yml` (ou override) **sem** o `volumes` do backend, **ou**
- No Coolify, editar o compose e remover o bloco:

```yaml
# Remover isto do serviço backend em produção:
volumes:
  - ./backend:/app
```

Assim o container usa apenas o que foi copiado no `Dockerfile`.

### 6. Deploy

1. Salve as variáveis e, se usou, o build arg do frontend.
2. Clique em **Deploy** (ou configure deploy automático no Git).
3. Aguarde o build dos containers e verifique os logs em caso de erro.

---

## Opção 2: Serviços separados no Coolify

Se preferir não usar Docker Compose:

1. **PostgreSQL**: crie um recurso **Database** → PostgreSQL no Coolify e anote host, porta, usuário, senha e nome do banco.
2. **Backend**: crie **Application** → **Dockerfile**, apontando para a pasta `backend/` do repositório. Defina `DATABASE_URL`, `SECRET_KEY`, etc., e exponha a porta 8001.
3. **Frontend**: crie **Application** → **Dockerfile**, apontando para a pasta `frontend/`. Defina o build arg `VITE_API_URL` com a URL do backend (ou `/api` se for mesmo domínio com proxy).
4. Configure domínios e proxy como na opção 1.

---

## Checklist rápido

- [ ] Repositório conectado no Coolify (Docker Compose ou serviços separados).
- [ ] Variáveis `POSTGRES_*` e `SECRET_KEY` definidas.
- [ ] Build do frontend com `VITE_API_URL` correto (URL do backend ou `/api`).
- [ ] Domínio(s) e proxy configurados (frontend e, se quiser, API).
- [ ] Em produção: sem volume `./backend:/app` no backend (opcional mas recomendado).
- [ ] Após o primeiro deploy: rodar migrações/criação de tabelas no backend, se o projeto exigir.

---

## Migrações do banco

Se o backend usar migrações (Alembic ou scripts), após o primeiro deploy acesse o container do backend ou use um job no Coolify para rodar, por exemplo:

```bash
# Exemplo – ajuste ao que seu projeto usa
alembic upgrade head
# ou
python -m app.scripts.create_tables
```

---

## Referências

- [Coolify – Docker Compose](https://coolify.io/docs/docker-compose)
- [Coolify – Environment Variables](https://coolify.io/docs/env-variables)
