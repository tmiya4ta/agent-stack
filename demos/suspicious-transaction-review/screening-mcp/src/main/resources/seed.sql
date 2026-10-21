DROP TABLE IF EXISTS watchlist;
DROP TABLE IF EXISTS news;
CREATE TABLE watchlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT, list_name TEXT, entity_type TEXT, name TEXT, name_key TEXT,
  birth_date TEXT, country TEXT, reason TEXT, listed_on TEXT);
CREATE TABLE news (
  id INTEGER PRIMARY KEY AUTOINCREMENT, published_on TEXT, source TEXT, title TEXT, body TEXT, names TEXT);

-- Every entry below is fictitious.
INSERT INTO watchlist (list_name, entity_type, name, name_key, birth_date, country, reason, listed_on) VALUES
('経済制裁対象者リスト（架空）','個人','Viktor Stanek','VIKTORSTANEK','1968-02-11','架空国 A','資産凍結措置の対象','2024-03-01'),
('経済制裁対象者リスト（架空）','法人','Northwind Maritime Holdings','NORTHWINDMARITIMEHOLDINGS',NULL,'架空国 A','制裁対象者が支配する法人','2024-03-01'),
('外国の重要な公人（PEP）リスト（架空）','個人','Aleksandr Morin','ALEKSANDRMORIN','1961-07-30','架空国 B','元政府高官','2023-01-15'),
('行内要注意取引先リスト','法人','Golden Harbor Trading Ltd','GOLDENHARBORTRADINGLTD',NULL,'香港','2025 年に別顧客の疑わしい取引の届出で送金先として記載','2025-11-20'),
('行内要注意取引先リスト','個人','黒田 隆之','黒田隆之','1981-05-09','日本','2024 年に口座不正利用で取引停止','2024-08-02');

INSERT INTO news (published_on, source, title, body, names) VALUES
('2026-07-14','東都日報（架空）','投資詐欺の疑いで 42 歳の男を逮捕 大阪府警',
 '大阪府警は 13 日、架空の投資話で計約 8,000 万円をだまし取ったとして、大阪市住之江区の無職、森本翔太容疑者（42）を詐欺の疑いで逮捕した。',
 '森本翔太'),
('2025-11-18','経済アジア通信（架空）','香港の貿易会社経由で不正送金か 警視庁が実態解明へ',
 '警視庁は、国内の複数の個人口座から香港の貿易会社「Golden Harbor Trading」に送金された資金の一部が、特殊詐欺の被害金だった可能性があるとみて調べている。同社は取材に応じていない。',
 'GOLDENHARBORTRADING'),
('2026-03-02','みなと経済新聞（架空）','みなと物産、今期も決算賞与を支給 業績好調で',
 '総合商社の株式会社みなと物産は、今期も 8 月末に全社員へ決算賞与を支給すると発表した。',
 'みなと物産'),
('2026-05-20','東都日報（架空）','飲食店の現金売上、キャッシュレス化で減少傾向',
 '都内の飲食店では、キャッシュレス決済の普及で現金売上の比率が年々下がっている。',
 '');
