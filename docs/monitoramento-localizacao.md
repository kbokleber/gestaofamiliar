# Monitoramento de localização — passagem de bastão

Documento autocontido para outra pessoa ou outra IA continuar o Gestão Familiar sem depender de conversa anterior. O estado descrito nas seções 1 a 6 é o do branch `cursor/localizacao-familiar-f740` no commit da API (`1c72c2d`); a seção "Atualização" logo abaixo descreve a etapa seguinte, com a tela do site. Nada disso foi para produção.

## Atualização: tela do site e ajustes de segurança (etapa B)

Depois da revisão do Dev e do QA, o Kleber escolheu seguir neste mesmo branch antes de qualquer merge. Esta etapa acrescentou:

- **Limite de tentativas no pareamento** (`backend/app/services/limite_tentativas.py`): `POST /dispositivos/parear` aceita 10 pedidos por IP e 100 no total a cada 15 minutos; acima disso responde 429. O IP é lido de trás para frente no `X-Forwarded-For`: com Traefik e nginx na frente (`PROXIES_CONFIAVEIS=2`), vale o penúltimo valor, que é o IP que o Traefik viu. O começo do cabeçalho é ignorado porque quem chama pode falsificá-lo. O limite fica na memória do processo da API e zera quando o container reinicia.
- **Prazo do histórico**: `LOCALIZACAO_RETENCAO_DIAS` (padrão 90) para as crianças. Pontos de **adulto** que compartilha a posição ficam no máximo **7 dias** (fixo em `RETENCAO_ADULTO`, igual ao texto de consentimento do app 2.0.5) e são apagados na hora quando ele para de compartilhar ou o celular é revogado. Pontos e avisos de chegada/saída mais antigos são apagados, e códigos de pareamento usados ou vencidos também. A limpeza roda no máximo uma vez por hora, quando chega um ponto novo ou quando um adulto abre o mapa (`limpar_historico_antigo`).
- **Troca de família**: se a criança passar para outra família, o celular antigo é revogado no próximo envio e recebe 401.
- **Apelido no mapa**: tabela nova `location_child_settings` e rota `PUT /criancas/{id}/apelido` (até 12 caracteres). O marcador mostra o apelido (ex.: Gui, Gi); sem apelido, as duas primeiras letras do nome.
- **Tela "Localização"** (`frontend/src/pages/localizacao/`), só para adulto, com Leaflet e OpenStreetMap, carregada sob demanda:
  - Agora: cartão por criança com a frase do lugar, a bateria grande e colorida, há quanto tempo e o mapa com marcadores e os círculos dos lugares. Atualiza a cada minuto.
  - Trajeto: criança e dia; distância, velocidade média e máxima, início e fim, percurso no mapa (tracejado no trecho sem sinal), paradas e chegadas/saídas.
  - Lugares: cadastrar, editar e apagar, com busca de endereço ou clique no mapa, preposição sugerida e raio.
  - Celulares: gerar código de pareamento (com contagem regressiva), apelido no mapa e revogar celular.
- **Menu e permissões**: chave `localizacao` em `frontend/src/lib/menus.ts`, item no menu lateral e rota `/localizacao`. Na tela de usuários, a opção "Localização" aparece para adulto e some para criança.

Continua pendente: o app Android, a notificação push de chegada/saída e o teste com um celular de verdade.

## Atualização: app Android da criança (etapa C)

O app está em `mobile/android-crianca/` (Kotlin, Android 8+), com README de instalação e de compilação. Ele pareia com o código gerado em Localização › Celulares, roda um serviço em primeiro plano com notificação fixa, pede a posição a cada ~5 minutos e envia latitude, longitude, precisão, velocidade, bateria e horário. Sem rede, guarda os pontos numa fila de até uma semana. Volta sozinho quando o celular liga. Quando um adulto revoga o celular no site, o app apaga o token e para. Não há áudio, tempo de tela nem botão de desligar no celular.

