#!/bin/bash
# max-oms の実行ファイルを mulay build で作り、イメージにして k0 に読み込む。
#   ./build.sh            版は VERSION のもの。アプリは ../../max/oms
# 認証情報 (mq-secret.yaml) をイメージに入れないため、それを除いた複製 (symlink は実体にする) から作る。
set -euo pipefail
cd "$(dirname "$0")"
v=$(cat VERSION)
mulay_dir=${MULAY_DIR:-$HOME/projects/mulay}
src=$(mktemp -d)
trap 'rm -rf "$src"' EXIT
rsync -aL --exclude 'mq-secret.yaml' --exclude target ../../max/oms/ "$src/oms/"
# ビルドの検査を通すための値の無い代わり (実行時は mq.file=/secrets/max-oms/mq.yaml で Secret のファイルを読む)
printf 'mq:\n  url: "unset"\n  clientId: "unset"\n  clientSecret: "unset"\n' > "$src/oms/src/main/resources/mq-secret.yaml"
mkdir -p build
"$mulay_dir/target/mulay" build "$src/oms" -o build/max-oms >/dev/null
docker build -q -t "max-oms:$v" .
kind load docker-image "max-oms:$v" --name k0
echo "max-oms:$v loaded into k0 (mulay $(git -C "$mulay_dir" log -1 --format=%h))"
