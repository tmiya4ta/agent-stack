#!/bin/bash
# stat-models の実行ファイルを mulay build で作り、イメージにして k0 に読み込む。
#   ./build.sh            版は VERSION のもの。アプリは ~/projects/mulay/templates/stat-models (MULAY_DIR で変えられる)
# 中身 (mulay か templates/stat-models か agent-harness の stat/*.dwl) を変えたら VERSION を上げ、yaml の image も上げる。
set -euo pipefail
cd "$(dirname "$0")"
v=$(cat VERSION)
mulay_dir=${MULAY_DIR:-$HOME/projects/mulay}
mkdir -p build
"$mulay_dir/target/mulay" build "$mulay_dir/templates/stat-models" -o build/stat-models http.port=8080 >/dev/null
docker build -q -t "stat-models:$v" .
kind load docker-image "stat-models:$v" --name k0
echo "stat-models:$v loaded into k0 (mulay $(git -C "$mulay_dir" log -1 --format=%h))"
