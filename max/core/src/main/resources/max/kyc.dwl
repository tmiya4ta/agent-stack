%dw 2.0
// 口座開設の申込みの規則 (乱数も時刻も使わない。asOf は業務日)。引っかかりが無ければ、人もエージェントも通さずに口座を開く。
// check(app, customers, watchlist, asOf) → {result: "pass" | "exception", findings: [{rule, detail}]}
//   app        {name, birth_date ("yyyy-MM-dd"), occupation, annual_income, experience_years, risk_tolerance, planned_investment}
//   customers  [{customer_id, name, birth_date}] (既存のお客さま)
//   watchlist  [{entry_id, name, birth_date (null 可), reason}]
// 規則:
//   適合性        80 歳以上で希望リスクが「高」、または投資経験が 0 年で希望リスクが「高」
//   資金の出どころ  入れる予定の金額が年収の 3 倍を超える
//   要注意リスト    名前が一致するか、空白を除いて一方が他方を含む (生年月日が合うかも書く)
//   重複の申込み    既存のお客さまと名前と生年月日が同じ

fun age(birth: String, asOf: String): Number = do {
    var b = birth as Date
    var d = asOf as Date
    var years = d.year - b.year
    ---
    if ((d.month * 100 + d.day) < (b.month * 100 + b.day)) years - 1 else years
}

fun squash(s: String): String = s replace /\s+/ with ""

fun yen(n: Number): String = (n as String {format: "#,##0"}) ++ " 円"

fun check(app: Object, customers: Array, watchlist: Array, asOf: String): Object = do {
    var years = age(app.birth_date as String, asOf)
    var n = squash(app.name as String)
    var listed = watchlist filter ((w) -> do {
        var m = squash(w.name as String)
        ---
        (m == n) or (m contains n) or (n contains m)
    })
    var dups = customers filter ((c) -> squash(c.name as String) == n and (c.birth_date as String) == (app.birth_date as String))
    var findings = [
        if (years >= 80 and app.risk_tolerance == "高")
            {rule: "適合性", detail: (years as String) ++ " 歳で、希望するリスクが「高」"} else null,
        if (app.experience_years == 0 and app.risk_tolerance == "高")
            {rule: "適合性", detail: "投資経験が無く、希望するリスクが「高」"} else null,
        if (app.planned_investment > app.annual_income * 3)
            {rule: "資金の出どころ", detail: "入れる予定の金額 " ++ yen(app.planned_investment) ++ " が年収 " ++ yen(app.annual_income) ++ " の 3 倍を超える"} else null
    ] ++ (listed map ((w) -> {rule: "要注意リスト",
            detail: w.entry_id ++ " " ++ w.name ++ " に" ++ (if (squash(w.name as String) == n) "一致" else "部分一致") ++ "。生年月日は"
                    ++ (if (w.birth_date == null) "リストに無い" else if ((w.birth_date as String) == (app.birth_date as String)) "一致" else "不一致 (リストは " ++ (w.birth_date as String) ++ ")")
                    ++ "。理由: " ++ w.reason}))
      ++ (dups map ((c) -> {rule: "重複の申込み", detail: "既存のお客さま " ++ c.customer_id ++ " と名前と生年月日が同じ"}))
    var hits = findings filter ($ != null)
    ---
    {result: if (isEmpty(hits)) "pass" else "exception", age: years, findings: hits}
}
