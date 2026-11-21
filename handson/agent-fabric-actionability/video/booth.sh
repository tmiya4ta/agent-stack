#!/bin/sh
# 録画用の Lab の台本を、ブースのアカウントで流して設定を作る (動画は使わない)。
# ドライバはブースの設定で起動しておく:
#   CRED=-1 WS_BG="Actionability Workshop1" PROFILE=out/profile-booth1 HANDSON_ENV=<env.json> node rec-driver.js
# 使い方: B=1 USER_BG=tmiyashita-10879 ORG=<ワークショップの BG の ID> [INST=<commerce-mcp-demo のインスタンス ID>] ./booth.sh m2-lab1a
#   台本の中の「Agent_Actionability_Workshop」「tmiyashita-10730」と、録画した org の ID を置き換えて流す。
#   録画は out/b<B>-<lab>.* に書く (録画用のファイルは上書きしない)
#   NOPREFIX=1 なら、ツール名の customer-rest-api_ / order-rest-api_ を外す (ブース 2 の org の MCP Bridge は、
#   ツール名に API の名前を付けない。get_customers、createOrder など)
lab="$1"; HERE="$(cd "$(dirname "$0")" && pwd)"
sed -e "s|Agent_Actionability_Workshop|${WS_BG:-Actionability Workshop$B}|g" \
    -e "s|tmiyashita-10730|$USER_BG|g" \
    -e "s|1ef6e021-8792-4d54-a2aa-21093e741434|$ORG|g" -e "s|21284377|${INST:-21284377}|g" "$HERE/labs/$lab.js" > "$HERE/out/booth-$lab.js"
[ -n "$NOPREFIX" ] && sed -i -e "s|customer-rest-api_||g" -e "s|order-rest-api_||g" "$HERE/out/booth-$lab.js"
"$HERE/run.sh" start "b$B-$lab" && T=1500 "$HERE/run.sh" < "$HERE/out/booth-$lab.js"; echo; "$HERE/run.sh" stop
