# Configuração: Telegram + IA

## Telegram (bot)

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `TELEGRAM_BOT_TOKEN` | Sim (para usar Telegram) | Token do bot obtido com [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_WEBHOOK_SECRET` | Não | Segredo para validar requisições do webhook |

## IA para respostas inteligentes

A IA interpreta o que o usuário escreve no Telegram e chama automaticamente as ferramentas do sistema (equipamentos, dashboard, consultas, medicações, etc.).

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `TELEGRAM_AI_ENABLED` | `true` | Ativar uso de IA para interpretar mensagens |
| `TELEGRAM_AI_PROVIDER` | `openai` | `openai`, `azure` ou `none` (desliga a IA) |

### OpenAI

| Variável | Descrição |
|----------|-----------|
| `OPENAI_API_KEY` | Chave da API OpenAI |
| `OPENAI_MODEL` | Modelo, ex: `gpt-4o-mini`, `gpt-4o` |

### Azure OpenAI

| Variável | Descrição |
|----------|-----------|
| `AZURE_OPENAI_ENDPOINT` | URL do recurso, ex: `https://seu-recurso.openai.azure.com` |
| `AZURE_OPENAI_API_KEY` | Chave da API |
| `AZURE_OPENAI_DEPLOYMENT` | Nome do deployment (ex: `gpt-4o`) |

## Exemplo no `.env`

```env
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_SECRET=meu-segredo-opcional

# IA (OpenAI)
TELEGRAM_AI_ENABLED=true
TELEGRAM_AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# OU IA (Azure)
# TELEGRAM_AI_PROVIDER=azure
# AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

## Desativar a IA

- `TELEGRAM_AI_ENABLED=false`, ou  
- `TELEGRAM_AI_PROVIDER=none`  

O bot continuará funcionando com comandos fixos; apenas as respostas “inteligentes” ficarão desativadas.
