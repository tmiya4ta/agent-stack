#!/usr/bin/env bash
# build/chat-server を ~/.local/lib/chat-server/ に置き、systemd --user サービスとして（再）起動する。
# 初回だけ ~/.config/chat-server/env（0600）を作り、ランダムな API キーを CHAT_API_KEYS に入れる。
#
#   ./install.sh                  ビルド済みのものを入れる（無ければビルドする）
#   systemctl --user status chat-server
#   journalctl --user -u chat-server -f
set -euo pipefail
cd "$(dirname "$0")"
[ -x build/chat-server ] || ./build.sh

DEST=$HOME/.local/lib/chat-server
CONF=$HOME/.config/chat-server
UNIT=$HOME/.config/systemd/user
mkdir -p "$DEST" "$CONF" "$UNIT"

# 動いているプロセスは古い inode を持ち続けるので、置き換えは rename で行う
install -m 0755 build/chat-server "$DEST/chat-server.new"
mv -f "$DEST/chat-server.new" "$DEST/chat-server"

if [ ! -f "$CONF/env" ]; then
  (
    umask 077
    cat > "$CONF/env" <<EOT
# chat-server の設定（systemd の EnvironmentFile）。変更後: systemctl --user restart chat-server
# CHAT_API_KEYS はカンマ区切りで複数書ける。空にすると認証しない（公開中は空にしないこと）。
CHAT_API_KEYS=sk-chat-$(openssl rand -hex 24)
#CHAT_MODEL=$HOME/models/gguf/llama3.2-3b-instruct-q4_k_m.gguf
#CHAT_MODEL_ID=llama3.2-3b-instruct-q4_k_m
#CHAT_HOST=172.23.0.1
#CHAT_PORT=8898
#CHAT_THREADS=8
#CHAT_GPU_LAYERS=-1
#CHAT_CTX=8192
EOT
  )
  echo "created $CONF/env (API key inside)"
fi

install -m 0644 chat-server.service "$UNIT/chat-server.service"
systemctl --user daemon-reload
systemctl --user enable chat-server
systemctl --user restart chat-server
echo "installed: $DEST/chat-server (systemctl --user status chat-server)"
