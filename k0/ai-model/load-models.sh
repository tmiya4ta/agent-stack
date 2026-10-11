#!/bin/bash
# モデルの GGUF を k0 の PVC (ai-model/models) に入れる。
#   ./load-models.sh            ~/models/gguf から Ornith と gte-Qwen2 (q8_0) を入れる
# PVC は local-path なので、実体は k0-worker のコンテナの中のディレクトリ。kubectl cp (API サーバー経由) は
# 20GB では遅いので、docker cp でノードに直接書く。同じ大きさのファイルが既にあれば飛ばす。
set -euo pipefail
cd "$(dirname "$0")"
CTX=kind-k0
NODE=k0-worker
SRC=${MODELS_DIR:-$HOME/models/gguf}
FILES=(Ornith-1.5-35B-Q4_K_M.gguf gte-Qwen2-1.5B-instruct-q8_0.gguf)

kubectl --context $CTX apply -f ../namespaces.yaml -f models-pvc.yaml >/dev/null
kubectl --context $CTX -n ai-model wait pod/models-loader --for=condition=Ready --timeout=300s >/dev/null
pv=$(kubectl --context $CTX -n ai-model get pvc models -o jsonpath='{.spec.volumeName}')
dir=$(kubectl --context $CTX get pv "$pv" -o jsonpath='{.spec.hostPath.path}{.spec.local.path}')
echo "PVC models -> $NODE:$dir"
for f in "${FILES[@]}"; do
  want=$(stat -c %s "$SRC/$f")
  have=$(docker exec $NODE stat -c %s "$dir/$f" 2>/dev/null || echo 0)
  if [ "$have" = "$want" ]; then echo "skip $f (already there)"; continue; fi
  echo "copy $f ($((want / 1024 / 1024)) MiB)"
  docker cp "$SRC/$f" "$NODE:$dir/$f"
  docker exec $NODE chmod 0444 "$dir/$f"
done
kubectl --context $CTX -n ai-model exec models-loader -- ls -l /models
kubectl --context $CTX -n ai-model delete pod models-loader --wait=false >/dev/null
