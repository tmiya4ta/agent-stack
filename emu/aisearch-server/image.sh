#!/bin/bash
# aisearch-server のイメージを作って k0 に読み込む (ai-search.azure.emu)。先に ./build.sh でテストとビルドを済ませる。
#   ./image.sh            版は VERSION のもの
set -euo pipefail
cd "$(dirname "$0")"
v=$(cat VERSION)
test -x build/aisearch-server
docker build -q -t "aisearch-server:$v" .
kind load docker-image "aisearch-server:$v" --name k0
echo "aisearch-server:$v loaded into k0"