A chave de assinatura do APK fica fora do git (`keystore.properties`, ignorado). Atualizações precisam ser assinadas com a mesma chave.

Continua pendente: teste num celular de verdade, notificação push de chegada/saída e a otimização de bateria própria de alguns fabricantes.

## Atualização: lembretes de Estudos pelo app (etapa D)

- Tabela nova `app_aviso`: avisos esperando o app da criança. Um aviso novo do mesmo tipo substitui o pendente; validade de 6 h; limpeza após 7 dias.
- `POST /localizacao/dispositivos/posicao` passa a devolver `avisos` (id, tipo, titulo, texto, url). Cada aviso é entregue uma vez.
- `services/lembrete.py`: se o filho tem celular pareado e não revogado, o lembrete vai para `app_aviso` em vez do Web Push do navegador. Sem app, segue o Web Push de antes. O disparo de teste informa o canal (`app` ou `navegador`).
- App 1.0.2 mostra os avisos no canal de notificação "Lembretes" (com som) e abre a página de atividades ao tocar.
- Entrega com confirmação: o aviso volta em toda resposta até o app confirmar (`avisos_recebidos` no envio seguinte) ou vencer. Resposta perdida não apaga o lembrete; o app não toca de novo um aviso que já mostrou.
- O canal "app" só é usado se o celular tem o app 1.0.2+ (`app_versao` >= 3), notificações liberadas (`notificacoes`) e mandou posição nos últimos 30 minutos. Colunas novas em `location_device`: `app_versao` e `notificacoes_ativas` (ALTER na subida da API). Senão, vai pelo navegador.
- Validade do lembrete: até as 21h do dia (fim da janela); disparo de teste fora da janela vale 1 hora.

## Atualização: app 2.0 para adultos e crianças, alertas e publicação automática (etapa E)

- **App 2.0.0** (`mobile/android-crianca`, versionCode 4): o site inteiro dentro do app (WebView), com login, envio e download de arquivos, botão voltar e faixa de versão nova. O código de pareamento continua como alternativa na tela de Configurações.
- **Criança logada conecta o celular sozinha**: `POST /api/v1/localizacao/dispositivos/parear-me` (login da criança; adulto recebe 403). Com `token_anterior`, o pareamento anterior do mesmo celular é revogado (troca de criança sem gerar alerta de "sem sinal").
- **Celular do adulto** (tabela `app_dispositivo_adulto`): `POST /api/v1/app-android/dispositivos/registrar` (login de adulto; criança recebe 403), `POST /dispositivos/avisos` (X-Device-Token; devolve e confirma alertas) e `POST /dispositivos/revogar-me`. O celular do adulto nunca envia localização. Se o usuário deixar de ser adulto ativo da família, o token é revogado na chamada seguinte.
- **Alertas para adultos** (`backend/app/services/alertas_adultos.py`), só para adultos com o app e acesso ao menu Localização: chegada/saída de lugar (pontos com mais de 1 hora da fila offline não alertam), bateria em 15% ou menos (um alerta por descarga) e sem localização há 30 minutos (um alerta por ausência, verificado a cada ~1 minuto no ciclo de lembretes; coluna nova `location_device.alerta_sem_sinal_em`). Os alertas usam a mesma fila `app_aviso`, com validade de 3 horas.
- **Token de publicação do APK** (tabela `app_publicacao_token`): admin gera, vê uma vez, revoga em Localização › Celulares. `POST /api/v1/app-android/publicar` com `X-App-Publish-Token` publica sem login e sem redeploy.
- **Site**: `frontend/src/lib/appNativo.ts` informa o login ao app e salva downloads pelo app; dentro do app, o botão de Web Push dos lembretes some (o app já notifica).

## Atualização: app 2.0.1 e 2.0.2

