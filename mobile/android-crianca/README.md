# App Android — Gestão Familiar

Desde a versão 2.0.0 o app é o **site do Gestão Familiar dentro do app**, com o mesmo login e as mesmas funções para adultos e crianças, mais o que o navegador não faz sozinho:

- **Criança logada**: o celular se conecta sozinho à família (sem código) e envia **localização e bateria** a cada ~5 minutos. Lembretes chegam como notificação com som.
- **Adulto logado**: o celular dele **nunca envia localização**. Recebe como notificação: chegada e saída dos lugares, bateria da criança em 15% ou menos e celular da criança sem enviar localização há 30 minutos.
- Envio de arquivos (fotos, PDFs), download de arquivos gerados pelo site (vão para Downloads), botão voltar e faixa de "nova versão" quando há APK mais novo em `/app`.

Não grava áudio, não vê a tela, fotos ou mensagens, e não controla tempo de tela.

- Pacote: `br.com.kbosolucoes.gestaofamiliar.crianca` (mantido para atualizar por cima das versões 1.x)
- Android 8.0 (API 26) ou mais novo
- API usada pelo nativo: `/api/v1/localizacao/dispositivos/{parear,parear-me,posicao}`, `/api/v1/app-android/dispositivos/{registrar,avisos,revogar-me}` e `/api/v1/app-android/ultima`

## Instalar

1. No celular, abra `https://gestaofamiliar.kbosolucoes.com.br/app` (ou o QR code em Localização › Celulares) e toque em **Baixar o app**.
2. Abra o arquivo. Se o Android pedir, permita "instalar apps desta fonte".
3. Abra o app **Gestão Familiar** e entre com a conta de quem usa o celular.
   - **Celular da criança**: entre com a conta dela. O app conecta o celular e abre a lista de permissões (passo 4).
   - **Celular do adulto**: entre com a sua conta e permita as notificações.
4. No celular da criança, complete a lista até tudo ficar com ✓ (se fechar, toque na faixa amarela no topo ou segure o ícone do app › Configurações).

Alternativa sem o login da criança: segure o ícone do app › **Configurações**, digite o código gerado em **Localização › Celulares › Gerar código** e toque em **Conectar à família**. O código vale 15 minutos e serve uma vez só.

Login pelo Google: o Google não deixa entrar dentro de apps. Ao tocar em "Google" na tela de login, o app abre o navegador do celular direto no Google; ao terminar, o navegador volta ao app por `https://gestaofamiliar.kbosolucoes.com.br/app-login` (link verificado por `/.well-known/assetlinks.json`; se o celular não abrir o app sozinho, a página mostra o botão "Voltar ao app"). Usuário e senha continuam dentro do app. O app guarda a sessão do Keycloak na área privada dele, para não pedir login toda vez que abre.

Regras do login no app:
- Um adulto que entra no celular da criança (ex.: para conferir algo) não muda nada: o celular continua enviando a localização da criança.
- Se outra criança entra no mesmo celular, ele passa a enviar a localização dela e o pareamento anterior é revogado.
- Sair do site não desliga nada: a criança continua conectada e o adulto continua recebendo alertas. Para desligar, revogue no site.

A lista de permissões da criança (complete até tudo ficar com ✓):
- **Localização**: Permitir, com "Localização precisa".
- **Notificação fixa** (Android 13+): Permitir.
- **Localização o tempo todo**: na tela que abrir, escolha **Permitir o tempo todo**.
- **Sem economia de bateria**: Permitir.

Depois, toque em **Enviar agora**. Em alguns segundos a criança aparece no mapa do site.

Alguns fabricantes (Xiaomi, Samsung, Motorola, Huawei) têm uma economia de bateria própria, além da do Android. Se o envio parar com a tela desligada, procure nas configurações do celular por "Inicialização automática" ou "Apps em segundo plano" e libere o Gestão Familiar.

## Como funciona

