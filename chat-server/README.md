# chat-server

OpenAI Chat Completions API と Gemini API（generateContent）の両方の形で話せる LLM サーバ。
Ornith 1.5 35B（Qwen3.5 系の MoE、35B のうち 1 トークンあたり約 3B が動く。Q4_K_M、21.7GB）を llama.cpp で動かし
（内蔵 GPU の Vulkan）、HTTP まわりは clay で書いている。
Anypoint の Model Proxy の Route B（fallback）に向ける想定。作りは embeddings-server と同じ。

```
Anypoint ─ https://theorems-relay-….cloudhub.io/chat/ ─ https://chat.theorems.io ─ theorems-edge (Caddy)
                                                                                      ▼
                                     172.23.0.1:8898  chat-server（clay の HTTP サーバ、systemd --user）
                                                          │ defextern
                                     chatshim.c ── 計算スレッド 1 本 ── llama.cpp（静的リンク、Vulkan）
```

## エンドポイント

| メソッド | パス | 認証 | 内容 |
|---|---|---|---|
| POST | `/v1/chat/completions` | 要 | OpenAI と同じリクエスト / レスポンス / エラー形式 |
| GET | `/v1/models` | 要 | `CHAT_MODEL_ID`（既定は GGUF のファイル名、今は `Ornith-1.5-35B-Q4_K_M`） |
| POST | `…/models/{model}:generateContent` | 要 | Gemini と同じ形（`/v1beta/models/..` も Vertex の `/v1/projects/../models/..` も） |
| POST | `…/models/{model}:streamGenerateContent` | 要 | `?alt=sse` なら SSE、無ければ JSON 配列（どちらも生成後にまとめて送る） |
| POST | `…/models/{model}:countTokens` | 要 | `{"totalTokens": n}` |
| GET | `/v1beta/models` | 要 | `models/gemini-2.5-flash` を 1 件 |
| GET | `/health` | 不要 | 死活確認 |

- 認証は `Authorization: Bearer <key>`、`x-goog-api-key: <key>`、`?key=<key>` のどれでもよい
  （キーが無いと OpenAI 形式は 401、Gemini 形式は 403 PERMISSION_DENIED、違うキーは Gemini 形式で 400 INVALID_ARGUMENT）
- Gemini 形式: `contents`（role は user / model）、`systemInstruction`、`generationConfig.maxOutputTokens` / `temperature`
  （snake_case も可）。parts は text だけ読む。応答は `candidates[0].content.parts[0].text`・`finishReason`（STOP / MAX_TOKENS）・
  `usageMetadata`・`modelVersion`（パスのモデル名をそのまま返す）
- パスの `%XX` は戻してから振り分ける。リレーが `:` を `%3A` にして送ってくるため

- `model` はどの名前でも受け、応答にそのまま返す（Model Proxy のルートに書いた名前が来るため）
- `messages`: role は system / developer / user / assistant / tool / function。content は文字列か
  `{"type":"text","text":..}` の配列（画像などは無視）。会話はモデルの chat template で 1 本のプロンプトにする
- `max_tokens` / `max_completion_tokens`（既定 512）、`temperature`（0〜2、既定 0.7。0 なら常に最も確からしいトークン）。
  0 より大きいときは top_k 20・top_p 0.8・min_p 0.05 で絞ってから引く
- `stream: true` は SSE で返すが、生成が終わってからまとめて送る（逐次ではない）。`stream_options.include_usage` 可
- `n` は 1 だけ。`tools` などは無視する
- 会話全体が `CHAT_CTX`（既定 8192 トークン）を超えると 400 `context_length_exceeded`

## 使い方

```bash
KEY=$(grep ^CHAT_API_KEYS= ~/.config/chat-server/env | cut -d= -f2)
curl -s https://theorems-relay-23fgzd.pnwfdv.jpn-e1.cloudhub.io/chat/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"こんにちは"}]}'
```

Anypoint など外部からは `chat.theorems.io` の直 URL が届かない（接続元によって拒否される）ので、リレーの URL を使う。
このマシンからは `http://172.23.0.1:8898` か `curl --resolve chat.theorems.io:443:192.168.11.6`。

## 速さ

- 生成は 1 秒 25 トークン前後、100 トークンの返答で 4 秒程度（Radeon 780M、Vulkan、Ornith）。
  速さはメモリ帯域で決まる（DDR5-5600 の 2 チャネル）。Llama 3.2 3B なら 30〜35 トークン/秒
- 生成は 1 件ずつ直列（同時リクエストは待ち合わせる）
- リレーの応答待ちは 60 秒なので、リレー経由では 1400 トークン程度が上限の目安
- 起動（モデルの読み込み）に 20 秒ほどかかる。GPU 側（GTT）を 20GB ほど使う

## ビルドと運用

```bash
./build.sh        # llama.cpp の静的ビルドは ../embeddings-server/build-llama を共用（無ければ作る）→ build/chat-server
./install.sh      # ~/.local/lib/chat-server/ に置いて systemd --user で（再）起動。初回は API キーを作る
systemctl --user status chat-server
journalctl --user -u chat-server -f     # 1 要求 1 行 + 生成ごとにトークン数と tok/s
```

環境変数（`~/.config/chat-server/env`）: `CHAT_API_KEYS` `CHAT_MODEL` `CHAT_MODEL_ID` `CHAT_HOST`（既定 172.23.0.1）
`CHAT_PORT`（既定 8898）`CHAT_THREADS`（既定 8）`CHAT_GPU_LAYERS`（既定 -1 = 全層）`CHAT_CTX`（既定 8192）。

モデル: env の `CHAT_MODEL=~/models/gguf/Ornith-1.5-35B-Q4_K_M.gguf`。指定しなければ
`~/models/gguf/llama3.2-3b-instruct-q4_k_m.gguf`（ollama の `llama3.2` の blob を複製したもの、2.0GB）。
chat template を持つ GGUF なら `CHAT_MODEL` で差し替えられる（持たないものは chatml で包む）。

Ornith のような Qwen3 系は、答える前に `<think>…</think>` で考える過程を書くようにできている。
テンプレートに `enable_thinking` があるモデルでは、プロンプトの末尾に空の `<think>\n\n</think>\n\n` を付けて
考える過程を飛ばす（Jinja で `enable_thinking=false` にしたときと同じ）。それでも `</think>` が出たらそこまでを落とす。

## 構成

```
chat/server.clay         HTTP サーバ（ルーティング、検査、OpenAI 形式の応答、SSE）
chatshim.h / chatshim.c  llama.cpp の薄い層。clay から Int と Str だけで呼べるようにし、生成は専用スレッドで行う
build.sh / install.sh / chat-server.service
```