- **2.0.1**: login pelo Google funciona no app. O Google não deixa entrar dentro de WebView; o app abre o mesmo pedido de login no navegador (`kc_idp_hint`) e o Keycloak devolve para `/app-login`, link verificado por `frontend/public/.well-known/assetlinks.json` (com botão "Voltar ao app" se o navegador não abrir o app). No app, a sessão do Keycloak fica guardada para não pedir login a cada abertura.
- **2.0.2**: ícone novo (casa, família e coração) no site (favicon, PWA, apple-touch) e no app (ícone adaptativo, com tema e notificação); lembretes vibram (canal novo `lembretes_vibrar`); confirmação antes de uma criança transformar o celular de um adulto no dela; o servidor recusa APK com outra assinatura (`backend/app/services/apk_assinatura.py`, `APP_ASSINATURA_SHA256`) e versão mais antiga que a publicada.

O Find My Kids serviu só de referência de recursos que a família quer enxergar: mapa em tempo quase real, trajetos com velocidade, bateria do celular e lugares com aviso de chegada e saída. Não existe integração, conta, SDK, chave nem qualquer ligação com o Find My Kids.

## 1. Objetivo

Monitorar a localização e a bateria dos celulares das crianças dentro do Gestão Familiar, da KBO Soluções Tecnológicas (sempre "KBO Soluções", nunca só "KBO").

- O adulto usa só o navegador, no site já existente: `https://gestaofamiliar.kbosolucoes.com.br`, com a API em `/api/v1`.
- A criança usa um app Android enxuto, só para parear o aparelho e enviar localização e bateria. Sem áudio, sem tempo de tela, sem mais nada.
- Cada criança marcada como criança aparece no mapa. Adulto não é monitorado e não aparece.
- O adulto cadastra lugares da família (Casa, Escola e outros), com nome, ponto ou endereço e raio. No mapa e na lista, a frase deve ser simples: "Guilherme está em Casa", "Giovana está na Escola" ou "fora dos lugares cadastrados", junto com a porcentagem de bateria bem visível.
- O adulto filtra o trajeto de um dia: desenho do percurso, início, fim, paradas, velocidade média e máxima em km/h e quilometragem.
- O isolamento é por `family_id`. O menu novo só aparece para adulto.

## 2. Decisão já tomada: quem é criança

Usar o campo `auth_user.is_child`, que já existe. Guilherme e Giovana são usuários com `is_child=true`.

Não usar `healthcare_familymember`. Aquela tabela é ficha de saúde (consulta, remédio, documento), sem login e sem celular. O pareamento precisa de um usuário da família.

Adulto é `is_child=false`. A listagem da API filtra `is_child=true` e `is_active=true` e a família do adulto. Um adulto da mesma família não entra na lista e não aceita código de pareamento.

O menu `localizacao` é só de adulto. No backend, criança recebe 403 com a mensagem "Localização é só para adultos.", mesmo que `allowed_menus` seja nulo (nulo hoje significa "todos os menus") ou que a chave esteja na lista. Ao criar ou salvar permissão de uma criança, a chave `localizacao` é removida da lista.

## 3. O que foi feito

O desenvolvimento parou a pedido do Kleber antes da tela e do app. A API está implementada e coberta por teste. A interface e o Android não foram começados.

Não há nada quebrado conhecido no que entrou neste branch. Os testes novos e um grupo de testes antigos vizinhos passaram neste ambiente (32 testes, incluindo os 7 de localização). A suíte inteira não foi executada aqui porque faltam dependências que o restante do backend já pedia antes desta mudança (por exemplo o pacote `openai` ao importar o módulo de Telegram). O frontend não foi alterado, então o build do React não muda com este branch.

### 3.1 Completo: API

Contrato base: prefixo `/api/v1/localizacao`.

Rotas do adulto (JWT já usado pelo site, menu `localizacao`, e o usuário não pode ser criança):

