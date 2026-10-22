"""ハンズオンの環境ごとの URL とクレデンシャルを、1 枚の HTML にまとめる。値は git の外に置く。

    ~/.config/handson/<handson>/<env>/env.json     値 (このスクリプトは読むだけ)
    ~/.config/handson/<handson>/<env>/index.html   環境ごとのページ
    ~/.config/handson/index.html                   全部の環境の一覧 (デスクトップのショートカットの先)

    python env_page.py                 # 全部の env.json から HTML を作り直す
    python env_page.py --shortcut      # ついでにデスクトップに「handson 環境」のショートカットを作る

env.json の形:

    {"handson": "new-hire-onboarding", "env": "20261029-acme", "customer": "Acme", "date": "2026-10-29",
     "note": "...", "status": "active",
     "sections": [{"title": "Anypoint の管理者",
                   "items": [{"label": "ユーザー名", "value": "..."},
                             {"label": "パスワード", "value": "...", "secret": true},
                             {"label": "URL", "value": "https://...", "link": true}]}]}

status は active (使っている) か done (片付けた)。done は一覧の下にまとまる。
"""
import argparse
import html
import json
import os
import subprocess

ROOT = os.path.join(os.path.expanduser('~'), '.config', 'handson')

STYLE = """
:root { --bg:#f6f7f9; --card:#fff; --ink:#1d2330; --mute:#6b7280; --line:#e3e6eb; --accent:#0b5cad; --ok:#1f7a4d; --done:#9aa1ad; }
@media (prefers-color-scheme: dark) { :root { --bg:#14171c; --card:#1c2028; --ink:#e6e9ee; --mute:#9aa3b2; --line:#2c323d; --accent:#6fb1ff; --ok:#5cc08d; --done:#5f6673; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:14px/1.5 "Segoe UI","Yu Gothic UI","Hiragino Sans",sans-serif; }
main { max-width:980px; margin:0 auto; padding:28px 20px 60px; }
h1 { font-size:22px; margin:0 0 4px; }
.sub { color:var(--mute); margin:0 0 20px; }
.note { background:var(--card); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:8px; padding:10px 14px; margin:0 0 18px; white-space:pre-wrap; }
section { background:var(--card); border:1px solid var(--line); border-radius:10px; margin:0 0 14px; overflow:hidden; }
section h2 { font-size:14px; margin:0; padding:10px 14px; border-bottom:1px solid var(--line); }
table { width:100%; border-collapse:collapse; }
td { padding:7px 14px; border-top:1px solid var(--line); vertical-align:top; }
tr:first-child td { border-top:0; }
td.k { width:220px; color:var(--mute); }
td.v { font-family:"Cascadia Mono",Consolas,monospace; font-size:13px; word-break:break-all; }
td.a { width:120px; text-align:right; white-space:nowrap; }
a { color:var(--accent); text-decoration:none; } a:hover { text-decoration:underline; }
button { font:12px "Segoe UI",sans-serif; border:1px solid var(--line); background:transparent; color:var(--ink); border-radius:6px; padding:2px 8px; cursor:pointer; margin-left:4px; }
button:hover { border-color:var(--accent); color:var(--accent); }
.mask { letter-spacing:2px; color:var(--mute); }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:12px; margin:0 0 24px; }
.env { display:block; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; color:var(--ink); }
.env:hover { border-color:var(--accent); text-decoration:none; }
.env b { display:block; font-size:15px; } .env span { color:var(--mute); }
.tag { display:inline-block; font-size:11px; border-radius:10px; padding:0 8px; margin-left:6px; color:#fff; background:var(--ok); }
.tag.done { background:var(--done); }
h3 { font-size:13px; color:var(--mute); margin:18px 0 8px; font-weight:600; }
"""

SCRIPT = """
function copyText(btn, text) {
  navigator.clipboard.writeText(text).then(() => { const t = btn.textContent; btn.textContent = 'コピーした'; setTimeout(() => btn.textContent = t, 1200); });
}
function toggle(btn) {
  const cell = btn.closest('tr').querySelector('td.v');
  const shown = cell.dataset.shown === '1';
  cell.textContent = shown ? '••••••••' : cell.dataset.value;
  cell.classList.toggle('mask', shown);
  cell.dataset.shown = shown ? '0' : '1';
  btn.textContent = shown ? '表示' : '隠す';
}
"""


def esc(s):
    return html.escape(str(s), quote=True)


