#!/bin/bash
# max-core の実行ファイルを mulay build で作り、イメージにして k0 に読み込む。
#   ./build.sh            版は VERSION のもの。アプリは ../../max/core
# 認証情報 (sf-secret.yaml) をイメージに入れないため、それを除いた複製 (symlink は実体にする) から作る。
# 中身を変えたら VERSION を上げ、max-core.yaml の image も上げる。
set -euo pipefail
cd "$(dirname "$0")"
v=$(cat VERSION)
mulay_dir=${MULAY_DIR:-$HOME/projects/mulay}
src=$(mktemp -d)
trap 'rm -rf "$src"' EXIT
rsync -aL --exclude 'sf-secret.yaml' --exclude 'mq-secret.yaml' --exclude target ../../max/core/ "$src/core/"
# ビルドの検査を通すための値の無い代わり (実行時は sf.file=/secrets/max-core/sf.yaml で Secret のファイルを読む)
printf 'sf:\n  clientId: "unset"\n  clientSecret: "unset"\n  tokenUrl: "unset"\n' > "$src/core/src/main/resources/sf-secret.yaml"
printf 'mq:\n  url: "unset"\n  clientId: "unset"\n  clientSecret: "unset"\n' > "$src/core/src/main/resources/mq-secret.yaml"
mkdir -p build
"$mulay_dir/target/mulay" build "$src/core" -o build/max-core >/dev/null
docker build -q -t "max-core:$v" .
kind load docker-image "max-core:$v" --name k0
echo "max-core:$v loaded into k0 (mulay $(git -C "$mulay_dir" log -1 --format=%h))"