| Método | Caminho | Função |
| --- | --- | --- |
| GET | `/criancas` | Uma entrada por criança da família: nome, última posição, precisão, velocidade em km/h se o GPS mandou, bateria, `ha_segundos`, frase do lugar e a lista de aparelhos com a bateria de cada um |
| GET | `/criancas/{id}/trajeto?dia=AAAA-MM-DD` | Trajeto daquele dia no fuso `America/Sao_Paulo`. Se `dia` vier vazio, usa hoje nesse fuso |
| POST | `/pareamentos` | Corpo `{"child_user_id": 16}`. Devolve o código em claro uma única vez, no formato `XXXX-XXXX`, válido por 15 minutos |
| POST | `/dispositivos/{id}/revogar` | Revoga o celular. O token deixa de enviar |
| GET | `/lugares` | Lugares da família |
| POST | `/lugares` | Cria lugar. Corpo: `nome`, `preposicao` (`em`, `na` ou `no`), `endereco` opcional, `latitude`, `longitude`, `raio_m` (30 a 2000, padrão 150), `family_id` opcional |
| PUT | `/lugares/{id}` | Atualiza o lugar. A frase da criança muda na hora; o histórico de chegada/saída guarda o nome antigo |
| DELETE | `/lugares/{id}` | Apaga o lugar. O evento antigo continua com o nome copiado |
| POST | `/lugares/geocodificar` | Corpo `{"endereco": "..."}`. Consulta o Nominatim (OpenStreetMap), sem chave. Primeiro restringe ao Brasil; se não achar, tenta de novo sem país |

Rotas do celular. Não usam o login do site. O token vai no header `X-Device-Token` e só serve para estas duas últimas rotas:

| Método | Caminho | Função |
| --- | --- | --- |
| POST | `/dispositivos/parear` | Corpo `code` e `device_label` opcional. Troca o código por `device_token` em claro, devolvido uma vez |
| POST | `/dispositivos/posicao` | Corpo `latitude`, `longitude`, e opcionais `accuracy_m`, `speed_mps` (metros por segundo), `battery_level` (0 a 100), `recorded_at` |
| POST | `/dispositivos/revogar-me` | O próprio celular revoga o token |

Regras já codificadas:

- Código e token são guardados só como SHA-256. Não há segredo fixo no código.
- Código de uso único. Código vencido ou repetido responde 400.
- Posição no futuro (mais de 5 minutos) ou com mais de 7 dias é recusada.
- O mesmo aparelho reenviando o mesmo `recorded_at` (tolerância de 1 segundo) não duplica o ponto. A resposta traz `repetido: true`.
- Velocidade absurda (fora de 0 a 70 m/s) ou precisão absurda é ignorada e o ponto ainda é gravado.
- Frase quando não há lugar: "Nenhum lugar cadastrado".
- Frase sem ponto ainda: "Guilherme ainda não enviou localização".
- Frase fora de todos os raios: "Guilherme está fora dos lugares cadastrados".
- Frase dentro: "Guilherme está em Casa" ou "Giovana está na Escola". Se o ponto cair em mais de um raio, vale o raio menor.
- Sugestão de preposição, se a tela quiser usar: nome começando por Escola, Praça, Faculdade, Igreja ou Academia sugere `na`; Colégio, Parque, Clube ou Curso sugere `no`; o resto sugere `em`. A sugestão não é obrigatória. Quem grava o lugar escolhe `em`, `na` ou `no`.
- Chegada e saída só nascem na mudança de estado. O primeiro ponto só grava "está dentro" ou "está fora" e não gera evento, para o pareamento não fingir uma chegada. Eventos: "Chegou em Casa", "Saiu de Casa", "Chegou na Escola", "Saiu da Escola" (`em`/`de`, `na`/`da`, `no`/`do`).
- Trajeto: soma haversine dos trechos. Trecho com intervalo maior que 30 minutos, ou velocidade implícita acima de 70 m/s, vira lacuna (`lacuna_antes: true`) e não entra na quilometragem. Parada: dois ou mais pontos dentro de 80 m por pelo menos 5 minutos. Velocidade média é a distância dividida pelo tempo em movimento, fora das paradas. Velocidade máxima usa o `speed_mps` do GPS quando ele veio válido; senão, a velocidade entre os pontos. O campo `fonte_velocidade` fica `gps`, `pontos`, `mista` ou `sem_dados`.
- Família errada devolve 404 na criança, no trajeto, no lugar e no aparelho. Criança não lê a API do adulto. Token revogado recebe 401.

