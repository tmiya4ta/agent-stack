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

-- 承認 (社員の最終確認。Salesforce の MaxApproval__c と対で持つ)。ID は AP-0001 から
create sequence approval_seq;
create table approvals (
  approval_id  text primary key,                -- AP-0001..
  kind         text not null,                   -- 売買審査 ..
  target_id    text not null,                   -- 対象 (アラート ID など)
  context_id   text,                            -- 調査した会話 (investigations)
  sf_id        text,                            -- Salesforce のレコード ID
  recommendation text not null,                 -- 問題なし / 深掘り / 保留 / 当局報告
  memo         text not null,                   -- 調査メモ (エージェントの下書き)
  requested_by text not null,                   -- agent:max-surveillance など
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

-- 仮想の業務時計 (1 行だけ)。業務の日付はいつもここから読む (壁の時計の now() は監査ログの時刻にだけ使う)
create table business_clock (
  id          int primary key default 1 check (id = 1),
  today       date not null,
  auto        boolean not null default false,   -- 自動で進めるか (POST /clock/auto)
  auto_until  date,                             -- 自動で進めるのはこの日まで (null なら限りなく)
  busy        boolean not null default false,   -- 進めている最中 (手と自動が重ならないように)
  busy_since  timestamp                         -- busy にした時刻 (10 分より古い印は、止まったプロセスの残りとして取り直せる)
);

-- これから公表される重要事実 (時計がその日に進むと announcements に移る)
create table planned_events (
  announcement_id text primary key,             -- A101..
  code            text not null references instruments(code),
  published_at    timestamp not null,
  kind            text not null,
  title           text not null,
  price_move_pct  numeric(6,1) not null
);

-- 仕込んだ注文 (時計がその日に進むと、その日の終値で約定する)
create table planned_orders (
  customer_id text not null references customers(customer_id),
  code        text not null references instruments(code),
  side        text not null check (side in ('買', '売')),
  qty         int not null,
  trade_date  date not null,
  primary key (customer_id, code, side, trade_date)
);

-- 注文 (max-oms が受け、その日の終値で約定させる。約定は Anypoint MQ で台帳 (trades) に届く)
create table orders (
  order_id    text primary key,                 -- O26101200001..
  customer_id text not null references customers(customer_id),
  code        text not null references instruments(code),
  side        text not null check (side in ('買', '売')),
  qty         int not null,
  trade_date  date not null,
  price       numeric(12,1) not null,
  channel     text not null,
  trade_id    text not null,                    -- 約定の ID (T261012001..)
  created_at  timestamp not null default now()
);

-- 口座開設の申込み (時計がその日に進むと planned_applications から届く)。規則で問題が無ければ口座を開き、
-- 引っかかれば口座開設の broker が調べて承認箱に回す
create table applications (
  application_id     text primary key,          -- OA-0001..
  name               text not null,
  name_kana          text not null,
  birth_date         date not null,
  occupation         text not null,
  employer           text,
  annual_income      bigint not null,
  experience_years   int not null,
  risk_tolerance     text not null,             -- 希望するリスク: 低 / 中 / 高
  planned_investment bigint not null,           -- 最初に入れるつもりの金額 (円)
  applied_on         date not null,
  status             text not null default '受付', -- 受付 / 口座開設 / 確認待ち / 承認待ち / 否認 / 追加確認
  findings           jsonb not null default '[]', -- 規則の引っかかり [{rule, detail}]
  customer_id        text references customers(customer_id)
);

create table planned_applications (
  application_id     text primary key,
  name               text not null,
  name_kana          text not null,
  birth_date         date not null,
  occupation         text not null,
  employer           text,
  annual_income      bigint not null,
  experience_years   int not null,
  risk_tolerance     text not null,
  planned_investment bigint not null,
  applied_on         date not null
);

-- 社内の要注意リスト (口座開設の照合に使う)
create table watchlist (
  entry_id    text primary key,                 -- W01..
  name        text not null,
  birth_date  date,
  reason      text not null,
  listed_on   date not null
);