def page(title, body):
    return (f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>{esc(title)}</title>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{STYLE}</style></head>'
            f'<body><main>{body}</main><script>{SCRIPT}</script></body></html>')


def env_html(env):
    head = f'<p><a href="../../index.html">← 環境の一覧</a></p><h1>{esc(env["handson"])} / {esc(env["env"])}</h1>'
    meta = ' · '.join(x for x in (env.get('customer'), env.get('date'), env.get('status')) if x)
    out = [head, f'<p class="sub">{esc(meta)}</p>']
    if env.get('note'):
        out.append(f'<div class="note">{esc(env["note"])}</div>')
    for sec in env.get('sections', []):
        rows = []
        for it in sec.get('items', []):
            v = str(it.get('value', ''))
            # data-value is HTML-escaped, so the copy button reads it back from the DOM
            copy = f'<button onclick="copyText(this, this.closest(\'tr\').querySelector(\'td.v\').dataset.value)">コピー</button>' if v else ''
            if it.get('secret'):
                cell = f'<td class="v mask" data-value="{esc(v)}" data-shown="0">••••••••</td>'
                acts = '<button onclick="toggle(this)">表示</button>' + copy
            elif it.get('link'):
                cell = f'<td class="v" data-value="{esc(v)}"><a href="{esc(v)}" target="_blank" rel="noopener">{esc(v)}</a></td>'
                acts = copy
            else:
                cell = f'<td class="v" data-value="{esc(v)}">{esc(v)}</td>'
                acts = copy
            rows.append(f'<tr><td class="k">{esc(it.get("label", ""))}</td>{cell}<td class="a">{acts}</td></tr>')
        out.append(f'<section><h2>{esc(sec.get("title", ""))}</h2><table>{"".join(rows)}</table></section>')
    return page(f'{env["handson"]} / {env["env"]}', ''.join(out))


def index_html(envs):
    out = ['<h1>ハンズオンの環境</h1><p class="sub">~/.config/handson/ の env.json から作った一覧 (git には入れない)</p>']
    for label, want in (('使っている環境', lambda e: e.get('status') != 'done'), ('片付けた環境', lambda e: e.get('status') == 'done')):
        group = [e for e in envs if want(e)]
        if not group:
            continue
        out.append(f'<h3>{label}</h3><div class="grid">')
        for e in sorted(group, key=lambda e: e.get('date', ''), reverse=True):
            tag = '<span class="tag done">done</span>' if e.get('status') == 'done' else '<span class="tag">active</span>'
            sub = ' · '.join(x for x in (e.get('customer'), e.get('date')) if x)
            out.append(f'<a class="env" href="{esc(e["handson"])}/{esc(e["env"])}/index.html">'
                       f'<b>{esc(e["handson"])}{tag}</b><span>{esc(e["env"])}</span><br><span>{esc(sub)}</span></a>')
        out.append('</div>')
    return page('ハンズオンの環境', ''.join(out))


def shortcut(target):
    desktop = subprocess.run(['powershell', '-NoProfile', '-Command', "[Environment]::GetFolderPath('Desktop')"],
                             capture_output=True, text=True).stdout.strip()
    lnk = os.path.join(desktop, 'handson 環境.lnk')
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
          f"$s.TargetPath='{target}';$s.Description='ハンズオンの環境 (URL とクレデンシャル)';$s.Save()")
    subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True)
    return lnk


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--shortcut', action='store_true', help='デスクトップにショートカットを作る (Windows)')
    args = p.parse_args()
    envs = []
    for handson in sorted(os.listdir(ROOT)) if os.path.isdir(ROOT) else []:
        hdir = os.path.join(ROOT, handson)
        for name in sorted(os.listdir(hdir)) if os.path.isdir(hdir) else []:
            f = os.path.join(hdir, name, 'env.json')
            if os.path.isfile(f):
                env = json.load(open(f, encoding='utf-8'))
                env.setdefault('handson', handson)
                env.setdefault('env', name)
                open(os.path.join(hdir, name, 'index.html'), 'w', encoding='utf-8').write(env_html(env))
                envs.append(env)
    os.makedirs(ROOT, exist_ok=True)
    top = os.path.join(ROOT, 'index.html')
    open(top, 'w', encoding='utf-8').write(index_html(envs))
    print(f'{len(envs)} environment(s): {top}')
    if args.shortcut:
        print(f'shortcut: {shortcut(top)}')


if __name__ == '__main__':
    main()
