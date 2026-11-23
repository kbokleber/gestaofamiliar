# Monitoramento de erros (GlitchTip), sem dados pessoais

Backend e site mandam erros para logs.kbosolucoes.com.br. Sem desempenho (tracing), sessão, replay, log ou métrica.

## Regra

O filtro **remonta** o evento só com a lista permitida. O que não está na lista não sai, inclusive campos novos do SDK.
Se o filtro falhar, o evento é descartado. O transporte só deixa passar envelope de erro, sem o cabeçalho de rastreio.

## O que sai

- id, hora, nível, plataforma, ambiente e versão (`gf-backend@<commit>`, `gf-site@<versão>`)
- tipo do erro e onde ele passou: arquivo, função, linha (e coluna no site)
- backend: nome da função da rota, método HTTP e nome do logger
- site: só arquivos compilados do próprio site; qualquer outra origem vira `[pagina]`

## O que é removido

- **texto do erro e do log** (vira `[texto removido]`): pode trazer nome, coordenada ou os valores de um INSERT
- URL, parâmetros, cabeçalhos (Authorization, X-Device-Token, X-API-Token, cookies, User-Agent, Referer), corpo, IP e dados do servidor
- usuário (id, nome, e-mail, IP), etiquetas, extras, contextos (aparelho, navegador, fuso, componentes React)
- variáveis locais, trechos de código, argumentos, caminhos absolutos, nome da máquina, módulos instalados
- histórico de cliques, chamadas e logs (breadcrumbs), threads, impressões digitais, anexos
- cabeçalho de rastreio do envelope (pode carregar o `baggage` de quem chamou)

## Variáveis

| Variável | Onde | Vazia |
|---|---|---|
| `GF_SENTRY_DSN_BACKEND` | backend, ao rodar | desligado, SDK nem importado |
| `GF_SENTRY_ENVIRONMENT` | backend, ao rodar (padrão `production`) | - |
| `GF_SENTRY_DSN_SITE` | **compilação** do site (vira `VITE_GF_SENTRY_DSN_SITE`) | desligado, SDK nem entra no site |

## Limite conhecido

O filtro controla o conteúdo. A conexão do navegador com o GlitchTip sempre mostra IP e User-Agent ao servidor:
o projeto do GlitchTip e o proxy precisam estar configurados para não guardar. O SDK pede `infer_ip: never`.

## Testes

- `backend/tests/test_monitoramento.py`: GlitchTip falso recebe os bytes reais
- `cd frontend && npx esbuild tests/monitoramento.test.ts --bundle --platform=node --format=esm --log-level=error | node --input-type=module -`
