#!/bin/bash
# max-core / max-oms を Runtime Manager から RTF (k0) に配備する。ランタイムは 4.9.22:8-java17 (k0 のノードに mulay のイメージを
# この名前で載せてある。theorems-infra の cluster/rtf-custom-runtime)。環境は T1 / Sandbox (名前空間 0f678523-..)。
#   ./deploy.sh oms|core <version>     (先に ./build-jar.sh <app>)
# 秘密の値は鍵のファイル (~/.config/max-*/env、sf-secret.yaml) から読み、安全なプロパティ (+secure:) で渡す。
# yc の要求の記録 (~/.yc/logs) に値が残らないよう、YC_NO_OPLOG=1 で配備する。
# RTF のイメージは http.port=8081 を先に置くので、中の API は 8081、外に出す口 (MCP、画面) は 8082 (Service に口がある)。
set -euo pipefail
cd "$(dirname "$0")"
app=${1:?oms or core}; ver=${2:?version}
ORG=fe1db8fb-8261-4b5c-a591-06fea582f980
ENVNS=0f678523-c036-4098-9be9-cc542dca2e6d
DB="jdbc:postgresql://max-pg.max-core.svc.cluster.local:5432/max"
FT=https://ft1-23fgzd.pnwfdv.jpn-e1.cloudhub.io
kv() { grep "^$2=" "$1" | cut -d= -f2-; }
. "$HOME/.config/max-mq/env"
mq_url="$MQ_URL/organizations/$MQ_ORG/environments/$MQ_ENV"
common=(target=rtf:k0 runtime=4.9.22:8-java17 replicas=1 cpu-reserved=100m cpu-limit=1000m mem-reserved=128Mi mem-limit=512Mi
        "+db.url=$DB" +db.user=max_app
        "+secure:db.password=$(kv "$HOME/.config/max-db/env" POSTGRES_PASSWORD)"
        "+secure:mq.url=$mq_url" "+secure:mq.clientId=$MQ_CLIENT_ID" "+secure:mq.clientSecret=$MQ_CLIENT_SECRET")
case "$app" in
  oms)
    props=(+ui.port=8082 "+secure:api.key=$(kv "$HOME/.config/max-oms/env" API_KEY)") ;;
  core)
    sf=../core/src/main/resources/sf-secret.yaml
    sfv() { python3 -I -c 'import sys,re
for l in open(sys.argv[1]):
    m=re.match(r"\s*"+re.escape(sys.argv[2])+r":\s*\"?(.*?)\"?\s*$",l)
    if m: print(m.group(1)); break' "$sf" "$1"; }
    props=(+mcp.port=8082 "+oms.url=http://max-oms.$ENVNS.svc:8081" +clock.auto.interval=120000
           "+broker.url=$FT/max-surveillance-broker/" "+broker.opsUrl=$FT/max-operations-broker/" "+broker.supportUrl=$FT/max-support-broker/"
           "+secure:api.key=$(kv "$HOME/.config/max-core/env" API_KEY)"
           "+secure:broker.jwtSecret=$(kv "$HOME/.config/max-core/env" BROKER_JWT_SECRET)"
           "+secure:oms.key=$(kv "$HOME/.config/max-oms/env" API_KEY)"
           "+secure:sf.clientId=$(sfv sf.clientId)" "+secure:sf.clientSecret=$(sfv sf.clientSecret)" "+secure:sf.tokenUrl=$(sfv sf.tokenUrl)") ;;
  *) echo "oms or core" >&2; exit 2 ;;
esac
YC_NO_OPLOG=1 yc deploy file T1 Sandbox "$ORG" "max-$app" "$ver" "build/max-$app.jar" "${common[@]}" "${props[@]}"
