#!/bin/bash
# max-oms の Secret (max-oms-secrets) を作る。値は表示しない。
#   keys.properties: api.key (~/.config/max-oms/env の API_KEY。無ければ作る) と db.password (~/.config/max-db/env)
#   mq.yaml: Anypoint MQ の認証情報 (~/.config/max-mq/env。client app "max")
set -euo pipefail
env="$HOME/.config/max-oms/env"
if [ ! -f "$env" ]; then
  mkdir -p "$(dirname "$env")"
  (umask 077; printf 'API_KEY=%s\n' "$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 40)" > "$env")
  echo "made $env"
fi
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
(umask 077
 printf 'api.key=%s\ndb.password=%s\n' "$(grep '^API_KEY=' "$env" | cut -d= -f2-)" "$(grep '^POSTGRES_PASSWORD=' "$HOME/.config/max-db/env" | cut -d= -f2-)" > "$tmp/keys.properties"
 . "$HOME/.config/max-mq/env"
 printf 'mq:\n  url: "%s/organizations/%s/environments/%s"\n  clientId: "%s"\n  clientSecret: "%s"\n' "$MQ_URL" "$MQ_ORG" "$MQ_ENV" "$MQ_CLIENT_ID" "$MQ_CLIENT_SECRET" > "$tmp/mq.yaml")
kubectl --context kind-k0 -n max-core create secret generic max-oms-secrets \
  --from-file=keys.properties="$tmp/keys.properties" --from-file=mq.yaml="$tmp/mq.yaml" \
  --dry-run=client -o yaml | kubectl --context kind-k0 apply -f - >/dev/null
echo "secret max-core/max-oms-secrets"