Tabelas novas, criadas pelos modelos. Nenhuma coluna foi acrescentada em tabela antiga:

- `location_pairing_code`
- `location_device`
- `location_point` (lat, lon, `accuracy_m`, `speed_mps`, `battery_level`, `recorded_at`, `received_at`)
- `location_place`
- `location_place_state` (última situação dentro/fora, para detectar a transição)
- `location_place_event` (chegada ou saída, com o nome do lugar copiado)

### 3.2 Arquivo por arquivo

Completos, no sentido de API pronta e testada:

- `backend/app/models/location.py` — os seis modelos acima.
- `backend/app/models/__init__.py` — registra esses modelos. O `create_all` que a API já roda na subida passa a enxergar as tabelas novas.
- `backend/app/schemas/location.py` — entrada e saída das rotas.
- `backend/app/services/localizacao.py` — pareamento, posição, lugares, frase, trajeto, geocodificação.
- `backend/app/api/v1/endpoints/localizacao.py` — rotas da tabela acima.
- `backend/app/api/v1/api.py` — inclui o router em `/localizacao`, sem trancar o router inteiro no menu, porque o celular não tem login de adulto.
- `backend/app/core/menus.py` — `localizacao` entrou em `MENU_KEYS`. `MENUS_SO_ADULTO` e `aplicar_perfil_menus` tiram esse menu da criança.
- `backend/app/api/deps.py` — `require_menu("localizacao")` recusa criança antes da regra de superusuário.
- `backend/app/api/v1/endpoints/users.py` — ao criar usuário ou salvar permissões, remove `localizacao` se a pessoa for criança.
- `backend/app/core/config.py` — `NOMINATIM_URL` e `NOMINATIM_USER_AGENT`, com padrão público e sem chave. Não são obrigatórios.
- `backend/scripts/migrate_location_tables.py` — script idempotente que chama `create_all` só destas tabelas. Não apaga dado. Não foi executado.
- `backend/tests/test_localizacao.py` — 7 testes em SQLite de memória. Cobrem frase da Casa e da Escola, bateria, trajeto (distância, média, máxima, parada, evento), isolamento de família, criança bloqueada, código vencido, revogação e geocodificação com a consulta externa simulada.

Parciais, de propósito, porque a tela e o app não existem:

- A bateria, a frase do lugar e o trajeto existem no JSON. Ninguém vê isso no navegador.
- O desenho do percurso, o filtro por dia na tela, o círculo do lugar e a porcentagem grande no mapa não existem.
- A geocodificação está na API e no teste com resposta falsa. Não houve chamada real ao Nominatim neste trabalho.
- O aviso de chegada e saída fica gravado e volta no trajeto do dia. Notificação push não foi feita e continua pendente.
- O script de migração existe e não rodou em banco nenhum.

Não começados:

- Nenhuma tela React. `frontend/src/lib/menus.ts` ainda não tem a chave `localizacao`. O menu lateral (`frontend/src/components/Layout.tsx`) e as rotas (`frontend/src/App.tsx`) não têm "Localização". A página de usuários continua igual: o checkbox "Filho" já marca `is_child`, e isso basta para a API, mas o texto da tela ainda não explica o mapa.
- (Resolvido na etapa C) O app Android foi criado depois em `mobile/android-crianca/`.
- Nenhum arquivo de segredo, token ou senha foi adicionado.

## 4. O que está em andamento

