#!/bin/bash
# max-core / max-oms の Mule アプリの jar を作る (RTF に Runtime Manager から配備するため)。
#   ./build-jar.sh core|oms      → build/max-<app>.jar
# 認証情報をイメージ (jar) に入れないため、秘密のファイルを値の無い代わりにした複製 (symlink は実体にする) から作る。
# 本物の値は配備のときに Runtime Manager の安全なプロパティで渡す (deploy.sh。配備のプロパティがファイルの値に勝つ)。
set -euo pipefail
cd "$(dirname "$0")"
app=${1:?core or oms}
case "$app" in core|oms) ;; *) echo "core or oms" >&2; exit 2 ;; esac
src=$(mktemp -d)
trap 'rm -rf "$src"' EXIT
rsync -aL --exclude 'sf-secret.yaml' --exclude 'mq-secret.yaml' --exclude 'keys.properties' --exclude target \
  "../../max/$app/" "$src/$app/"
r="$src/$app/src/main/resources"
printf 'api.key=\ndb.password=\nbroker.jwtSecret=\noms.key=\n' > "$r/keys.properties"
printf 'mq:\n  url: "unset"\n  clientId: "unset"\n  clientSecret: "unset"\n' > "$r/mq-secret.yaml"
[ "$app" = core ] && printf 'sf.clientId: "unset"\nsf.clientSecret: "unset"\nsf.tokenUrl: "unset"\n' > "$r/sf-secret.yaml"
(cd "$src/$app" && mvn -q -o package -DskipTests)
mkdir -p build
cp "$src/$app"/target/*-mule-application.jar "build/max-$app.jar"
# 秘密が入っていないことを確かめる (値の無い代わりだけ)
if unzip -p "build/max-$app.jar" keys.properties | grep -qE '=[^[:space:]]'; then echo "keys.properties has values" >&2; exit 1; fi
echo "build/max-$app.jar"
