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

## Qual compose usar?

| Arquivo | Quando usar |
|---------|-------------|
| **`docker-compose.external-db.yml`** | **Recomendado no Coolify.** Inclui **PostgreSQL** + backend + frontend no mesmo stack. Frontend na **porta 3000** (evita conflito com a 80). Variáveis: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SECRET_KEY`. Após o deploy, importe o backup no Postgres (DBeaver ou pg_restore). |
| **`docker-compose.yml`** | Postgres + backend + frontend; frontend na porta 80. Útil para rodar local ou quando a 80 estiver livre. |

No Coolify, use **`docker-compose.external-db.yml`** e configure o domínio do frontend para a **porta 3000**.

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

### Se usar `docker-compose.external-db.yml` (Postgres dentro do compose – recomendado no Coolify)

O Postgres sobe junto com a aplicação. Cole no Coolify em **Environment Variables** (obrigatório: `POSTGRES_PASSWORD` e `SECRET_KEY`):

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=coloque_uma_senha_forte_aqui
POSTGRES_DB=sistema_familiar_db
SECRET_KEY=cole_aqui_uma_chave_gerada_com_openssl_rand_hex_32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
VITE_API_URL=
```

- **POSTGRES_PASSWORD**: senha do usuário postgres (obrigatória).
- **POSTGRES_DB**: nome do banco (padrão `sistema_familiar_db`). Use o mesmo nome do backup para restaurar.
- **VITE_API_URL**: deixe vazio para o frontend usar `/api` no mesmo domínio (o Nginx do front faz proxy para o backend).

Após o primeiro deploy, **importe o backup** no Postgres (DBeaver conectando no IP do servidor Coolify, porta 5432, ou use o terminal do Coolify para rodar `pg_restore`).

---

## Opção 1: Deploy com Docker Compose (recomendado)

Coolify consegue subir o repositório inteiro como um **stack Docker Compose**.

### 1. Criar novo recurso no Coolify

1. No Coolify: **Project** → **Add Resource** → **Docker Compose**.
2. Conecte o repositório Git (GitHub/GitLab) com o projeto **SistemaFamiliar2.0**.
3. Defina o **Docker Compose Location**: use **`docker-compose.external-db.yml`** (inclui Postgres; frontend na porta 3000).

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

- Crie um **domínio** para o frontend (ex.: `app.seudominio.com`) e aponte para o serviço **frontend**.
  - **Importante:** no Coolify, ao vincular o domínio ao serviço **frontend**, informe a **porta da aplicação**:
    - Se usa **`docker-compose.yml`** (banco novo): porta **80**.
    - Se usa **`docker-compose.external-db.yml`** (banco externo): porta **3000** (o compose publica `3000:80` para evitar conflito com a 80 do servidor).
  - Se a porta ficar errada (ex.: 80 quando o compose expõe 3000), o site pode dar **"Não é possível acessar esse site" / ERR_CONNECTION_RESET** mesmo com o build ok.
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

## Backup e restauração do PostgreSQL

Use estes passos para fazer backup de um banco (ex.: servidor atual) e importar no PostgreSQL do Coolify. **Não coloque senhas no repositório** — use variáveis de ambiente ou digite quando pedido.

### 1. Fazer o backup do banco atual

No PowerShell (ou terminal), com [PostgreSQL client](https://www.postgresql.org/download/windows/) instalado, ou usando Docker:

**Opção A – pg_dump instalado na máquina**

```powershell
# Substitua pela sua URL de origem (ou use variável de ambiente)
$env:PGPASSWORD = "sua_senha"
pg_dump -h 89.116.186.192 -p 5432 -U postgres -d sistema_familiar_db -Fc -f backup_sistema_familiar.dump
```

**Opção B – usando Docker (não precisa instalar PostgreSQL)**

```powershell
docker run --rm -v "${PWD}:/backup" postgres:15-alpine pg_dump "postgresql://postgres:SUA_SENHA@89.116.186.192:5432/sistema_familiar_db" -Fc -f /backup/backup_sistema_familiar.dump
```

- `-Fc` = formato custom (compacto, ideal para `pg_restore`).
- O arquivo `backup_sistema_familiar.dump` será criado na pasta atual.

### 2. No Coolify: criar o banco e pegar a URL

1. No Coolify: **Project** → **Add Resource** → **Database** → **PostgreSQL**.
2. Crie o banco (ex.: nome `sistema_familiar` ou `sistema_familiar_db`).
3. Anote a **connection string** que o Coolify mostra (host, porta, usuário, senha, nome do banco). Ela costuma ser algo como:
   - `postgresql://usuario:senha@host:5432/nome_do_banco`
   - O host pode ser interno (ex.: `postgres.instancia.svc`) ou um IP/domínio que o Coolify informar.

### 3. Restaurar o backup no PostgreSQL do Coolify

O Coolify pode expor o PostgreSQL na rede (porta pública ou rede interna). Você precisa conseguir conectar do seu PC ou de um container ao host:porta do banco.

**Opção A – Conexão direta (Coolify expõe a porta do banco)**

```powershell
# Substitua HOST, PORTA, USUARIO, SENHA e NOME_DO_BANCO pelos dados que o Coolify mostrou
$env:PGPASSWORD = "SENHA_DO_COOLIFY"
pg_restore -h HOST -p PORTA -U USUARIO -d NOME_DO_BANCO --clean --if-exists --no-owner backup_sistema_familiar.dump
```

**Opção B – Usando Docker (funciona mesmo sem pg_restore instalado)**

Coloque `backup_sistema_familiar.dump` na pasta atual. Substitua `HOST`, `PORTA`, `USUARIO`, `SENHA` e `NOME_DO_BANCO` pelos dados do PostgreSQL do Coolify. Se o Coolify estiver em outro servidor, use o IP ou domínio desse servidor.

```powershell
docker run --rm -v "${PWD}:/backup" -e PGPASSWORD=SENHA postgres:15-alpine pg_restore -h HOST -p PORTA -U USUARIO -d NOME_DO_BANCO --clean --if-exists --no-owner /backup/backup_sistema_familiar.dump
```

Exemplo (Coolify no IP 192.168.1.10, porta 5432):

```powershell
docker run --rm -v "${PWD}:/backup" -e PGPASSWORD=minhasenha postgres:15-alpine pg_restore -h 192.168.1.10 -p 5432 -U postgres -d sistema_familiar_db --clean --if-exists --no-owner /backup/backup_sistema_familiar.dump
```

### 4. Após a restauração

1. No recurso **Docker Compose** (ou Application) do Sistema Familiar no Coolify, defina **DATABASE_URL** com a connection string do **novo** banco (o que você acabou de restaurar).
2. Faça um novo deploy ou reinicie o backend para ele usar o banco com os dados importados.

### Dica: backup em SQL (texto)

Se preferir um arquivo `.sql` (mais fácil de inspecionar ou importar em outros sistemas):

```powershell
# Backup
docker run --rm -v "${PWD}:/backup" postgres:15-alpine pg_dump "postgresql://postgres:SUA_SENHA@89.116.186.192:5432/sistema_familiar_db" -f /backup/backup.sql

# Restore (no Coolify)
docker run --rm -v "${PWD}:/backup" -e PGPASSWORD=SENHA_COOLIFY postgres:15-alpine psql "postgresql://USUARIO@HOST:PORTA/NOME_DO_BANCO" -f /backup/backup.sql
```

---

## Referências

- [Coolify – Docker Compose](https://coolify.io/docs/docker-compose)
- [Coolify – Environment Variables](https://coolify.io/docs/env-variables)
