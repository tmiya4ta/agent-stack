"""new-hire-onboarding のハンズオン環境を Anypoint に作る (hosting.md の手順 1〜4 と 6 の後半)。

    export ANYPOINT_USERNAME=... ANYPOINT_PASSWORD=...
    python anypoint_setup.py org                      # BG1 / APPBG、vCore、Gateway
    python anypoint_setup.py team                     # チーム workshop と、BG1 / Sandbox への全ロール
    python anypoint_setup.py users --count 6 --date 20261029 --env 20261029-acme --email tmiyashita+{name}@salesforce.com
    python anypoint_setup.py proxy-jwt --env 20261029-acme   # Model Proxy の認証を Client ID から JWT (HS256) に替える
    python anypoint_setup.py page --env 20261029-acme # 受講者が見る Exchange のページ (URL、JWT、コピペする 3 つのファイル)
    python anypoint_setup.py show                     # 作ったものの ID と URL
    python anypoint_setup.py teardown --date 20261029 [--yes]   # 後片付け。--yes が無ければ消すものを出すだけ

すでにあるもの (同じ名前の BG、Gateway、チーム、ユーザー) は作り直さない。
ユーザーのパスワードは --out (既定 ~/.config/handson/new-hire-onboarding/<--env>/users.json、git の外) に書く。
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import string
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HOST = 'https://anypoint.mulesoft.com'
HERE = os.path.dirname(os.path.abspath(__file__))


class Api:
    def __init__(self, username, password):
        s, body = self._call('POST', '/accounts/login', {'username': username, 'password': password}, token=None)
        if s != 200:
            sys.exit(f'login failed: {s} {body[:200]}')
        self.token = json.loads(body)['access_token']

    def _call(self, method, path, body=None, token=''):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        data = json.dumps(body).encode() if body is not None else None
        while True:
            req = urllib.request.Request(HOST + path, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, r.read().decode()
            except urllib.error.HTTPError as e:
                text = e.read().decode()
                if e.code == 429:  # 50 calls per window; the message says how long to wait
                    m = re.search(r'after (\d+)', text)
                    time.sleep((int(m.group(1)) if m else 30) + 2)
                    continue
                return e.code, text

    def call(self, method, path, body=None):
        return self._call(method, path, body, self.token)

    def get(self, path):
        s, body = self.call('GET', path)
        if s != 200:
            sys.exit(f'GET {path}: {s} {body[:300]}')
        return json.loads(body)


def root_org(api, args):
    if args.org:
        return args.org
    return api.get('/accounts/api/me')['user']['organization']['id']


def find_bg(api, root, name):
    for sub in api.get(f'/accounts/api/organizations/{root}/hierarchy').get('subOrganizations', []):
        if sub['name'] == name:
            return sub['id']
    return None


def sandbox_env(api, bg):
    for e in api.get(f'/accounts/api/organizations/{bg}/environments')['data']:
        if e['name'] == 'Sandbox':
            return e['id']
    sys.exit(f'no Sandbox environment in {bg}')


def ids(api, args):
    root = root_org(api, args)
    bg1, appbg = find_bg(api, root, args.bg1), find_bg(api, root, args.appbg)
    return root, bg1, appbg


def create_bg(api, root, owner, name, vcores, gateways_small=0):
    ent = {'createSubOrgs': False, 'createEnvironments': True, 'globalDeployment': False,
           'vCoresProduction': {'assigned': 0}, 'vCoresSandbox': {'assigned': vcores},
           'vCoresDesign': {'assigned': 0}, 'staticIps': {'assigned': 0}, 'vpcs': {'assigned': 0},
           'vpns': {'assigned': 0}, 'loadBalancer': {'assigned': 0}}
    if gateways_small:
        ent['managedGatewaySmall'] = {'assigned': gateways_small}
    s, body = api.call('POST', '/accounts/api/organizations',
                       {'name': name, 'parentOrganizationId': root, 'ownerId': owner, 'entitlements': ent})
    if s != 201:
        sys.exit(f'create BG {name}: {s} {body[:300]}')
    return json.loads(body)['id']


def cmd_org(api, args):
    root = root_org(api, args)
    owner = api.get('/accounts/api/me')['user']['id']
    appbg = find_bg(api, root, args.appbg)
    if not appbg:
        appbg = create_bg(api, root, owner, args.appbg, args.appbg_vcores)
        print(f'created {args.appbg}: {appbg} (vCore {args.appbg_vcores})')
    bg1 = find_bg(api, root, args.bg1)
    if not bg1:
        sb = api.get(f'/accounts/api/organizations/{root}')['entitlements']['vCoresSandbox']
        # "reassigned" can include vCores that are not actually free; the API tells us the real figure on 400
        free = round(sb['assigned'] - sb['reassigned'], 2)
        while free > 0:
            try:
                bg1 = create_bg(api, root, owner, args.bg1, free, gateways_small=1)
                break
            except SystemExit as e:
                m = re.search(r'only ([\d.]+) vCores available', str(e))
                if not m or float(m.group(1)) >= free:
                    raise
                free = float(m.group(1))
        print(f'created {args.bg1}: {bg1} (vCore {free})')
    env = sandbox_env(api, bg1)
    gws = api.get(f'/gatewaymanager/api/v1/organizations/{bg1}/environments/{env}/gateways')['content']
    gw = next((g for g in gws if g['name'] == args.gateway), None)
    if not gw:
        versions = api.get('/gatewaymanager/xapi/v1/gateway/versions')['channels']['lts']['versions']
        body = {'name': args.gateway, 'size': 'small', 'targetId': args.target,
                'runtimeVersion': versions[0]['displayName'], 'releaseChannel': 'lts',
                # publicUrl left out: on a shared space the gateway assigns one
                'configuration': {'ingress': {'forwardSslSession': False, 'lastMileSecurity': False},
                                  'logging': {'forwardLogs': True, 'level': 'info'},
                                  'properties': {'connectionIdleTimeout': 60, 'upstreamResponseTimeout': 300}}}
        s, text = api.call('POST', f'/gatewaymanager/api/v1/organizations/{bg1}/environments/{env}/gateways', body)
        if s != 201:
            sys.exit(f'create gateway: {s} {text[:300]}')
        gw = json.loads(text)
        print(f'created gateway {args.gateway} {versions[0]["displayName"]} on {args.target}')
    for _ in range(40):
        g = api.get(f'/gatewaymanager/api/v1/organizations/{bg1}/environments/{env}/gateways/{gw["id"]}')
        if g['status'] == 'APPLIED' and g['configuration']['ingress'].get('publicUrl'):
            print(f'gateway {args.gateway}: {g["configuration"]["ingress"]["publicUrl"]}')
            return
        time.sleep(15)
    print(f'gateway {args.gateway} is not APPLIED yet; run `show` later')


def find_team(api, root, name):
    teams = api.get(f'/accounts/api/organizations/{root}/teams?limit=500')['data']
    return next((t['team_id'] for t in teams if t['team_name'] == name), None), teams


def cmd_team(api, args):
    root, bg1, _ = ids(api, args)
    if not bg1:
        sys.exit(f'{args.bg1} not found; run `org` first')
    env = sandbox_env(api, bg1)
    team, teams = find_team(api, root, args.team)
    if not team:
        org_name = api.get(f'/accounts/api/organizations/{root}')['name']
        parent = next(t['team_id'] for t in teams if t['team_name'] == org_name and not t.get('parent_team_id'))
        s, body = api.call('POST', f'/accounts/api/organizations/{root}/teams',
                           {'team_name': args.team, 'parent_team_id': parent, 'team_type': 'internal'})
        if s != 201:
            sys.exit(f'create team: {s} {body[:300]}')
        team = json.loads(body)['team_id']
        print(f'created team {args.team}: {team}')
    have = {r['role_id'] for r in api.get(f'/accounts/api/organizations/{root}/teams/{team}/roles?limit=500')['data']}
    roles = api.get('/accounts/api/roles?limit=500')['data']
    done = {'env': 0, 'bg': 0, 'already': 0}
    forbidden = []
    path = f'/accounts/api/organizations/{root}/teams/{team}/roles'
    for r in roles:
        if r['role_id'] in have:
            done['already'] += 1
            continue
        # environment-scoped roles need envId; BG-scoped roles reject it, so try env first, then BG
        s, _ = api.call('POST', path, [{'role_id': r['role_id'], 'context_params': {'org': bg1, 'envId': env}}])
        if s in (200, 201, 204, 409):
            done['env'] += 1
            continue
        if s != 403:
            s, _ = api.call('POST', path, [{'role_id': r['role_id'], 'context_params': {'org': bg1}}])
            if s in (200, 201, 204, 409):
                done['bg'] += 1
                continue
        forbidden.append(r['name'])
    print(f'team {args.team}: env-scoped {done["env"]}, BG-scoped {done["bg"]}, already {done["already"]}, '
          f'not assignable {len(forbidden)}')


def cmd_users(api, args):
    root, _, _ = ids(api, args)
    team, _ = find_team(api, root, args.team)
    if not team:
        sys.exit(f'team {args.team} not found; run `team` first')
    out = json.load(open(args.out)) if os.path.exists(args.out) else {}
    out.setdefault('users', {})
    for i in range(args.start, args.start + args.count):
        name = f'ws{i:02d}'
        username = f'{name}_{args.date}'
        found = api.get(f'/accounts/api/organizations/{root}/users?search={username}&limit=10')['data']
        user = next((u for u in found if u['username'] == username), None)
        if user:
            uid = user['id']
            print(f'{username}: exists')
        else:
            pw = 'Ws' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10)) + f'!{i}'
            s, body = api.call('POST', f'/accounts/api/organizations/{root}/users',
                               {'username': username, 'firstName': name, 'lastName': 'workshop',
                                'email': args.email.format(name=name, username=username), 'password': pw,
                                'mfaVerificationExcluded': True})
            if s not in (200, 201):
                print(f'{username}: create failed {s} {body[:200]}')
                continue
            uid = json.loads(body)['id']
            out['users'][username] = {'password': pw, 'suffix': name}
            print(f'{username}: created')
        s, _ = api.call('PUT', f'/accounts/api/organizations/{root}/teams/{team}/members/{uid}',
                        {'membership_type': 'member'})
        if s not in (200, 204):
            print(f'{username}: adding to team failed {s}')
    json.dump(out, open(args.out, 'w'), indent=2)
    print(f'passwords: {args.out}')


def env_dir(args):
    d = os.path.join(os.path.expanduser('~'), '.config', 'handson', 'new-hire-onboarding', args.env or args.date or '')
    if not (args.env or args.date):
        sys.exit('--env (or --date) is required')
    os.makedirs(d, exist_ok=True)
    return d


def llm_jwt(args, create=False):
    """the HS256 secret and the one token every participant puts in openAI.apiKey (<env folder>/llm-jwt.json)."""
    path = os.path.join(env_dir(args), 'llm-jwt.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    if not create:
        sys.exit(f'{path} not found; run proxy-jwt first')
    b64 = lambda x: base64.urlsafe_b64encode(x).rstrip(b'=').decode()
    secret = secrets.token_urlsafe(32)
    exp = int(time.time()) + args.jwt_days * 86400
    head = b64(json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':')).encode())
    body = b64(json.dumps({'sub': args.page_asset, 'client_id': args.page_asset, 'iat': int(time.time()), 'exp': exp},
                          separators=(',', ':')).encode())
    sig = b64(hmac.new(secret.encode(), f'{head}.{body}'.encode(), hashlib.sha256).digest())
    jwt = {'hs256Secret': secret, 'token': f'{head}.{body}.{sig}',
           'exp': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(exp))}
    json.dump(jwt, open(path, 'w', encoding='utf-8'), indent=2)
    print(f'new JWT (expires {jwt["exp"]}): {path}')
    return jwt


def cmd_proxy_jwt(api, args):
    """Client ID Enforcement を無効にし、JWT Validation (HS256) を同じ位置 (order 3) に付ける。"""
    _, bg1, _ = ids(api, args)
    env = sandbox_env(api, bg1)
    base = f'/apimanager/api/v1/organizations/{bg1}/environments/{env}/apis'
    inst = [i for a in api.get(base)['assets'] if a['assetId'] == args.proxy for i in a['apis']]
    if not inst:
        sys.exit(f'model proxy {args.proxy} not found; create it with model-proxy.js first')
    pol = f'{base}/{inst[0]["id"]}/policies'
    policies = api.get(pol)
    policies = policies.get('policies', policies)
    kind = lambda p: (p.get('template') or {}).get('assetId') or p.get('assetId')
    # a disabled policy drops out of this list
    for p in policies:
        if kind(p) == 'client-id-enforcement' and not p.get('disabled'):
            s, _ = api.call('PATCH', f'{pol}/{p["policyId"]}', {'disabled': True})
            print(f'client-id-enforcement disabled: {s}')
    jwt = llm_jwt(args, create=True)
    cfg = {
        # the broker sends openAI.apiKey as "Authorization: Bearer"; a customExpression here did not take effect
        # on Flex 1.12.9 (every request passed), so stay with the standard origin
        'jwtOrigin': 'httpBearerAuthenticationHeader', 'jwtExpression': "#[attributes.headers['jwt']]",
        'signingMethod': 'hmac', 'signingKeyLength': 256, 'jwtKeyOrigin': 'text', 'textKey': jwt['hs256Secret'],
        'jwksUrl': 'http://your-jwks-service.example:80/base/path', 'jwksServiceTimeToLive': 60,
        'jwksServiceConnectionTimeout': 10000,
        'customKeyExpression': "#[authentication.properties['key_to_your_public_pem_certificate']]",
        'skipClientIdValidation': True, 'clientIdExpression': '#[vars.claimSet.client_id]',
        'validateAudClaim': False, 'mandatoryAudClaim': False, 'supportedAudiences': 'aud.example.com',
        'mandatoryExpClaim': True, 'mandatoryNbfClaim': False, 'validateCustomClaim': False,
    }
    current = next((p for p in policies if kind(p) == 'jwt-validation'), None)
    if current:
        s, body = api.call('PATCH', f'{pol}/{current["policyId"]}', {'configurationData': cfg})
        print(f'jwt-validation updated: {s}')
        return
    # the newest template may have no implementation for this gateway version (400); step down
    templates = api.get(f'/apimanager/xapi/v1/organizations/{bg1}/exchange-policy-templates'
                        f'?includeAllVersions=true&environmentId={env}&apiInstanceId={inst[0]["id"]}')
    versions = sorted({t['version'] for t in templates if t.get('assetId') == 'jwt-validation'},
                      key=lambda v: [int(x) for x in v.split('.')], reverse=True)
    for v in versions:
        s, body = api.call('POST', pol, {'configurationData': cfg, 'groupId': '68ef9520-24e9-4cf2-b2f5-620025690913',
                                         'assetId': 'jwt-validation', 'assetVersion': v, 'order': 3})
        if s == 201:
            print(f'jwt-validation {v} added (takes a minute or two to reach the gateway)')
            return
    sys.exit(f'could not add jwt-validation: {s} {body[:200]}')


def member_urls(api, appbg):
    """public URL of each member app in APPBG / Sandbox, keyed by deployment name."""
    env = sandbox_env(api, appbg)
    base = f'/amc/application-manager/api/v2/organizations/{appbg}/environments/{env}/deployments'
    urls = {}
    for d in api.get(base).get('items', []):
        full = api.get(f'{base}/{d["id"]}')
        urls[d['name']] = full['target']['deploymentSettings']['http']['inbound']['publicUrl'].rstrip('/')
    return urls


def gateway_url(api, bg1, env, name):
    for g in api.get(f'/gatewaymanager/api/v1/organizations/{bg1}/environments/{env}/gateways')['content']:
        if g['name'] == name:
            d = api.get(f'/gatewaymanager/api/v1/organizations/{bg1}/environments/{env}/gateways/{g["id"]}')
            return d['configuration']['ingress']['publicUrl'].rstrip('/')
    sys.exit(f'gateway {name} not found')


def fill(text, values):
    for k, v in values.items():
        text = text.replace('{{' + k + '}}', v)
    return text


PAGE_HOME = '''# 新入社員オンボーディング ハンズオン

自分の番号 (ユーザー名の `wsXX`、例 `ws03`) を使って、broker を BG1 / Sandbox に配備します。
下のファイルの **`wsXX` を全部自分の番号に置き換えて** (VS Code の Replace All) から配備してください。

## 使う値

| 名前 | 値 |
|---|---|
| Business Group | {bg_name} (`{bg1}`) |
| Environment | Sandbox |
| Omni Gateway | `{gateway}` |
| IT Provisioning Agent の URL | `{it}` |
| Office Concierge Agent の URL | `{office}` |
| Employee DB (MCP) の URL | `{db}` |
| LLM (Model Proxy) の URL | `{llm}` |

## クレデンシャル

| 名前 | 値 |
|---|---|
| Anypoint のログイン | 配られたユーザー名とパスワード |
| `openAI.apiKey` | `{jwt}` |
| `openAI.clientId` / `openAI.clientSecret` | `none` (使わない) |

`openAI.apiKey` は LLM (Model Proxy) の JWT です (全員同じ。期限 {jwt_exp})。broker が `Authorization: Bearer` で送ります。

## ファイル

ページ exchange.json、agent-network.yaml、broker1.agent の中身を、プロジェクトの同じ名前のファイルにそのまま貼ります
(`broker1.agent` は `brokers/` の下)。

## 呼んでみる

配備したら、broker の URL は `{gw}/onboarding-broker-wsXX/` です (最後の `/` が要ります)。

```bash
curl -s {gw}/onboarding-broker-wsXX/ \\
  -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \\
  -d '{{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{{"message":{{"role":"ROLE_USER","parts":[{{"text":"Please start onboarding for new employee Taro Tanaka (tanaka.taro@example.com)"}}],"messageId":"11111111-1111-1111-1111-111111111111"}}}}}}'
```
'''


def cmd_page(api, args):
    """Exchange (BG1) に custom の資産を作り、受講者がコピペする値とファイルをページに載せる。"""
    root, bg1, appbg = ids(api, args)
    env = sandbox_env(api, bg1)
    gw = gateway_url(api, bg1, env, args.gateway)
    urls = member_urls(api, appbg)
    llm = f'{gw}/{args.proxy_path}'
    jwt = llm_jwt(args)
    values = {
        # every participant shares BG1 / Sandbox / the gateway, so names carry the participant's number
        '-suffix': '-wsXX', '_suffix': '_wsXX',
        'business-group-id': bg1,
        'it-provisioning-agent-url': urls['it-provisioning-agent'] + '/',
        'office-concierge-agent-url': urls['office-concierge-agent'] + '/',
        'employee-db-app-url': urls['employee-db-app'],
        'llm-base-url': llm,
        # the Model Proxy checks only the JWT (openAI.apiKey); client id / secret are not used
        'llm-client-id': 'none', 'llm-client-secret': 'none', 'llm-api-key': jwt['token'],
    }
    net = os.path.join(HERE, '..', 'onboarding-employees')
    files = [('exchange.json', ['exchange.json'], 'json'),
             ('agent-network.yaml', ['agent-network.yaml'], 'yaml'),
             ('broker1.agent', ['brokers', 'broker1.agent'], '')]
    pages = {'home': PAGE_HOME.format(bg_name=args.bg1, bg1=bg1, gateway=args.gateway, gw=gw, llm=llm,
                                      it=values['it-provisioning-agent-url'],
                                      office=values['office-concierge-agent-url'],
                                      db=values['employee-db-app-url'], jwt=jwt['token'], jwt_exp=jwt['exp'])}
    for name, path, lang in files:
        text = fill(open(os.path.join(net, *path), encoding='utf-8').read(), values)
        pages[name] = f'# {name}\n\n`wsXX` を自分の番号に置き換えてから貼ります。\n\n```{lang}\n{text.rstrip()}\n```\n'

    auth = ['--username', os.environ['ANYPOINT_USERNAME'], '--password', os.environ['ANYPOINT_PASSWORD'],
            '--organization', bg1]

    def cli(*cmd):
        r = subprocess.run(['anypoint-cli-v4', *cmd, *auth], capture_output=True, text=True, encoding='utf-8',
                           errors='replace', shell=(os.name == 'nt'))
        return r.returncode, (r.stdout + r.stderr).strip()

    asset = f'{bg1}/{args.page_asset}/1.0.0'
    s, _ = api.call('GET', f'/exchange/api/v2/assets/{bg1}/{args.page_asset}/1.0.0')
    if s != 200:
        rc, out = cli('exchange', 'asset', 'upload', asset, '--type', 'custom',
                      '--name', 'New Hire Onboarding Hands-on',
                      '--description', 'Values and files for the new hire onboarding hands-on')
        print(f'asset {args.page_asset}: {"created" if rc == 0 else out[-300:]}')
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in pages.items():
            path = os.path.join(tmp, name.replace('.', '-') + '.md')
            open(path, 'w', encoding='utf-8').write(text)
            for _ in range(3):  # the upload sometimes drops the connection (ECONNRESET)
                rc, out = cli('exchange', 'asset', 'page', 'upload', asset, name, path)
                if rc == 0:
                    break
            print(f'page {name}: {"ok" if rc == 0 else out[-300:]}')
    print(f'https://anypoint.mulesoft.com/exchange/{bg1}/{args.page_asset}/')


def cmd_teardown(api, args):
    """後片付け。アプリ → API インスタンス → Gateway → ユーザー → チーム → BG の順に消す。"""
    root, bg1, appbg = ids(api, args)
    plan = []  # (label, path) to DELETE
    for bg in (bg1, appbg):
        if not bg:
            continue
        env = sandbox_env(api, bg)
        dep = f'/amc/application-manager/api/v2/organizations/{bg}/environments/{env}/deployments'
        for d in api.get(dep).get('items', []):
            plan.append((f'app {d["name"]}', f'{dep}/{d["id"]}'))
        apis = f'/apimanager/api/v1/organizations/{bg}/environments/{env}/apis'
        for a in api.get(apis).get('assets', []):
            for i in a['apis']:
                plan.append((f'api {a["assetId"]} {i["id"]}', f'{apis}/{i["id"]}'))
        gws = f'/gatewaymanager/api/v1/organizations/{bg}/environments/{env}/gateways'
        for g in api.get(gws)['content']:
            plan.append((f'gateway {g["name"]}', f'{gws}/{g["id"]}'))
    if args.date:
        users = api.get(f'/accounts/api/organizations/{root}/users?search=_{args.date}&limit=100')['data']
        for u in users:
            if re.fullmatch(rf'ws\d\d_{args.date}', u['username']):
                plan.append((f'user {u["username"]}', f'/accounts/api/organizations/{root}/users/{u["id"]}'))
    team, _ = find_team(api, root, args.team)
    if team:
        plan.append((f'team {args.team}', f'/accounts/api/organizations/{root}/teams/{team}'))
    for name, bg in ((args.bg1, bg1), (args.appbg, appbg)):
        if bg:
            # Exchange assets (networks, the Model Proxy asset, the hands-on page) go with the BG
            plan.append((f'BG {name}', f'/accounts/api/organizations/{bg}'))
    for label, _ in plan:
        print(('delete ' if args.yes else 'would delete ') + label)
    if not args.yes:
        print('dry run; pass --yes to delete')
        return
    for i, (label, path) in enumerate(plan):
        if label.startswith('gateway') and not plan[i - 1][0].startswith('gateway'):
            time.sleep(30)  # let the apps and API instances leave the gateway first
        tries = 20 if label.startswith('BG') else 1  # a BG can't go while its gateway is still being removed
        for _ in range(tries):
            s, body = api.call('DELETE', path)
            if s in (200, 202, 204, 404):
                break
            if tries > 1:
                time.sleep(30)
        print(f'{label}: {s}' + ('' if s in (200, 202, 204, 404) else f' {body[:200]}'))

def cmd_show(api, args):
    root, bg1, appbg = ids(api, args)
    print(f'root   {root}')
    for name, bg in ((args.bg1, bg1), (args.appbg, appbg)):
        if not bg:
            print(f'{name:6} (none)')
            continue
        env = sandbox_env(api, bg)
        vc = api.get(f'/accounts/api/organizations/{bg}')['entitlements']['vCoresSandbox']['assigned']
        print(f'{name:6} {bg}  Sandbox {env}  vCore {vc}')
        for g in api.get(f'/gatewaymanager/api/v1/organizations/{bg}/environments/{env}/gateways')['content']:
            d = api.get(f'/gatewaymanager/api/v1/organizations/{bg}/environments/{env}/gateways/{g["id"]}')
            print(f'  gateway {g["name"]} {d["status"]} {d["configuration"]["ingress"].get("publicUrl")}')
        deps = api.get(f'/amc/application-manager/api/v2/organizations/{bg}/environments/{env}/deployments')
        for d in deps.get('items', []):
            print(f'  app {d["name"]} {d.get("application", {}).get("status")}')
        for a in api.get(f'/apimanager/api/v1/organizations/{bg}/environments/{env}/apis').get('assets', []):
            print(f'  api {a["assetId"]} ' + ' '.join(str(i['id']) for i in a['apis']))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('step', choices=['org', 'team', 'users', 'proxy-jwt', 'page', 'show', 'teardown'])
    p.add_argument('--org', help='root org ID (default: the login user\'s org)')
    p.add_argument('--bg1', default='BG1')
    p.add_argument('--appbg', default='APPBG')
    p.add_argument('--appbg-vcores', type=float, default=0.3, help='0.1 per member app')
    p.add_argument('--gateway', default='agent-network-shared-gw')
    p.add_argument('--target', default='cloudhub-us-east-2')
    p.add_argument('--team', default='workshop')
    p.add_argument('--count', type=int, default=6)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--date', help='YYYYMMDD of the workshop, used in user names')
    p.add_argument('--email', default='tmiyashita+{name}@salesforce.com')
    p.add_argument('--proxy', default='workshop-llm-proxy')
    p.add_argument('--proxy-path', default='llm', help='Model Proxy base path')
    p.add_argument('--page-asset', default='new-hire-onboarding-handson')
    p.add_argument('--jwt-days', type=int, default=90, help='proxy-jwt: lifetime of a new JWT')
    p.add_argument('--yes', action='store_true', help='teardown: really delete')
    p.add_argument('--env', help='environment name for ~/.config/handson/new-hire-onboarding/<env>/ (default: --date)')
    p.add_argument('--out', help='users: where to write passwords (default: <env folder>/users.json)')
    args = p.parse_args()
    if args.step == 'users' and not args.date:
        p.error('users needs --date')
    if args.step == 'users' and not args.out:
        envdir = os.path.join(os.path.expanduser('~'), '.config', 'handson', 'new-hire-onboarding', args.env or args.date)
        os.makedirs(envdir, exist_ok=True)
        args.out = os.path.join(envdir, 'users.json')
    api = Api(os.environ['ANYPOINT_USERNAME'], os.environ['ANYPOINT_PASSWORD'])
    {'org': cmd_org, 'team': cmd_team, 'users': cmd_users,
     'proxy-jwt': cmd_proxy_jwt, 'page': cmd_page, 'show': cmd_show,
     'teardown': cmd_teardown}[args.step](api, args)


if __name__ == '__main__':
    main()
