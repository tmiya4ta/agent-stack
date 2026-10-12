# マックス証券 (架空)

社員は最後の承認だけをし、ほかは規則による自動処理 (STP) とエージェントが受け持つ、架空のネット証券のデモ。
名前・会社・銘柄・数値はすべて架空で、合成データ (`db/gen_seed.py`、決まった乱数の種) から作る。実在の会社や人とは関係ない。

## v1: 売買審査の縦の通し (2026-10-12 に通しで動いた)

```
max-core (mulay、k0 の max-core)                         Agent Network (T1/Sandbox、ft1)          Salesforce d30
  POST /surveillance/run  点数付け → アラート
    └─ dispatch: A2A 1.0 SendMessage (JWT HS256) ──────▶ max-surveillance-broker
                                                          classify → investigate (get-alert)
  MCP (8082、mcp-surveillance.max.theorems.dev) ◀──────── → executor request-approval ──────────────▶ 承認依頼 (MaxApproval__c)
    request-approval: 調査メモを組み立て、承認箱に依頼                                                 社員が「判断」を選ぶ
  approvals-poll (30 秒ごと) ◀──────────────────────────────────────────────────────────────────── 判断済みの依頼
    判断を記録 (アラートの状態、調査、監査ログ)
```

1. **max-core** (`core/`、System API。mulay で k0 の max-core に置く): 合成データの上で審査の点数付けを回し、アラートを作る。
   作ったアラートは調査エージェントに回す (社員はチャットで頼まない)
2. 調査エージェント (`networks/max-surveillance`、AgentScript v2): get-alert を 1 回で調べ、推奨を下書きし、executor が承認箱に依頼する。
   LLM はデモのプロキシ (OpenAI 互換、gpt-5-mini)。手元の LLM では判断が安定しなかった (k0/README.md)
3. 承認箱 (`salesforce/`、d30 のカスタムオブジェクト「承認依頼」): 社員が推奨と調査メモを見て判断する
4. max-core が 30 秒ごとに判断を取り込み、監査ログに残す (エージェントの依頼と社員の判断の両方)

### デモの回し方

```bash
cd ~/mule/agents/agent-stack
k0/max-core/secrets.sh && k0/max-core/build.sh            # 秘密とイメージ (中身を変えたら VERSION と yaml の image を上げる)
kubectl --context kind-k0 apply -f k0/max-core/max-core.yaml
yc harness deploy <T1> <Sandbox> max-demo                   # broker (yc の変数のプロファイル max)
# データを最初からにする: max-pg に max/db/schema.sql と seed.sql を流す (README の「データ」)。承認箱の AP-* も消す
kubectl --context kind-k0 -n max-core port-forward svc/max-core 18081:80 &
curl -X POST -H "Authorization: Bearer $API_KEY" http://127.0.0.1:18081/surveillance/run   # 1〜2 分で承認箱に 3 件
```

API_KEY は `~/.config/max-core/env`。broker にチャットで話しかけることもできる (A2A 1.0、JWT の sub は会話の持ち主)。

v2 で、注文の流れ・模擬の市場・仮想の業務時計・Anypoint MQ を足す。

## データ (`db/`)

- `schema.sql` が正本。`seed.sql` は `python3 db/gen_seed.py > db/seed.sql` で作る (手で直さない)。
- max-core の資源 `max/schema.sql`・`max/seed.sql` はここへの symlink。`POST /admin/reset` (`admin.reset=true` のときだけ) で流し直す。
- k0 では max-core 名前空間の max-pg (PostgreSQL 16、DB max、利用者 max_app。鍵は `~/.config/max-db/env`、Secret max-db)。
  ホストからは `kubectl --context kind-k0 -n max-core port-forward svc/max-pg 15433:5432`。

### 仕込んだ筋書き

| 顧客 | 銘柄 | 公表 | 中身 | 点 | 想定する判断 |
|---|---|---|---|---|---|
| C017 西田 亮 (蒼穹商事の社員) | MX07 白樺化学 | A005 公開買付け 2026-09-25 | 取引先の社員 (内部者の登録あり) が、初めての銘柄を公表前に約 716 万円買い、公表後に売った | 100 | 当局報告 (過去の PC-01 と同じ形) か深掘り |
| C011 柴田 浩二 (自営業) | MX21 常磐バイオ | A009 業務提携 2026-10-02 | 公表の 2 日前に初めての銘柄を約 679 万円買った。登録上の関係は無い | 75 | 保留 (本人への聞き取り) |
| C004 遠藤 拓也 (会社員) | MX12 汐見エナジー | A008 上方修正 2026-10-05 | 毎月最初の営業日の積み立て (100 株) が、公表の前に当たっただけ | 30 | 問題なし |

エージェントの推奨は下書きで、回ごとに揺れることがある (2026-10-12 の 2 回: SV-0001 は 2 回とも当局報告、SV-0002 は 2 回とも保留、
SV-0003 は保留 → 問題なし)。判断するのは承認箱の社員。

## 審査の点数 (`core/src/main/resources/max/score.dwl`)

値動きが 3% 以上の公表ごとに、値動きの向きに合う売買を公表の前 5 営業日にした顧客を拾い、次の点を足す (上限 100、30 点以上でアラート)。

| 規則 | 点 |
|---|---|
| 公表前の売買 | 30 |
| 初めての銘柄 | 20 |
| 普段との差 (直前 60 営業日の 1 回の平均の 5 倍以上 / 2 倍以上 / 直前に売買が無い) | 25 / 10 / 25 |
| 内部者の登録あり | 25 |
| 公表後 5 営業日以内の反対売買 | 10 |

## 試験

```bash
cd ~/projects/mulay
tools/mule-oracle/mule-oracle fill  ~/mule/agents/agent-stack/max/core/scenario.scn   # 実 Mule で期待値を取る
tools/mule-oracle/mule-oracle mulay ~/mule/agents/agent-stack/max/core/scenario.scn   # mulay で照合する
```

DB は mulay の試験用の PG (localhost:15432、スキーマ max) を使う。
