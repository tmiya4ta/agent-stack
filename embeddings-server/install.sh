#!/usr/bin/env bash
# build/embeddings-server を ~/.local/lib/embeddings-server/ に置き、systemd --user サービスとして（再）起動する。
# 初回だけ ~/.config/embeddings-server/env（0600）を作り、ランダムな API キーを EMB_API_KEYS に入れる。
#
#   ./install.sh                  ビルド済みのものを入れる（無ければビルドする）
#   systemctl --user status embeddings-server
#   journalctl --user -u embeddings-server -f
set -euo pipefail
cd "$(dirname "$0")"
[ -x build/embeddings-server ] || ./build.sh

DEST=$HOME/.local/lib/embeddings-server
CONF=$HOME/.config/embeddings-server
UNIT=$HOME/.config/systemd/user
mkdir -p "$DEST" "$CONF" "$UNIT"

# 動いているプロセスは古い inode を持ち続けるので、置き換えは rename で行う
install -m 0755 build/embeddings-server "$DEST/embeddings-server.new"
mv -f "$DEST/embeddings-server.new" "$DEST/embeddings-server"

if [ ! -f "$CONF/env" ]; then
  (
    umask 077
    cat > "$CONF/env" <<EOF
# embeddings-server の設定（systemd の EnvironmentFile）。変更後: systemctl --user restart embeddings-server
# EMB_API_KEYS はカンマ区切りで複数書ける。空にすると認証しない（公開中は空にしないこと）。
EMB_API_KEYS=sk-emb-$(openssl rand -hex 24)
#EMB_MODEL=$HOME/models/gguf/gte-Qwen2-1.5B-instruct-q8_0.gguf
#EMB_HOST=172.23.0.1
#EMB_PORT=8896
#EMB_THREADS=8
#EMB_GPU_LAYERS=-1
#EMB_CTX=8192
EOF
  )
  echo "created $CONF/env (API key inside)"
fi

install -m 0644 embeddings-server.service "$UNIT/embeddings-server.service"
systemctl --user daemon-reload
systemctl --user enable embeddings-server
systemctl --user restart embeddings-server
echo "installed: $DEST/embeddings-server (systemctl --user status embeddings-server)"
