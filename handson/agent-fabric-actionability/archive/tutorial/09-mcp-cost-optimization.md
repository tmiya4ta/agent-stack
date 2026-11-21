# 09 MCP Cost Optimization: ツールの説明のトークンを減らす

元のページ: [Lab 3: MCP Cost Optimization](https://develop-actionability.workshops.mulesoft.com/cost/cost-optimization.html) (モジュール 4)

## 目的

MCP のツールの説明は、毎回の呼び出しでモデルに送られてトークンを使う。2 つのやり方で減らす。

- **Tool Mapping**: LLM でツールの説明を短くする (意味は保つ)
- **Progressive Disclosure**: ツールの一覧を 2 つのメタツール (`search_tools`、`invoke_tool`) に替え、要るときだけ出す

## 演習 A: Tool Mapping

1. **Cost management** の **Top Opportunities** で、自分の MCP サーバ (手順書では `commerce-mcp-bridge-<イニシャル>`。
   ラボ 02 で付けた名前を探す) を選ぶ。
2. インスタンスの **View optimization** → MCP Tool Mapping の **Apply this Policy**。
3. **Import Tools → From Exchange** → `get_customers_customerid` と `post_orders` を選び **Optimize All**
   (手順書のツール名。ラボ 02 の名前と違うので、出ている名前に合わせる)。
4. **Apply Changes** → **Next** → **Apply Policy**。
5. MCP サーバを試し、減ったトークンを見る。

## 演習 B: Progressive Disclosure

1. 同じく **Top Opportunities** → 自分の MCP サーバ → **View optimization** → MCP Tools Progressive Disclosure の **Apply this Policy**。
2. (任意) よく使うツールを **Hot Tools** に入れると、一覧に残る。名前そのもの (`get_customers_customerid`) か glob (`list_*`)。
3. **Next** → **Apply Policy**。
4. MCP サーバ → インスタンス → **Policies** → **Reorder Policies** で、Progressive Disclosure を **MCP Support のすぐ下**にして **Save Order**。
   アクセス制御 (ラボ 03) より下に置くと、アクセス制御には `invoke_tool` しか見えず、止めたはずのツールを呼べてしまう。
5. MCP サーバを試し、一覧が `search_tools` と `invoke_tool` (と Hot Tools) だけになったことと、減ったトークンを見る。

## おまけ: Semantic Caching

同じ問いや言い換えには、保存した答えを返して LLM を呼ばない ([Bonus Topics](https://develop-actionability.workshops.mulesoft.com/cost/explore-more.html)、
[デモ](https://play.goconsensus.com/sf7b5f2d4))。ラボ 07 では OFF のまま。

## 実施メモ

- 減ったトークン (A / B):
- 気づいたこと:
