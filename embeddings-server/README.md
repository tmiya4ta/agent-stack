# embeddings-server

OpenAI Embeddings API (`POST /v1/embeddings`) 互換の埋め込みサーバ。
[gte-Qwen2-1.5B-instruct](https://huggingface.co/Alibaba-NLP/gte-Qwen2-1.5B-instruct)（Apache-2.0、1536 次元）を
llama.cpp で推論し（内蔵 GPU の Vulkan。GPU が無ければ CPU）、HTTP まわりは clay で書いている。このマシンで systemd --user サービスとして動かし、
`https://embeddings.theorems.io` で公開する。

```
クライアント ─ https://embeddings.theorems.io ─ theorems-edge (Caddy, TLS 終端)
                                                  ▼
                              172.23.0.1:8896  embeddings-server (clay の HTTP サーバ)
                                                  │ defextern
                                                  ▼
                              embshim.c ── 計算スレッド 1 本 ── llama.cpp（静的リンク）
```

## エンドポイント

| メソッド | パス | 認証 | 内容 |
|---|---|---|---|
| POST | `/v1/embeddings` | 要 | OpenAI と同じリクエスト / レスポンス / エラー形式 |
| GET | `/v1/models` | 要 | 受け付けるモデル名 |
| GET | `/health` | 不要 | 死活確認 |

- `model`: `gte-Qwen2-1.5B-instruct` / `text-embedding-ada-002` / `text-embedding-3-small`（中身はどれも同じモデル、1536 次元）。
  `text-embedding-3-large`（3072 次元）は扱わない（404）
- `input`: 文字列か文字列の配列（最大 2048 件、1 件 8192 トークンまで）。
  **トークン ID 配列は 400**（tiktoken の ID をこのモデルの語彙に戻せないため。LangChain は `check_embedding_ctx_length=False` にする）
- `dimensions`: `ada-002` 以外で 1〜1536。先頭を切り出して正規化し直す（このモデルは Matryoshka 学習ではないので、小さくするほど質は落ちる）
- `encoding_format`: `float`（既定）/ `base64`（float32 リトルエンディアン。openai-python SDK の既定）
- `usage` のトークン数はこのモデル（Qwen2）のトークナイザーで数えた値で、tiktoken とは一致しない

## 使い方

```bash
KEY=$(grep ^EMB_API_KEYS= ~/.config/embeddings-server/env | cut -d= -f2)
curl -s https://embeddings.theorems.io/v1/embeddings -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' -d '{"model":"text-embedding-ada-002","input":"注文の配送状況を教えて"}'
```

LAN 内からは `embeddings.theorems.io` を直接開けない（ヘアピン NAT が効かない）。
`--resolve embeddings.theorems.io:443:192.168.11.6` を付けるか、このマシンから直接 `http://172.23.0.1:8896` を叩く。
直接叩くときも同じく `Authorization: Bearer <key>` を付ける。

Anypoint の Semantic Cache Config なら、Provider は OpenAI、Model は `text-embedding-ada-002`、
URL は `https://embeddings.theorems.io/v1/embeddings`、Authentication key は上の `$KEY`。

## 認証

API キーは `~/.config/embeddings-server/env` の `EMB_API_KEYS`（カンマ区切りで複数可、初回の `install.sh` がランダムに作る）。
変えたら `systemctl --user restart embeddings-server`。

サーバは `Authorization: Bearer <key>` を直接検査する（clay 0.41.0 からハンドラでヘッダを読める。
それまでは theorems-edge が Authorization を X-Forwarded-User に写していたが、2026-09-22 に外した）。
サーバは 172.23.0.1（kind bridge）にだけ bind していて、LAN には出ていない。

## 精度と速さ

元の PyTorch 実装（双方向アテンション + 末尾トークン）との一致: コサイン類似度 0.9993 以上（q8_0 量子化。f16 なら 0.99997）。

このサーバで測った類似度:

| 組み合わせ | 類似度 |
|---|---|
| 「注文の配送状況を教えて」/「注文の配送状況を教えてください」 | 0.98 |
| 「注文の配送状況を教えて」/「注文の配達状況を教えて」 | 0.98 |
| 「返品したい」/「購入した商品を返したい」 | 0.87 |
| 「注文の配送状況を教えて」/「出荷はいつ完了しますか」 | 0.70 |
| 「注文の配送状況を教えて」/「Where is my order?」 | 0.66 |
| 「パスワードを忘れました」/「I forgot my password」 | 0.61 |
| 「注文の配送状況を教えて」/「今月の売上レポートを見せて」 | 0.53 |
| 「パスワードを忘れました」/「明日の天気は？」 | 0.28 |

無関係な文どうしでも 0.3 前後、話題が近いと 0.5 前後になる。Semantic Cache のしきい値は、
言い換えまでヒットさせるなら 0.85 前後、表記ゆれ程度に絞るなら 0.95 前後から試す。

内蔵 GPU（Radeon 780M、Mesa RADV の Vulkan）で計算する。サーバ側の処理時間（q8_0）:

| 入力 | GPU（間隔を空けた単発） | GPU（連続） | CPU（8 スレッド） |
|---|---|---|---|
| 9 トークン | 80ms | 50ms | 67ms |
| 79 トークン | 150ms | 94ms | 307ms |
| 521 トークン | 460ms | 400ms | 1.95 秒 |
| 1712 トークン | 1.34 秒 | | 7.4 秒 |
| 8102 トークン | 17.4 秒 | | |

- 短い入力はモデルの重み（1.76GB）を 1 回読むだけで時間が決まる（メモリ帯域律速）。GPU も CPU も同じ DDR5 を
  読むので、短い文では大差がない。長い入力ほど GPU が効く（4〜5 倍）
- 「単発」が遅いのは、GPU のクロックが `auto` だと 0.2 秒ほど暇になると 800MHz に落ち、上がるまでに 30ms ほどかかるため。
  `echo high | sudo tee /sys/class/drm/card0/device/power_dpm_force_performance_level` で常に 2600MHz にすると
  「連続」の値になる（再起動で戻る）
- CPU との差: コサイン類似度 0.9997 以上（演算順の違い）
- 計算は 1 件ずつ直列（同時リクエストは待ち合わせる）。プロセスのメモリ約 150MB（重みは GPU 側 = VRAM 領域 2GB と GTT に置かれる）
- 起動時に journal へ `embshim: gpu Vulkan0 (AMD Radeon 780M Graphics (RADV PHOENIX))` が出れば GPU を使っている。
  `ggml_vulkan: Failed to allocate pinned memory` の警告は出力バッファ（語彙 × n_ctx、約 5GB の仮想領域）を pinned で
  取れず普通のメモリで取り直したという意味で、動作には影響しない
- 以前は ROCm（amdgpu-install）が置いた `/etc/ld.so.conf.d/20-amdgpu.conf` が `/opt/amdgpu` の古い libdrm_amdgpu (2.4.123) を
  先に見せていて、RADV がそれを掴むと `VK_ERROR_INITIALIZATION_FAILED` で GPU が見えなくなる（`vulkaninfo` で llvmpipe しか出ない）。
  2026-09-22 に AMD のパッケージ一式（amdgpu-install、/opt/amdgpu）を消したので今は起きないが、入れ直しても困らないよう
  実行ファイルには RPATH `/usr/lib/x86_64-linux-gnu` を持たせてシステムの libdrm を読ませている（build.sh）

## ビルドと運用

```bash
./build.sh        # build-llama/ に llama.cpp（CPU + Vulkan）を静的ビルド（初回だけ）→ build/embeddings-server
./install.sh      # ~/.local/lib/embeddings-server/ に置いて systemd --user で（再）起動
python3 smoke_test.py http://172.23.0.1:8896                     # 認証なしで起動しているとき
API_KEY=$KEY python3 smoke_test.py http://172.23.0.1:8896        # 通常
systemctl --user status embeddings-server
journalctl --user -u embeddings-server -f                        # 1 リクエスト 1 行のログ
```

環境変数（`~/.config/embeddings-server/env`）: `EMB_MODEL` `EMB_HOST`（既定 172.23.0.1）`EMB_PORT`（既定 8896）
`EMB_THREADS`（既定 8。16 にすると SMT の取り合いで倍遅くなる）`EMB_GPU_LAYERS`（既定 -1 = 全層を GPU、0 = CPU のみ）
`EMB_CTX`（既定 8192）`EMB_API_KEYS`。

モデルファイル:

```
~/models/hf/gte-Qwen2-1.5B-instruct/                  Hugging Face の元データ（7.1GB）
~/models/gguf/gte-Qwen2-1.5B-instruct-q8_0.gguf       既定（1.9GB）
~/models/gguf/gte-Qwen2-1.5B-instruct-f16.gguf        精度優先（3.6GB、CPU で 1 件 80ms 程度）
```

作り直すとき（llama.cpp の変換スクリプトは torch を要求する。transformers はモデル同梱のコードに合わせて 4.49 系）:

```bash
cd ~/projects/llama.cpp-src
uv run --python 3.12 --index https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match \
  --with torch --with 'transformers>=4.44,<4.50' --with sentencepiece --with numpy --with safetensors \
  --with protobuf --with ./gguf-py \
  python convert_hf_to_gguf.py ~/models/hf/gte-Qwen2-1.5B-instruct --outtype q8_0 \
  --outfile ~/models/gguf/gte-Qwen2-1.5B-instruct-q8_0.gguf
```

## 構成

```
emb/server.clay          HTTP サーバ（ルーティング、検査、OpenAI 形式の応答）
embshim.h / embshim.c    llama.cpp の薄い層。clay から Int と Str だけで呼べるようにし、計算は専用スレッドで行う
build.sh / install.sh    ビルドとインストール
embeddings-server.service  systemd --user のユニット
smoke_test.py            スモークテスト（標準ライブラリのみ）
```

clay 側の制約でこうなっているところ:

- `run-server` のアプリは `clay build` ではなく clay の `build.sh` に `-DCLAY_SERVER=threaded` を付けてビルドする
- `(c-include "\"embshim.h\"")` の形は使えず、`(c/..)` の型調べは -I なしで走る。そのため宣言は `defextern` で書き、
  `embshim.h` は `-include` で読ませている
- ハンドラは 256KB スタックのスレッドで並行に動く。llama.cpp は embshim.c の計算スレッド（64MB スタック）でだけ呼ぶ
- Vulkan のシェーダ生成に glslc が要る（`glslc` パッケージ）
