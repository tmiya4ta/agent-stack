#!/bin/bash
# embed-emu をビルドし、イメージを作って k0 に読み込む。
#   ./build.sh            版は VERSION のもの
set -euo pipefail
cd "$(dirname "$0")"
v=$(cat VERSION)
mkdir -p build
clay build main.clay -o build/embed-emu
docker build -q -t "embed-emu:$v" .
kind load docker-image "embed-emu:$v" --name k0
echo "embed-emu:$v loaded into k0"