O pull request deste branch é um rascunho para o Kleber revisar. O desenvolvimento parou aqui de propósito, para outra IA continuar. Não houve merge e não houve deploy.

## 5. O que falta

Continuar em cima desta API. Não recriar tabelas, rotas ou a regra do `is_child`, a menos que um teste quebre.

Ainda falta, e é o miolo que o adulto precisa ver:

- Lugares cadastrados na tela, com status por filho em palavras. A API já devolve a frase em `GET /criancas`, no objeto `status.frase`, e já grava Casa/Escola em `/lugares`. Falta a tela: formulário com nome, preposição (`em`/`na`/`no`), endereço com o botão que chama `/lugares/geocodificar` ou um clique no mapa, e raio. No mapa e na lista, mostrar a frase inteira ("Guilherme está em Casa", "Giovana está na Escola", "Guilherme está fora dos lugares cadastrados") e o círculo do raio. Biblioteca sugerida, e ainda não instalada no projeto: Leaflet com OpenStreetMap, sem chave paga. O projeto não usa outro mapa hoje.
- Bateria bem visível. A API já manda `bateria` na criança e `bateria` em cada item de `aparelhos`. Falta o número grande no cartão e no marcador, com cor de alerta quando estiver baixa. O adulto não instala app.
- Histórico de trajetos com velocidade e quilometragem. A API já responde `distancia_km`, `velocidade_media_kmh`, `velocidade_maxima_kmh`, `inicio`, `fim`, `paradas`, `pontos` (com `lacuna_antes` para o trecho sem sinal) e `eventos`. Falta a tela: seletor de dia, linha do percurso, linha tracejada na lacuna, paradas e a lista "Chegou em Casa" / "Saiu da Escola".
- Menu "Localização" só para adulto. Incluir a chave em `frontend/src/lib/menus.ts` com o mesmo nome `localizacao`, esconder se `is_child` for verdadeiro, colocar o item no `Layout.tsx` e a rota em `App.tsx`. Sem isso, o adulto não acha a função, mesmo a API estando pronta. Quem não é superusuário e tem `allowed_menus` preenchido só entra na API se a lista tiver `localizacao`. Superusuário e quem tem `allowed_menus` nulo já passam, desde que não sejam criança.
- App Android separado e enxuto, pasta sugerida `mobile/android-crianca/`, Kotlin nativo. Tela de pareamento: endereço do site (produção `https://gestaofamiliar.kbosolucoes.com.br`, a API é `/api/v1`) e o código. Depois, serviço em primeiro plano com notificação persistente, permissão de localização em segundo plano, intervalo em torno de 5 minutos, envio de `latitude`, `longitude`, `accuracy_m`, `speed_mps` quando o GPS tiver, `battery_level` e `recorded_at`. Se a rede cair, guardar o último ponto e reenviar. Sem áudio e sem tempo de tela. README com o passo a passo de compilar e instalar o APK. O token fica só no aparelho, nunca no git.
- Notificação push de chegada e saída. Os eventos já existem. O push fica para depois.
- Fila offline maior do que um ponto, retenção do histórico, limite de tentativas do código de pareamento, teste do APK num celular de verdade e o cuidado de uso do Nominatim e dos tiles do OpenStreetMap se o tráfego crescer.

### Como testar agora

Na pasta `backend`, com um `DATABASE_URL` e um `SECRET_KEY` fictícios. O import do projeto cria um engine na hora, mas os testes de localização usam SQLite na memória e não precisam do banco real. Não aponte `DATABASE_URL` para produção e não rode o script de migração contra produção.

```bash
cd backend
python -m pytest tests/test_localizacao.py -q
```

Os 7 testes desse arquivo passaram neste ambiente, junto com `test_visibilidade_filho.py`, `test_apontamentos.py`, `test_version.py`, `test_receipt_dates.py`, `test_recurrence_generation.py` e `test_category_matching.py`.

