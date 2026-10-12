#!/usr/bin/env bash
# aisearch-server をビルドする: テスト（test/*.clay）を回してから build/aisearch-server を作る。
#
# - clay 0.85.0（2026-10-12 に 0.42 から移した。0.42 の書き方ではもうビルドできない）。
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
