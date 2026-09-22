#!/usr/bin/env bash
# aisearch-server をビルドする: テスト（test/*.clay）を回してから build/aisearch-server を作る。
#
# - clay 0.42.0 以降（http/header・スレッド安全な atom は 0.41.0、run-server アプリの `clay build` は 0.41.1、
#   chunked の要求本文・threaded バックエンドの自動選択・max-body が効かない不具合の修正は 0.42.0）。
# - `-I .` はモジュール ais/*.clay を解決する起点（無いと入口と同じ階層の ais/ais/.. を探す）。
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
for t in odata engine; do
  clay build -I . "test/${t}_test.clay" -o "build/${t}_test" >/dev/null
  "build/${t}_test"
done
clay build -I . ais/server.clay -o build/aisearch-server >/dev/null
echo "built: build/aisearch-server ($(clay --version))"