Não há tela para abrir no navegador. Não há APK para compilar, porque a pasta do app não existe.

### O que o deploy exigiria, quando o Kleber autorizar

Não fazer esse deploy agora.

- Não há variável nova obrigatória. Não há senha nem token para configurar.
- Opcionais, só se um dia a busca de endereço mudar de servidor: `NOMINATIM_URL` e `NOMINATIM_USER_AGENT`. O padrão já aponta para o Nominatim público e um identificador do sistema, sem chave.
- Migração: as tabelas são novas. O jeito do projeto é o `Base.metadata.create_all` na subida da API (`backend/app/main.py`), que passa a incluí-las porque os modelos estão em `app.models`. Também dá para rodar antes, de propósito, `python scripts/migrate_location_tables.py` dentro de `backend/`, com o `DATABASE_URL` do ambiente escolhido. O script não apaga dados. Ele não foi executado. Não usar o banco de produção sem o ok do Kleber.
- Cuidado: quando este código subir de verdade, a subida da API tenta criar as tabelas. Por isso o merge e o deploy esperam o Kleber.
- O frontend deste branch não mudou. Um deploy só do backend ainda não mostra mapa.
- Nenhum servidor foi alterado.

## 6. Regras do projeto

- O Kleber revisa os pull requests e dá o ok antes de qualquer merge.
- Quem desenvolve não faz merge, não faz deploy em produção e não altera servidores sem aprovação explícita dele.
- Senhas e tokens nunca vão para o chat, para o código ou para commits. Código de pareamento e token de celular são gerados na hora e só o hash fica no banco.
- Mudanças de infraestrutura e deploys ficam com a equipe de infraestrutura (bot Infra Estrutura).
- O projeto é da KBO Soluções Tecnológicas, chamada sempre de "KBO Soluções" e nunca só de "KBO".
- A comunicação é sempre em português.

## Avós (só compartilham) e SOS

- **Só compartilhar** (`allowed_menus` com `compartilhar_localizacao`, sem `localizacao`): o adulto (ex.: avô ou avó) pareia pelo app e envia a própria posição, aparece no mapa de quem tem Localização, mas **não vê ninguém**: toda rota de leitura de localização e de SOS responde 403 para ele. Ele não recebe alertas nem SOS de outros. No site, só tem a tela "Minha localização" (`/minha-localizacao`).
- **SOS** (`POST /api/v1/localizacao/dispositivos/sos`, com o token do celular): o app só envia depois de **segurar 3 s** e de uma **contagem de 5 s com Cancelar**. O servidor guarda o pedido (`location_sos`) com nome, posição do momento ou a última conhecida, horário e bateria, e avisa **só os familiares escolhidos** (`location_sos_destinatario`, configurável em Localização › Celulares; só adultos que veem o mapa). Sem nenhum escolhido, avisa todos os adultos que veem o mapa. Quem pediu nunca recebe o próprio aviso. Canal: a fila de avisos do app e o Web Push do navegador (sem Firebase). Repetição em menos de 2 min devolve o mesmo pedido, sem novo aviso (a linha do celular é travada até gravar), e há teto de 10 SOS por família por hora (429). Um horário enviado no futuro ou antigo demais não recusa o SOS: a posição enviada é descartada e vale a última conhecida. Quem foi avisado fica gravado (`location_sos_avisado`): **só essas pessoas** listam o SOS (`GET /sos`, com posição) e marcam "Visto"; os outros adultos não veem. No mapa, a faixa vermelha e o selo SOS ficam até alguém avisado tocar em "Visto". **Prazo:** posição e bateria do SOS são apagadas em 7 dias e o pedido inteiro em 30 dias (`limpar_historico_antigo`); quando o adulto para de compartilhar ou é revogado, a posição dos SOS dele é apagada na hora. O texto de consentimento do app cita esses prazos. Quando o SOS falha ou ninguém é avisado, o app mostra 190, 192 e 193.
