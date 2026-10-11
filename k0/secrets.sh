#!/bin/bash
# 各サービスの API キーの Secret (<名前>-api-key、キー api-key) を ~/.config/<名前>/env の API_KEY から作る。
# env が無ければランダムな鍵を作って 0600 で置く。鍵の値は表示しない。
#   ./secrets.sh <名前空間> <名前>...     例: ./secrets.sh ai-model llm-ornith-model
set -euo pipefail
ns=$1; shift
for name in "$@"; do
  env="$HOME/.config/$name/env"
  if [ ! -f "$env" ]; then
    mkdir -p "$(dirname "$env")"
    (umask 077; printf 'API_KEY=%s\n' "$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 40)" > "$env")
    echo "made $env"
  fi
  key=$(grep '^API_KEY=' "$env" | cut -d= -f2-)
  kubectl --context kind-k0 -n "$ns" create secret generic "$name-api-key" --from-literal=api-key="$key" \
    --dry-run=client -o yaml | kubectl --context kind-k0 apply -f - >/dev/null
  echo "secret $ns/$name-api-key"
done
