#!/bin/bash
# llm-openai-emu をビルドし、イメージを作って k0 に読み込む。
#   ./build.sh            版は VERSION のもの
set -euo pipefail
cd "$(dirname "$0")"
v=$(cat VERSION)
mkdir -p build
clay build main.clay -o build/llm-openai-emu
docker build -q -t "llm-openai-emu:$v" .
kind load docker-image "llm-openai-emu:$v" --name k0
echo "llm-openai-emu:$v loaded into k0"
