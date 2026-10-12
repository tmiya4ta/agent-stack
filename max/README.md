# マックス証券 (架空)

社員は最後の承認だけをし、ほかは規則による自動処理 (STP) とエージェントが受け持つ、架空のネット証券のデモ。
名前・会社・銘柄・数値はすべて架空で、合成データ (`db/gen_seed.py`、決まった乱数の種) から作る。実在の会社や人とは関係ない。

## v1: 売買審査の縦の通し

1. **max-core** (`core/`、System API。mulay で k0 の max-core に置く): 合成データの上で審査の点数付けを回し、アラートを作る
2. 調査エージェント (Agent Network の broker): MCP の道具でアラートを調べ、調査メモと推奨を下書きする
3. 承認箱 (Salesforce d30): 社員が推奨を見て判断する
4. 判断を max-core に戻し、監査ログに残す

v2 で、注文の流れ・模擬の市場・仮想の業務時計・Anypoint MQ を足す。

## データ (`db/`)

- `schema.sql` が正本。`seed.sql` は `python3 db/gen_seed.py > db/seed.sql` で作る (手で直さない)。
- max-core の資源 `max/schema.sql`・`max/seed.sql` はここへの symlink。`POST /admin/reset` (`admin.reset=true` のときだけ) で流し直す。
- k0 では max-core 名前空間の max-pg (PostgreSQL 16、DB max、利用者 max_app。鍵は `~/.config/max-db/env`、Secret max-db)。
  ホストからは `kubectl --context kind-k0 -n max-core port-forward svc/max-pg 15433:5432`。

### 仕込んだ筋書き

| 顧客 | 銘柄 | 公表 | 中身 | 点 | 想定する判断 |
|---|---|---|---|---|---|
| C017 西田 亮 (蒼穹商事の社員) | MX07 白樺化学 | A005 公開買付け 2026-09-25 | 取引先の社員 (内部者の登録あり) が、初めての銘柄を公表前に約 716 万円買い、公表後に売った | 100 | 深掘り |
| C011 柴田 浩二 (自営業) | MX21 常磐バイオ | A009 業務提携 2026-10-02 | 公表の 2 日前に初めての銘柄を約 679 万円買った。登録上の関係は無い | 75 | 保留 (本人への聞き取り) |
| C004 遠藤 拓也 (会社員) | MX12 汐見エナジー | A008 上方修正 2026-10-05 | 毎月最初の営業日の積み立て (100 株) が、公表の前に当たっただけ | 30 | 問題なし |

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
