-- マックス証券 (架空) の業務データ。PostgreSQL 16 (k0 の max-core/max-pg、DB max)。
-- 正本はこのファイル。作り直すときは drop schema max cascade のあと、このファイルと seed.sql を流す (max-core の POST /admin/reset)。
-- 注意: Mule の execute-script で流すので、注釈に区切りの記号 (セミコロン) を書かない
-- 名前・銘柄・数値はすべて架空 (gen_seed.py が決まった乱数の種で作る)。実在の会社や人とは関係ない。

create schema if not exists max;
set search_path to max;

-- 顧客 (属性は適合性や審査の判断に使う)
create table customers (
  customer_id        text primary key,          -- C001..
  name               text not null,
  name_kana          text not null,
  birth_date         date not null,
  occupation         text not null,             -- 会社員、自営業、役員、無職 ..
  employer           text,                      -- 勤務先 (無職などは null)
  annual_income      bigint not null,           -- 円
  experience_years   int not null,              -- 投資経験 (年)
  risk_tolerance     text not null,             -- 低 / 中 / 高
  opened_on          date not null
);

-- 銘柄 (コードは実在の証券コードと重ならない MXnn)
create table instruments (
  code      text primary key,
  name      text not null,
  sector    text not null,
  market    text not null                       -- プライム / スタンダード / グロース
);

-- 日々の終値
create table prices (
  code        text not null references instruments(code),
  trade_date  date not null,
  close       numeric(12,1) not null,
  volume      bigint not null,                  -- 市場全体の出来高 (株)
  primary key (code, trade_date)
);

-- 約定 (v1 は静的な合成データ。v2 で注文の流れから入る)
create table trades (
  trade_id    text primary key,                 -- T000001..
  customer_id text not null references customers(customer_id),
  code        text not null references instruments(code),
  side        text not null check (side in ('買', '売')),
  qty         int not null,
  price       numeric(12,1) not null,
  trade_date  date not null,
  channel     text not null                     -- ネット / 対面 / コールセンター
);
create index trades_by_customer on trades (customer_id, trade_date);
create index trades_by_code on trades (code, trade_date);

-- 重要事実の公表 (適時開示)
create table announcements (
  announcement_id text primary key,             -- A001..
  code            text not null references instruments(code),
  published_at    timestamp not null,
  kind            text not null,                -- 公開買付け / 業務提携 / 決算 / 業績修正 ..
  title           text not null,
  price_move_pct  numeric(6,1) not null         -- 公表翌日の値動き (%)
);

-- 内部者の登録 (社内の登録簿: 顧客と銘柄の発行会社との関係)
create table insider_registry (
  customer_id   text not null references customers(customer_id),
  code          text not null references instruments(code),
  relation      text not null,                  -- 役員 / 社員 / 取引先の社員 / 親族 ..
  registered_on date not null,
  primary key (customer_id, code)
);

-- 審査のアラート (審査の点数付けのバッチが作る)
create table alerts (
  alert_id        text primary key,             -- SV-0001..
  kind            text not null,                -- インサイダー取引の疑い ..
  customer_id     text not null references customers(customer_id),
  code            text not null references instruments(code),
  announcement_id text references announcements(announcement_id),
  score           numeric(5,1) not null,        -- 0..100
  reasons         jsonb not null,               -- 点数の内訳 [{rule, points, detail}]
  raised_on       date not null,
  status          text not null default '未対応'  -- 未対応 / 調査中 / 承認待ち / 問題なし / 深掘り / 保留
);

-- 過去の審査の事例 (似た事例の検索に使う)
create table past_cases (
  case_id     text primary key,                 -- PC-01..
  kind        text not null,
  summary     text not null,
  decision    text not null,                    -- 問題なし / 深掘り / 保留 / 当局報告
  reason      text not null,
  decided_on  date not null
);

-- 調査の状態 (broker の会話ごと。contextId が鍵)
create table investigations (
  context_id     text primary key,
  alert_id       text references alerts(alert_id),
  step           text not null,                 -- new / awaiting_decision / decided
  recommendation text,
  memo           text,
  updated_at     timestamp not null default now()
);

-- 承認 (社員の最終確認。Salesforce の MaxApproval__c と対で持つ)
create table approvals (
  approval_id  text primary key,                -- AP-0001..
  kind         text not null,                   -- 売買審査 ..
  target_id    text not null,                   -- 対象 (アラート ID など)
  sf_id        text,                            -- Salesforce のレコード ID
  recommendation text not null,
  status       text not null default '承認待ち',  -- 承認待ち / 判断済み
  decision     text,                            -- 問題なし / 深掘り / 保留 ..
  note         text,
  decided_by   text,
  decided_at   timestamp,
  created_at   timestamp not null default now()
);

-- 監査ログ (誰が・何を・いつ。追記だけ)
create table audit_log (
  id      bigserial primary key,
  at      timestamp not null default now(),
  actor   text not null,                        -- system:surveillance / agent:surveillance-broker / user:<名前>
  action  text not null,
  target  text not null,
  detail  jsonb not null default '{}'
);