- **Serviço em primeiro plano** com notificação fixa ("Localização compartilhada com a família"). A notificação é obrigatória no Android e deixa claro, para a criança, que o compartilhamento está ligado.
- **Intervalo**: pede posição a cada 5 minutos (no mínimo 2), pelo provedor de localização do Google Play Services.
- **Sem internet**: os pontos ficam numa fila no próprio celular (até uma semana) e são enviados na ordem quando a conexão volta. O servidor recusa pontos com mais de 7 dias. O envio acontece fora da trava da fila: com rede lenta, a posição nova e a tela do app não ficam esperando.
- **Ao ligar o celular** ou atualizar o app, o envio volta sozinho (precisa de "Permitir o tempo todo").
- **Lembretes de atividades**: o servidor não manda push direto ao celular. Os avisos pendentes voltam na resposta de cada envio de localização, e o app os mostra como notificação com som no canal "Lembretes". Por isso o lembrete chega em até ~5 minutos depois de disparado. Tocar na notificação abre a página de atividades pendentes no site (só caminhos do próprio site). O app confirma no envio seguinte os avisos que mostrou, e o servidor reenvia até a confirmação (sem tocar duas vezes). O lembrete só vai pelo app quando ele está ativo (versão 1.0.2+, notificações liberadas e posição enviada nos últimos 30 minutos); senão, segue pelo navegador.
- **Revogação**: quando um adulto revoga o celular no site, o próximo envio recebe 401. O app apaga o token e a fila, para de enviar e avisa para parear de novo. O app não tem botão de desligar: quem desliga é o adulto, pelo site.
- **Alertas do adulto**: o celular do adulto busca os alertas a cada ~15 minutos em segundo plano (o menor intervalo que o Android permite sem serviço fixo) e na hora em que o app é aberto. Alertas usam o canal "Alertas da família"; lembretes, o canal "Lembretes". O servidor reenvia até o app confirmar.
- **Ponte com o site**: o site detecta o app pelo user agent (`GestaoFamiliarApp/<versão>`) e fala com ele por `window.GFAppNativo` (`sessao` e `salvarArquivo`). A ponte só atende páginas do próprio site; links de outros endereços abrem fora do app (o login em `auth.kbosolucoes.com.br` abre dentro).
- **Token**: fica só na área privada do app, fora do backup na nuvem e da transferência para outro celular.

Limites conhecidos: a criança ainda pode forçar a parada ou desinstalar o app. O mapa do site mostra "há X min" para deixar visível quando o celular parou de enviar.

## Compilar

Requisitos: JDK 17 e Android SDK (platform 34, build-tools 34).

```bash
cd mobile/android-crianca
echo "sdk.dir=/caminho/do/android-sdk" > local.properties
./gradlew testDebugUnitTest assembleDebug   # APK de teste: app/build/outputs/apk/debug/
```

### APK assinado (para instalar e atualizar)

A chave de assinatura **não fica no git**. Crie `keystore.properties` nesta pasta (ignorado pelo git):

```properties
storeFile=/caminho/seguro/gestaofamiliar-crianca.jks
storePassword=...
keyAlias=crianca
keyPassword=...
```

```bash
./gradlew assembleRelease   # app/build/outputs/apk/release/app-release.apk
```

### Publicar a versão nova no site

O app é baixado em **/app** do site (página pública, sem login). Em Localização › Celulares há o cartão com botão, QR code e link.

O APK não fica no git. Há dois jeitos de publicar:

- **Automático**: um admin gera o **token de publicação** em Localização › Celulares (o token aparece uma vez só; gerar outro invalida o anterior). Quem publica envia:

  ```bash
  curl -X POST -H "X-App-Publish-Token: $TOKEN" -F versao=2.0.0 -F arquivo=@app/build/outputs/apk/release/app-release.apk \
    https://gestaofamiliar.kbosolucoes.com.br/api/v1/app-android/publicar
  ```

  O token só serve para publicar o APK (guardado com hash no banco) e pode ser revogado no mesmo cartão.
- **Manual**: depois de gerar o APK assinado (`./gradlew assembleRelease`), um admin abre **Localização › Celulares › Enviar nova versão do app**, escolhe o arquivo e a versão (ex.: 1.0.3) e toca em Publicar. O servidor guarda as 3 últimas versões e entrega sempre a mais nova. Não precisa de redeploy.

Use sempre a mesma chave: o Android só aceita atualizar o app se o APK novo vier assinado com a mesma chave do instalado. Para cada versão nova, aumente `versionCode` e `versionName` em `app/build.gradle.kts`.

## Testes

- `FilaDePontosTest`: ordem de envio, erro de rede, ponto recusado, token revogado, limite da fila, formato do ponto, leitura das respostas da API e rede lenta (o envio não trava a posição nova nem a tela).
- `SessaoTest`: o que o app faz em cada login (criança, adulto, troca de criança, versão antiga), comparação de versões e quais endereços abrem dentro do app ou falam com a ponte.
- `ApiIntegracaoTest`: pareia e envia pontos contra uma API real. Só roda com `GF_API_URL` e `GF_CODIGO` definidos (por exemplo, contra uma API local). Não use produção sem combinar.

```bash
GF_API_URL=http://127.0.0.1:8001 GF_CODIGO=ABCD-1234 ./gradlew testDebugUnitTest
```

  O teste `criancaLogadaConectaEAdultoRecebeAlerta` usa `GF_LOGIN_CRIANCA` e `GF_LOGIN_ADULTO` (tokens de login de uma API local): login da criança conecta o celular, bateria baixa vira alerta no celular do adulto, troca de criança revoga o token antigo.
