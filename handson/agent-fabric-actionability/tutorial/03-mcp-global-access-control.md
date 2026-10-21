# 03 MCP Global Access Control: ツールをゲートウェイで隠す

元のページ: [Lab 1: Govern an MCP](https://develop-actionability.workshops.mulesoft.com/action/mcp-global-access-control.html) (モジュール 2)

## 目的

ラボ 02 の Commerce MCP から、注文を作るツール `order-rest-api_createOrder` を、API に手を入れずにゲートウェイで止める。
止めたツールは tools/list から消え (エージェントからは見えない)、直接呼んでも JSON-RPC のエラーになる。
他社の MCP を統制するときも同じやり方 (コードではなく通り道で決める)。

## 手順

1. 統制の前: MCP タブで自分のサーバにつなぎ、ツールが 6 つ (`order-rest-api_createOrder` を含む) あることを確かめる。
2. 自分の MCP サーバの **Instances** → インスタンスの ID → **Apply Policy** → **MCP Global Access Control** → Next。
3. ルールを 1 つ足して **Apply Policy**: Rule Block、Match Type literal、Value `order-rest-api_createOrder`
   (ツール名は Bridge の設定で決まるので、MCP タブに出ている名前をそのまま使う)。
4. **Reorder Instance Policies** で MCP Global Access Control を **2 番目**にして **Save Order**:

| 順 | ポリシー |
|---|---|
| 1 | MCP Support |
| 2 | MCP Global Access Control |
| 3 | MCP Schema Validation |
| 4 | MCP Payload Optimization |
| 5 | MCP Transcoding Router |
| 6、7 | MCP Transcoding |

## 確かめること

MCP タブで **Disconnect** → **Connect** し直すと、ツールが 5 つになり `order-rest-api_createOrder` が無い。

## つまずき

| 症状 | 直し |
|---|---|
| 一覧に残り、呼ぶと `{}` が返る | 順番が違う。Global Access Control を MCP Support のすぐ下 (Schema Validation と Transcoding Router より上) にする |
| まったく効かない | Value がツール名と完全に同じか、Match Type が literal か |
| 一覧が変わらない | Disconnect → Connect で tools/list を取り直す |

## ほかの MCP のポリシー

| ポリシー | 何を決めるか |
|---|---|
| MCP Global Access Control | このラボ。出す・呼べるツールの許可と拒否 |
| MCP Attribute-Based Access Control | 呼び手ごとのツールの組 (Cedar の式) |
| MCP PII Detector | 応答の個人情報を見つけて、記録・伏せ字・拒否 |
| MCP Payload Optimization | 応答を縮めてトークンを減らす (費用のため) |

## 実施メモ

- 気づいたこと:
