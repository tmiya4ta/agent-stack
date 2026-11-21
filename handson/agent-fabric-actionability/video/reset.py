"""撮り直しの前に、録画用のユーザーが {名前} (既定 demo) で作ったものを一覧にする / 消す。

  python reset.py <env.json> [--name demo] [--yes]

対象 (手順書の「後片付け」と同じ):
  - ご自身の BG: Agent Scanner「{名前} Scanner」と、取り込んだエージェントの Exchange 資産 (agent-quick-start-*)
  - Agent_Actionability_Workshop / Sandbox: MCP サーバー commerce-mcp-{名前}、Model Proxy {名前}-proxy と Exchange 資産、
    アプリケーション「{名前} Application」、Model Wallet {名前}-wallet
--yes を付けないと、消すものを表示するだけ。Scanner と Wallet は API が公開されていないので、表示だけして画面で消す。
MCP サーバーは、インスタンスを消しても MCP Servers の一覧に本体 (インスタンス 0) が残り、同じ名前で作れない。
画面の Actions → Delete で消す (Exchange の検索には出てこない)。
"""
import argparse, json, sys, time, urllib.error, urllib.request

HOST = 'https://anypoint.mulesoft.com'
WS = 'Agent_Actionability_Workshop'


def env_values(path):
    d = json.load(open(path, encoding='utf-8'))
    return {s['title'].split(' ')[0] + '/' + i['label']: i['value'] for s in d['sections'] for i in s['items']}


class Api:
    def __init__(self, user, pw):
        s, b = self.call('POST', '/accounts/login', {'username': user, 'password': pw}, token=None)
        if s != 200:
            sys.exit(f'login failed {s} {b[:200]}')
        self.token = json.loads(b)['access_token']

    def call(self, method, path, body=None, token='', headers=None):
        h = {'Content-Type': 'application/json', **(headers or {})}
        tok = self.token if token == '' else token
        if tok:
            h['Authorization'] = 'Bearer ' + tok
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(HOST + path, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def get(self, path):
        s, b = self.call('GET', path)
        if s != 200:
            print(f'  ! GET {path}: {s} {b[:200]}')
            return None
        return json.loads(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('env')
    ap.add_argument('--name', default='demo')
    ap.add_argument('--yes', action='store_true')
    a = ap.parse_args()
    V = env_values(a.env)
    api = Api(V['Anypoint/ユーザー名'], V['Anypoint/パスワード'])
    me = api.get('/accounts/api/me')['user']
    root = me['organization']['id']
    bgs = {o['name']: o['id'] for o in me.get('memberOfOrganizations', [])}  # ご自身の BG は階層の深いところにある
    ws, own = bgs.get(WS), bgs.get(V['Anypoint/ユーザー名'])
    print(f'root {root}  {WS} {ws}  own {own}')
    envs = api.get(f'/accounts/api/organizations/{ws}/environments')['data']
    env = next(e['id'] for e in envs if e['name'] == 'Sandbox')
    n = a.name
    plan = []

    # API Manager のインスタンス (MCP サーバーと Model Proxy)
    apis = f'/apimanager/api/v1/organizations/{ws}/environments/{env}/apis'
    for asset in (api.get(apis + '?limit=200') or {}).get('assets', []):
        for i in asset['apis']:
            label = i.get('instanceLabel') or ''
            if asset['assetId'] in (f'commerce-mcp-{n}', f'{n}-proxy') or label in (f'commerce-mcp-{n}', f'{n}-proxy'):
                plan.append((f'api {asset["assetId"]} ({label}) {i["id"]}', 'DELETE', f'{apis}/{i["id"]}'))
    # アプリケーション (契約ごと消える)
    apps = api.get(f'/exchange/api/v2/organizations/{ws}/applications?limit=200') or []
    for app in apps if isinstance(apps, list) else apps.get('applications', []):
        if app['name'] == f'{n} Application':
            plan.append((f'application {app["name"]} {app["id"]}', 'DELETE',
                         f'/exchange/api/v2/organizations/{ws}/applications/{app["id"]}'))
    # Exchange の資産
    for bg, ids in ((ws, (f'commerce-mcp-{n}', f'{n}-proxy')), (own, ())):
        for asset in api.get(f'/exchange/api/v2/assets/search?organizationId={bg}&limit=200') or []:
            aid = asset['assetId']
            if aid in ids or (bg == own and aid.startswith('agent-quick-start')):
                plan.append((f'exchange {aid} {asset.get("version")} ({asset.get("type")})', 'DELETE',
                             f'/exchange/api/v2/assets/{bg}/{aid}/{asset["version"]}'))
    print('\n'.join(('delete ' if a.yes else 'would delete ') + p[0] for p in plan) or 'nothing via API')
    print(f'画面で消すもの: {own} の Providers の「{n} Scanner」、Model Wallets の {n}-wallet')
    if not a.yes:
        return
    order = ('application', 'api', 'exchange')  # 契約が残っていると Proxy を消せず、インスタンスが残っていると資産を消せない
    for label, m, path in sorted(plan, key=lambda p: order.index(p[0].split()[0])):
        # Exchange の資産はゴミ箱に残ると、同じ名前とバージョンで作り直せない (deleted asset with the same version)
        s, b = api.call(m, path, headers={'x-delete-type': 'hard-delete'} if label.startswith('exchange') else None)
        print(f'{label}: {s} {"" if s < 300 else b[:200]}')
        time.sleep(1)


if __name__ == '__main__':
    main()
