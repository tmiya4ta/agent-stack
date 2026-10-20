%dw 2.0
// 問い合わせの窓口の部品 (乱数も時刻も使わない)。
// topFaq(text, faqs, n): 問い合わせの文と FAQ (質問と答え) の 2 文字の重なりで点を付け、上から n 件 ({faqId, category, question, answer, score})。
//   点 = 問い合わせの 2 文字の組のうち FAQ に出てくるものの割合 (小数 3 桁)。同じ点なら faqId の順。
// approvalRule(alerts, applications, text): 社員の承認が要るか ({requiresApproval, reasons})。エージェントの判断とは別の決まった守り:
//   - 売買審査のアラートがあるお客さま (審査中の事柄を窓口から話さない)
//   - 同じ名前と生年月日の申込みが断られたか確認中のお客さま
//   - 苦情の言葉 (責任者、苦情、クレーム、納得、説明して) を含む

var COMPLAINT = ["責任者", "苦情", "クレーム", "納得", "説明して"]

fun normalize(s: String): String = s replace /[\s、。，．,.!?！？「」()（）・]/ with ""

fun bigrams(s: String): Array<String> = do {
    var t = normalize(s)
    ---
    if (sizeOf(t) < 2) [] else ((0 to (sizeOf(t) - 2)) map ((i) -> t[i to (i + 1)])) distinctBy $
}

fun topFaq(text: String, faqs: Array, n: Number): Array = do {
    var q = bigrams(text)
    var scored = faqs map ((f) -> do {
        var body = normalize((f.question as String) ++ (f.answer as String))
        var hits = sizeOf(q filter ((b) -> body contains b))
        ---
        {faqId: f.faq_id, category: f.category, question: f.question, answer: f.answer,
         score: if (isEmpty(q)) 0 else round(hits * 1000 / sizeOf(q)) / 1000}
    })
    ---
    (scored orderBy ((f) -> ((9 - (f.score as Number)) as String {format: "0.000"}) ++ (f.faqId as String)))[0 to (n - 1)] default []
}

fun approvalRule(alerts: Array, applications: Array, text: String): Object = do {
    var reasons = [
        if (not isEmpty(alerts)) "売買審査のアラートがある (" ++ ((alerts map ($.alert_id as String)) joinBy ", ") ++ ")。審査中の事柄は窓口から話さない" else null,
        if (not isEmpty(applications)) "口座開設の申込みが " ++ ((applications map (($.application_id as String) ++ " " ++ ($.status as String))) joinBy ", ") else null,
        if (not isEmpty(COMPLAINT filter ((w) -> text contains w))) "苦情の言葉を含む (" ++ ((COMPLAINT filter ((w) -> text contains w)) joinBy ", ") ++ ")" else null
    ] filter ($ != null)
    ---
    {requiresApproval: not isEmpty(reasons), reasons: reasons}
}
