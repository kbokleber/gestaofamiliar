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

- **texto do erro e do log** (vira `[texto removido]`): pode trazer nome, coordenada ou os valores de um INSERT.
  Única exceção: a mensagem fixa do erro de teste, comparada letra por letra (veja "Teste em produção")
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
| `GF_SENTRY_TESTE` | backend, ao rodar. Só o valor `1` cria a rota de teste | a rota não existe (404) |
| `GF_SENTRY_DSN_SITE` | **compilação** do site (vira `VITE_GF_SENTRY_DSN_SITE`) | desligado, SDK nem entra no site |

## Limite conhecido

O filtro controla o conteúdo. A conexão do navegador com o GlitchTip sempre mostra IP e User-Agent ao servidor:
o projeto do GlitchTip e o proxy precisam estar configurados para não guardar. O SDK pede `infer_ip: never`.

## Teste em produção

Prova que um erro do próprio app chega ao GlitchTip. Mensagem fixa: `TESTE-GLITCHTIP (pode ignorar)`.

1. No Coolify, ponha `GF_SENTRY_TESTE=1` no backend e publique de novo.
2. Um administrador logado (superuser) abre `/admin/teste-glitchtip` (sem link no menu) e toca em **Gerar erro no site** e
   **Gerar erro no backend**. Repetir na mesma página não manda de novo o erro do site (o SDK descarta igual seguido):
   recarregue antes.
   Só o backend, sem o site: `POST /api/v1/system/teste-glitchtip` com `X-API-Token` de um superuser. Resposta esperada: 500.
   `GET` no mesmo endereço só diz se está ligado e qual o commit; não gera erro. Sem login 401, não administrador 403,
   variável desligada 404.
3. No GlitchTip, um evento em cada projeto:
   - backend: `ErroDeTesteGlitchTip`, release `gf-backend@<commit>`, environment de `GF_SENTRY_ENVIRONMENT`
     (pode vir um `ExceptionGroup` antes: é o middleware de log embrulhando o erro)
   - site: `ErroDeTesteGlitchTip`, release `gf-site@<versão>`, environment `production`
   - IP do usuário vazio ou zerado. User-Agent só no site (cabeçalho da conexão, aceito na opção A); o do backend é
     `sentry.python/<versão>`. Nenhum dos dois vai no conteúdo do evento.

Desligar: apague `GF_SENTRY_TESTE` e publique de novo o backend (a rota volta a dar 404).
Remover o código: `git revert` do commit que criou este teste e nova publicação.

## Testes

- `backend/tests/test_monitoramento.py`: GlitchTip falso recebe os bytes reais
- `backend/tests/test_teste_glitchtip.py`: rota de teste no app de verdade
- `cd frontend && npx esbuild tests/monitoramento.test.ts --bundle --platform=node --format=esm --log-level=error | node --input-type=module -`
