"""aisearch-server の HTTP スモークテスト（標準ライブラリのみ）。

  API_KEY=<key> python3 smoke_test.py http://172.23.0.1:8897            # 動いているサーバに対して
  API_KEY=<key> python3 smoke_test.py http://127.0.0.1:18897 --concurrency  # 並行登録も試す

テスト用のインデックス smoke-<乱数> を作って最後に消す。
"""
import json
import math
import os
import random
import sys
import threading
import urllib.error
import urllib.request

BASE = sys.argv[1].rstrip("/")
KEY = os.environ.get("API_KEY", "")
API = "api-version=2024-07-01"
DIMS = 8
failures = 0


def call(method, path, body=None, key=KEY):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if key:
        headers["api-key"] = key
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"{BASE}{path}{sep}{API}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw and r.headers.get_content_type() == "application/json" else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def check(label, ok, detail=""):
    global failures
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  {detail}"))
    if not ok:
        failures += 1


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


name = f"smoke-{random.randint(100000, 999999)}"
index = {
    "name": name,
    "fields": [
        {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
        {"name": "prompt", "type": "Edm.String", "searchable": True},
        {"name": "partition", "type": "Edm.String", "filterable": True},
        {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True,
         "dimensions": DIMS, "vectorSearchProfile": "vp"},
    ],
    "vectorSearch": {
        "algorithms": [{"name": "hnsw1", "kind": "hnsw", "hnswParameters": {"metric": "cosine"}}],
        "profiles": [{"name": "vp", "algorithm": "hnsw1"}],
    },
}

if KEY:
    s, b = call("GET", "/indexes", key="")
    check("api-key なし -> 403", s == 403, s)
    s, b = call("GET", "/indexes", key="wrong")
    check("違う api-key -> 403", s == 403, s)

s, b = call("PUT", f"/indexes('{name}')", index)
check("PUT index -> 201", s == 201, (s, b))
s, b = call("POST", "/indexes", index)
check("POST 既存 -> 409", s == 409, (s, b))
s, b = call("GET", f"/indexes/{name}")
check("GET index", s == 200 and b.get("name") == name and "@odata.etag" in b, (s, b))
s, b = call("GET", "/indexes/does-not-exist")
check("無いインデックス -> 404", s == 404 and "error" in b, (s, b))

base = [random.random() for _ in range(DIMS)]
near = [x + random.uniform(-0.01, 0.01) for x in base]
far = [random.random() for _ in range(DIMS)]
docs = [
    {"@search.action": "upload", "id": "hit", "prompt": "注文の配送状況を教えて", "partition": "p1", "embedding": base},
    {"@search.action": "upload", "id": "other", "prompt": "天気", "partition": "p1", "embedding": far},
    {"@search.action": "mergeOrUpload", "id": "p2doc", "prompt": "注文", "partition": "p2", "embedding": base},
]
s, b = call("POST", f"/indexes/{name}/docs/index", {"value": docs})
check("docs/index -> 200", s == 200 and all(v["status"] for v in b["value"]), (s, b))

q = {"count": True, "select": "id,prompt",
     "vectorQueries": [{"kind": "vector", "vector": near, "fields": "embedding", "k": 1}],
     "filter": "partition eq 'p1'"}
s, b = call("POST", f"/indexes/{name}/docs/search", q)
ok = s == 200 and len(b["value"]) == 1 and b["value"][0]["id"] == "hit"
check("ベクトル検索 k=1 + filter", ok, (s, b))
if ok:
    cos = sum(x * y for x, y in zip(unit(near), unit(base)))
    want = 1 / (1 + (1 - cos))
    got = b["value"][0]["@search.score"]
    check("@search.score = 1/(1+(1-cos))", abs(got - want) < 1e-9, (got, want))
    check("select で embedding を返さない", "embedding" not in b["value"][0], b["value"][0])

s, b = call("GET", f"/indexes/{name}/docs/$count")
check("$count = 3", s == 200 and str(b).strip() == "3", (s, b))
s, b = call("GET", f"/indexes/{name}/docs('hit')")
check("1 件取得", s == 200 and b.get("id") == "hit", (s, b))
s, b = call("POST", f"/indexes/{name}/docs/index", {"value": [{"id": "bad", "embedding": [1.0, 2.0]}]})
check("次元違い -> 400", s == 400, (s, b))
s, b = call("POST", f"/indexes/{name}/docs/search", {"filter": "partition eq"})
check("壊れた filter -> 400", s == 400, (s, b))

if "--concurrency" in sys.argv:
    n_threads, per = 8, 25

    def worker(t):
        for i in range(per):
            call("POST", f"/indexes/{name}/docs/index",
                 {"value": [{"id": f"c{t}-{i}", "partition": "c", "embedding": [random.random() for _ in range(DIMS)]}]})

    th = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for x in th:
        x.start()
    for x in th:
        x.join()
    s, b = call("GET", f"/indexes/{name}/docs/$count")
    check(f"並行登録 {n_threads}x{per} で更新が消えない", str(b).strip() == str(3 + n_threads * per), b)

if "--keep" not in sys.argv:
    s, b = call("DELETE", f"/indexes/{name}")
    check("DELETE index -> 204", s == 204, (s, b))
else:
    print(f"(kept index {name})")

print(f"\n{'OK' if failures == 0 else 'NG'}: {failures} failure(s)")
sys.exit(1 if failures else 0)
