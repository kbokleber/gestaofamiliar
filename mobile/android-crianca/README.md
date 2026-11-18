# App Android da criança — Gestão Familiar

App enxuto que pareia o celular da criança com a família e envia **localização e bateria** a cada ~5 minutos para o Gestão Familiar da KBO Soluções. Não grava áudio, não vê a tela, fotos ou mensagens, e não controla tempo de tela.

- Pacote: `br.com.kbosolucoes.gestaofamiliar.crianca`
- Android 8.0 (API 26) ou mais novo
- API usada: `/api/v1/localizacao/dispositivos/parear` e `/api/v1/localizacao/dispositivos/posicao`

## Instalar no celular da criança

1. Copie o APK para o celular, por exemplo pelo WhatsApp, Google Drive ou cabo USB.
2. Abra o arquivo. Se o Android pedir, permita "instalar apps desta fonte".
3. Abra o app **Gestão Familiar**.
4. No site, como adulto, vá em **Localização › Celulares** e toque em **Gerar código** na criança certa.
5. No app, confira o endereço do site (já vem preenchido com `https://gestaofamiliar.kbosolucoes.com.br`), digite o código e toque em **Conectar à família**. O código vale 15 minutos e serve uma vez só.
6. O app mostra uma lista. Complete todos os itens até ficarem com ✓:
   - **Localização**: Permitir, com "Localização precisa".
   - **Notificação fixa** (Android 13+): Permitir.
   - **Localização o tempo todo**: na tela que abrir, escolha **Permitir o tempo todo**.
   - **Sem economia de bateria**: Permitir.
7. Toque em **Enviar agora**. Em alguns segundos a criança aparece no mapa do site.

Alguns fabricantes (Xiaomi, Samsung, Motorola, Huawei) têm uma economia de bateria própria, além da do Android. Se o envio parar com a tela desligada, procure nas configurações do celular por "Inicialização automática" ou "Apps em segundo plano" e libere o Gestão Familiar.

## Como funciona

- **Serviço em primeiro plano** com notificação fixa ("Localização compartilhada com a família"). A notificação é obrigatória no Android e deixa claro, para a criança, que o compartilhamento está ligado.
- **Intervalo**: pede posição a cada 5 minutos (no mínimo 2), pelo provedor de localização do Google Play Services.
- **Sem internet**: os pontos ficam numa fila no próprio celular (até uma semana) e são enviados na ordem quando a conexão volta. O servidor recusa pontos com mais de 7 dias.
- **Ao ligar o celular** ou atualizar o app, o envio volta sozinho (precisa de "Permitir o tempo todo").
- **Revogação**: quando um adulto revoga o celular no site, o próximo envio recebe 401. O app apaga o token e a fila, para de enviar e avisa para parear de novo. O app não tem botão de desligar: quem desliga é o adulto, pelo site.
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

Use sempre a mesma chave: o Android só aceita atualizar o app se o APK novo vier assinado com a mesma chave do instalado. Para cada versão nova, aumente `versionCode` e `versionName` em `app/build.gradle.kts`.

## Testes

- `FilaDePontosTest`: ordem de envio, erro de rede, ponto recusado, token revogado, limite da fila, formato do ponto e leitura das respostas da API.
- `ApiIntegracaoTest`: pareia e envia pontos contra uma API real. Só roda com `GF_API_URL` e `GF_CODIGO` definidos (por exemplo, contra uma API local). Não use produção sem combinar.

```bash
GF_API_URL=http://127.0.0.1:8001 GF_CODIGO=ABCD-1234 ./gradlew testDebugUnitTest
```
