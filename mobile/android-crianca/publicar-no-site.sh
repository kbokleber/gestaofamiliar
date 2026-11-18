#!/usr/bin/env bash
# Copia o APK assinado (release) para o site, em frontend/public/downloads,
# e atualiza app-crianca.json com versão, tamanho e SHA-256.
# Uso: ./publicar-no-site.sh [caminho-do-apk]   (padrão: app/build/outputs/apk/release/app-release.apk)
set -euo pipefail
cd "$(dirname "$0")"
APK="${1:-app/build/outputs/apk/release/app-release.apk}"
DESTINO="../../frontend/public/downloads"
[ -f "$APK" ] || { echo "APK não encontrado: $APK (rode ./gradlew assembleRelease com a chave)"; exit 1; }

VERSAO=$(sed -n 's/.*versionName = "\(.*\)".*/\1/p' app/build.gradle.kts | head -n1)
CODIGO=$(sed -n 's/.*versionCode = \([0-9]*\).*/\1/p' app/build.gradle.kts | head -n1)
mkdir -p "$DESTINO"
cp "$APK" "$DESTINO/gestaofamiliar-crianca.apk"
TAMANHO=$(wc -c < "$DESTINO/gestaofamiliar-crianca.apk" | tr -d ' ')
SHA=$(sha256sum "$DESTINO/gestaofamiliar-crianca.apk" | cut -d' ' -f1)
cat > "$DESTINO/app-crianca.json" <<JSON
{
  "versao": "$VERSAO",
  "codigo": $CODIGO,
  "arquivo": "/downloads/gestaofamiliar-crianca.apk",
  "tamanho_bytes": $TAMANHO,
  "sha256": "$SHA",
  "publicado_em": "$(date -u +%Y-%m-%d)"
}
JSON
echo "Publicado no site: versão $VERSAO ($TAMANHO bytes). Faça commit de frontend/public/downloads e o redeploy."
