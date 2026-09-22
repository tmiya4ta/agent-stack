#!/usr/bin/env bash
# build/aisearch-server を ~/.local/lib/aisearch-server/ に置き、systemd --user サービスとして（再）起動する。
# 初回だけ ~/.config/aisearch-server/env（0600）を作り、ランダムな api-key を AIS_API_KEYS に入れる。
# データ（状態を変えた要求のログ）は ~/.local/share/aisearch-server/log/。
#
#   ./install.sh                  ビルド済みのものを入れる（無ければビルドする）
#   systemctl --user status aisearch-server
#   journalctl --user -u aisearch-server -f
set -euo pipefail
cd "$(dirname "$0")"
[ -x build/aisearch-server ] || ./build.sh

DEST=$HOME/.local/lib/aisearch-server
CONF=$HOME/.config/aisearch-server
UNIT=$HOME/.config/systemd/user
mkdir -p "$DEST" "$CONF" "$UNIT"

# 動いているプロセスは古い inode を持ち続けるので、置き換えは rename で行う
install -m 0755 build/aisearch-server "$DEST/aisearch-server.new"
mv -f "$DEST/aisearch-server.new" "$DEST/aisearch-server"

if [ ! -f "$CONF/env" ]; then
  (
    umask 077
    cat > "$CONF/env" <<EOT
# aisearch-server の設定（systemd の EnvironmentFile）。変更後: systemctl --user restart aisearch-server
# AIS_API_KEYS はカンマ区切りで複数書ける。空にすると認証しない（公開中は空にしないこと）。
AIS_API_KEYS=$(openssl rand -hex 26)
#AIS_HOST=172.23.0.1
#AIS_PORT=8897
#AIS_SERVICE=aisearch
#AIS_DATA=$HOME/.local/share/aisearch-server
EOT
  )
  echo "created $CONF/env (api-key inside)"
fi

install -m 0644 aisearch-server.service "$UNIT/aisearch-server.service"
systemctl --user daemon-reload
systemctl --user enable aisearch-server
systemctl --user restart aisearch-server
echo "installed: $DEST/aisearch-server (systemctl --user status aisearch-server)"
