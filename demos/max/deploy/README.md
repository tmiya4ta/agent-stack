# max-core / max-oms を Runtime Manager から RTF (k0) に配備する

2026-10-12 から、マックス証券の業務アプリは Anypoint のコントロールプレーンで配備している (それまでは k8s の Deployment を直接置いていた)。
中身は実 Mule ではなく mulay で動く。k0 のノードに、Anypoint の一覧にあるランタイム名 **4.9.22:8-java17** で mulay のイメージを載せてある
(ARIADNE が使う 4.9.21:4-java17 とは別にして、版を別々に上げられるようにした)。仕組みは theorems-infra の
`cluster/rtf-custom-runtime/README.md`、イメージは mulay の `deploy/Dockerfile.rtf`。

| | 中の API (Service :8081) | 外に出す口 (Service :8082) | 公開 |
|---|---|---|---|
| max-core | 業務の API (/clock、/approvals ..) | MCP 3 つ (/k/<鍵>/mcp、ops/mcp、support/mcp) | mcp-surveillance.max.theorems.dev/k/ |
| max-oms | 注文の API (max-core が呼ぶ) | 注文の画面 (/k/<鍵>/) | order.max.theorems.dev/k/ |

- 環境: T1 / Sandbox (名前空間 `0f678523-c036-4098-9be9-cc542dca2e6d`)。DB は max-core 名前空間の max-pg をそのまま使う。
- `build-jar.sh core|oms`: 秘密のファイルを値の無い代わりにした複製から jar を作る (jar に秘密は入らない)。
- `deploy.sh core|oms <版>`: Exchange に上げて配備する。秘密の値は鍵のファイルから読み、安全なプロパティで渡す
  (RTF は Secret に入れ、設定には `file:///opt/mule/secrets/<id>` と書く。mulay のイメージの entrypoint がそれを読む)。
  yc の要求の記録に残らないよう YC_NO_OPLOG=1。配備のプロパティはアプリのファイルの値に勝つ。
- `routes.yaml`: 公開の経路。Anypoint の公開 URL は使わない (1 つのポートにしか流せない、鍵の経路が Anypoint に平文で残る、15 秒で切れる)。
- mulay を上げるとき: mulay で `docker build -f deploy/Dockerfile.rtf -t mulay-rtf:<hash> .`、ノードの 4.9.22:8-java17 を消してから
  theorems-infra の `build-and-load.sh --image mulay-rtf:<hash> 4.9.22:8-java17` で載せ、Pod を作り直す。ノードを作り直したら載せ直す。
