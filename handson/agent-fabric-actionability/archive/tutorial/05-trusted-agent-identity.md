# 05 Trusted Agent Identity: OBO で利用者の身元を運ぶ

元のページ: [Trusted Agent Identity](https://develop-actionability.workshops.mulesoft.com/govern/trusted-agent-identity.html) (モジュール 3)

## 目的

broker が利用者に代わってツールを呼ぶとき、共有のサービスアカウントではなく、その利用者の身元で呼ぶ。
仕組みは On-Behalf-Of (OBO) のトークン交換 (RFC 8693): ゲートウェイがログインのトークンを、`sub` はそのままで、
行き先 (audience) を Commerce MCP だけに絞り、期限を短くした新しいトークンに替える。

## 手順 1: 設定を見る

1. **MCP Servers** で `commerce mcp` を探し、**Commerce MCP Server** → **Instances** → インスタンスの ID。
2. **Credential Injection OAuth2 OBO** のポリシーを開く。

| 項目 | 値 | 意味 |
|---|---|---|
| Token Exchange Flow | oauth2-token-exchange | RFC 8693 |
| Target Type / Value | audience → `commerce-mcp-obo` | 新しいトークンは Commerce MCP でだけ使える |
| Client ID / Secret | OBO の機密クライアント | IdP が交換を許している相手 |
| Token Endpoint | Keycloak の token の URL | ここで交換する |
| Scope | openid | |

outbound のポリシー (ゲートウェイから Commerce MCP へ出る要求にかかる)。アプリのコードは交換に関わらない。

## 手順 2: 動きを見る

1. Multi-Agent Orchestrator で今のペルソナから出て、**Jamie Torres** で入る。
2. 1 つ目の問い「Check order ORD-2026-00003 (Jamie's own order).」を押す (毎回の顧客の情報の取得で OBO が起きる)。
3. **Identity** タブで 2 つのトークンを比べる (**Show raw token** の値を jwt.io で読める)。

| claim | 受け取ったトークン | 交換後のトークン |
|---|---|---|
| username | jamie.torres | 同じ |
| sub | Jamie の UUID | 同じ |
| aud | いくつもの相手 | `commerce-mcp-obo` だけ |
| azp | vogue-ui | commerce-mcp-obo |
| exp | ログインから約 30 分 | もっと短い |

4. 2 つ目の問い「Check order ORD-2026-00002 (another customer's order).」を押す。他人の注文なので Commerce MCP は返さない
   (「見つからない」になる)。broker に送られる問いは `Check the status of order ORD-2026-0000X` だけで、持ち主のことは
   書かれていない。決めているのは交換後のトークンの身元だけ。
5. **Ashley Grover** で同じ ORD-2026-00002 を聞くと返る (データは同じで、身元が違う)。

## 読むだけ: In-Task Authorization

お金を動かすなど危ない操作では、A2A のエージェントが途中で止まって利用者に確認を求められる (このワークショップでは設定しない)。
[In-Task Authorization のドキュメント](https://docs.mulesoft.com/gateway/latest/policies-outbound-a2a-intask-authorization-code)、
[OBO のポリシーのドキュメント](https://docs.mulesoft.com/gateway/latest/policies-outbound-oauth-obo)。

## 実施メモ

- 気づいたこと:
