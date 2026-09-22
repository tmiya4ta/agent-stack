#!/usr/bin/env python3
"""embeddings-server のスモークテスト（標準ライブラリのみ）。

  python3 smoke_test.py [BASE_URL]                 # 既定 http://172.23.0.1:8896
  API_KEY=xxx python3 smoke_test.py [BASE_URL]     # EMB_API_KEYS を設定しているとき

Caddy (theorems-edge) 経由でも直接でも同じ（Authorization: Bearer <key>）。
"""
import base64
import json
import math
import os
import struct
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://172.23.0.1:8896").rstrip("/")
API_KEY = os.environ.get("API_KEY", "")
failures = []


def call(method, path, body=None, raw=None, key=API_KEY):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def embed(model, inp, **kw):
    return call("POST", "/v1/embeddings", {"model": model, "input": inp, **kw})


def check(name, cond, detail=""):
    """cond は真偽値か、真偽値を返す関数（途中で例外になっても FAIL として続行する）"""
    try:
        ok = bool(cond() if callable(cond) else cond)
    except Exception as e:  # noqa: BLE001
        ok, detail = False, f"{type(e).__name__}: {e} / {detail}"
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -- {str(detail)[:500]}"))
    if not ok:
        failures.append(name)


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def vec(resp, i=0):
    return resp["data"][i]["embedding"]


# --- 正常系 ---
s, r = call("GET", "/health", key="")
check("GET /health（認証なしで 200）", lambda: s == 200 and r["status"] == "ok", (s, r))

t0 = time.time()
s, r = embed("text-embedding-ada-002", "注文の配送状況を教えて")
ms = (time.time() - t0) * 1000
check("ada-002: 200 / list / 1536次元", lambda: s == 200 and r["object"] == "list" and len(vec(r)) == 1536, (s, r))
check("ada-002: data[0] の形", lambda: r["data"][0]["object"] == "embedding" and r["data"][0]["index"] == 0, r)
check("ada-002: L2ノルム = 1", lambda: abs(math.sqrt(sum(x * x for x in vec(r))) - 1) < 1e-5)
check("ada-002: 0 の次元が無い（密なベクトル）", lambda: sum(1 for x in vec(r) if x == 0) < 5)
check("usage を返す", lambda: r["usage"]["prompt_tokens"] > 0 and r["usage"]["total_tokens"] == r["usage"]["prompt_tokens"], r.get("usage"))
check("model をそのまま返す", lambda: r["model"] == "text-embedding-ada-002", r.get("model"))
print(f"     (1 件 {ms:.0f} ms)")

_, r2 = embed("text-embedding-ada-002", "注文の配送状況を教えて")
check("同じ入力は同じベクトル", lambda: vec(r) == vec(r2))

anchor = "注文の配送状況を教えて"
s, rs = embed("gte-Qwen2-1.5B-instruct", [anchor, "出荷はいつ完了しますか", "Where is my order?", "今月の売上レポートを見せて", "明日の天気は？"])
sims = [cos(vec(rs, 0), vec(rs, i)) for i in range(1, 5)] if s == 200 else []
check("配列入力: 件数と index", lambda: s == 200 and [d["index"] for d in rs["data"]] == [0, 1, 2, 3, 4], (s, rs))
check("配列入力の要素 = 単発呼び出しと同じ", lambda: max(abs(a - b) for a, b in zip(vec(rs, 0), vec(r))) < 1e-6)
check("言い換え・日英は無関係な文より近い", lambda: min(sims[0], sims[1]) > max(sims[2], sims[3]) + 0.1, sims)
print(f"     (類似度: 出荷 {sims[0]:.3f} / Where is my order {sims[1]:.3f} / 売上 {sims[2]:.3f} / 天気 {sims[3]:.3f})" if sims else "")

s, r = embed("text-embedding-3-small", "hello", dimensions=256)
check("3-small + dimensions=256", lambda: s == 200 and len(vec(r)) == 256 and abs(math.sqrt(sum(x * x for x in vec(r))) - 1) < 1e-5, (s, r))

s, rf = embed("text-embedding-3-small", "base64 check", encoding_format="float")
s2, r64 = embed("text-embedding-3-small", "base64 check", encoding_format="base64")
check("base64: float32 LE に復号すると float 版と一致",
      lambda: s2 == 200 and max(abs(a - b) for a, b in
                                zip(struct.unpack("<1536f", base64.b64decode(vec(r64))), vec(rf))) < 1e-6, (s2, r64))

s, r = call("GET", "/v1/models")
check("GET /v1/models", lambda: s == 200 and {m["id"] for m in r["data"]} >= {"text-embedding-ada-002", "text-embedding-3-small", "gte-Qwen2-1.5B-instruct"}, (s, r))


# --- 異常系（OpenAI と同じ error 形式） ---
def check_error(name, resp, status, param=None, code=None):
    s, r = resp
    err = (r or {}).get("error", {})
    ok = s == status and err.get("type") and err.get("message") and err.get("param") == param and err.get("code") == code
    check(name, ok, (s, r))


check_error("model なし -> 400", call("POST", "/v1/embeddings", {"input": "x"}), 400)
check_error("未知の model -> 404", embed("no-such-model", "x"), 404, code="model_not_found")
check_error("3-large（3072 次元）は扱わない -> 404", embed("text-embedding-3-large", "x"), 404, code="model_not_found")
check_error("input なし -> 400", call("POST", "/v1/embeddings", {"model": "text-embedding-ada-002"}), 400, param="input")
check_error("空文字の input -> 400", embed("text-embedding-ada-002", ""), 400, param="input")
check_error("空配列の input -> 400", embed("text-embedding-ada-002", []), 400, param="input")
check_error("トークン ID 配列 -> 400", embed("text-embedding-ada-002", [1734, 374]), 400, param="input")
check_error("ada-002 に dimensions -> 400", embed("text-embedding-ada-002", "x", dimensions=256), 400, param="dimensions")
check_error("dimensions が範囲外 -> 400", embed("text-embedding-3-small", "x", dimensions=5000), 400, param="dimensions")
check_error("encoding_format 不正 -> 400", embed("text-embedding-3-small", "x", encoding_format="int8"), 400, param="encoding_format")
check_error("壊れた JSON -> 400", call("POST", "/v1/embeddings", raw=b'{"model": "text-embedding-ada-002", "input": '), 400)
if API_KEY:
    check_error("API キーなし -> 401", call("POST", "/v1/embeddings", {"model": "text-embedding-ada-002", "input": "x"}, key=""), 401)
    check_error("誤った API キー -> 401", call("GET", "/v1/models", key="wrong-key"), 401, code="invalid_api_key")

print(f"\n{'OK' if not failures else 'NG'}: {len(failures)} failure(s)")
sys.exit(1 if failures else 0)
