#!/bin/bash
# max-core の Secret (max-core-secrets) を作る。値は表示しない。
#   keys.properties: api.key (~/.config/max-core/env の API_KEY。無ければ作る) と db.password (~/.config/max-db/env)
#   sf.yaml: 承認箱の Salesforce の認証情報 (../../max/core/src/main/resources/sf-secret.yaml。gitignore 済み)
set -euo pipefail
cd "$(dirname "$0")"
env="$HOME/.config/max-core/env"
if [ ! -f "$env" ]; then
  mkdir -p "$(dirname "$env")"
  (umask 077; printf 'API_KEY=%s\n' "$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 40)" > "$env")
  echo "made $env"
fi
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
(umask 077
 printf 'api.key=%s\ndb.password=%s\n' "$(grep '^API_KEY=' "$env" | cut -d= -f2-)" "$(grep '^POSTGRES_PASSWORD=' "$HOME/.config/max-db/env" | cut -d= -f2-)" > "$tmp/keys.properties")
kubectl --context kind-k0 -n max-core create secret generic max-core-secrets \
  --from-file=keys.properties="$tmp/keys.properties" --from-file=sf.yaml=../../max/core/src/main/resources/sf-secret.yaml \
  --dry-run=client -o yaml | kubectl --context kind-k0 apply -f - >/dev/null
echo "secret max-core/max-core-secrets"
