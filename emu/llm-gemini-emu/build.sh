#!/bin/bash
# llm-gemini-emu をビルドし、イメージを作って k0 に読み込む。
#   ./build.sh            版は VERSION のもの
set -euo pipefail
cd "$(dirname "$0")"
v=$(cat VERSION)
mkdir -p build
clay build main.clay -o build/llm-gemini-emu
docker build -q -t "llm-gemini-emu:$v" .
kind load docker-image "llm-gemini-emu:$v" --name k0
echo "llm-gemini-emu:$v loaded into k0"
