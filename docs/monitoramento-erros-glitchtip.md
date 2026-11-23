# Monitoramento de erros (GlitchTip), sem dados pessoais

Backend e site mandam erros para logs.kbosolucoes.com.br. Sem desempenho (tracing), sessão, replay, log ou métrica.

## Regra

O filtro **remonta** o evento só com a lista permitida. O que não está na lista não sai, inclusive campos novos do SDK.
Se o filtro falhar, o evento é descartado. O transporte só deixa passar envelope de erro, sem o cabeçalho de rastreio.

## O que sai

- id, hora, nível, plataforma, ambiente e versão (`gf-backend@<commit>`, `gf-site@<versão>`)
- backend: tipo do erro, módulo, arquivo, função, linha, função da rota, método HTTP e logger
- site: tipo do erro (lista fixa), arquivo, linha e coluna. **Sem nome de função**
- etiqueta `causas_cortadas`, quando a cadeia tem mais de 10 exceções: só a quantidade; ficam as 10 da ponta

## Um nome só sai se existir de verdade

Uma palavra como "Guilhermina" tem formato de nome, então o formato não basta.

- **Backend:** módulo e logger precisam ser um módulo carregado; a classe do erro precisa existir no módulo; função e
  arquivo precisam ser do módulo. Nome criado na hora (classe, logger, função, `exec`) não sai. Ambiente e versão são
  os configurados ao ligar, não os do evento. Hora só em ISO UTC.
- **Site:** o arquivo precisa ser do mesmo domínio, da pasta `/assets/` no formato do Vite (ou `sw.js`, `push-sw.js`,
  `workbox-*.js`) **e** ter sido carregado pela página. Outro domínio, caminho ou página vira `[pagina]`.
  Tipo fora da lista vira `Erro`. Hora só a menos de 2 dias de agora.
- **Pilha do site:** o navegador copia a mensagem para a pilha. Se a mensagem, o nome ou qualquer causa tiver quebra de
  linha, ou se a pilha não começar pela mensagem, o evento sai sem nenhum quadro.

## O que é removido

- **texto do erro e do log** (vira `[texto removido]`): pode trazer nome, coordenada ou os valores de um INSERT
- URL, parâmetros, cabeçalhos (Authorization, X-Device-Token, X-API-Token, cookies, User-Agent, Referer), corpo, IP e dados do servidor
- usuário (id, nome, e-mail, IP), etiquetas, extras, contextos (aparelho, navegador, fuso, componentes React)
- nome de função no site, variáveis locais, trechos de código, argumentos, caminhos absolutos, nome da máquina, módulos instalados
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
