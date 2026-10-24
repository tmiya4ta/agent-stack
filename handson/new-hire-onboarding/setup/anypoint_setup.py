"""new-hire-onboarding のハンズオン環境を Anypoint に作る (hosting.md の手順 1〜4 と 6 の後半)。

    export ANYPOINT_USERNAME=... ANYPOINT_PASSWORD=...
    python anypoint_setup.py org                      # BG1 / APPBG、vCore、Gateway
    python anypoint_setup.py team                     # チーム workshop と、BG1 / Sandbox への全ロール
    python anypoint_setup.py users --count 6 --date 20261029 --env 20261029-acme --email tmiyashita+{name}@salesforce.com
    python anypoint_setup.py proxy-jwt --env 20261029-acme   # Model Proxy の認証を Client ID から JWT (HS256) に替える
    python anypoint_setup.py atelier --env 20261029-acme   # A2A のクライアント Atelier を APPBG に配備 (受講者の broker の snapshot 付き)
    python anypoint_setup.py page --env 20261029-acme # 受講者が見る Exchange のページ (URL、JWT、コピペする 3 つのファイル)
    python anypoint_setup.py show                     # 作ったものの ID と URL
    python anypoint_setup.py teardown --date 20261029 [--yes]   # 後片付け。--yes が無ければ消すものを出すだけ
    python anypoint_setup.py teardown --participant ws00 [--yes] # 1 人の broker だけ消す (ユーザーは残す)

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
import shutil
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
        # environment-scoped roles need envId; BG-scoped roles reject it, so try env first, then BG.
        # A BG-scoped role answers the env attempt with 403 too (e.g. Mule Developer Generative AI User, which
        # Vibes needs), so always try the BG scope
        s, _ = api.call('POST', path, [{'role_id': r['role_id'], 'context_params': {'org': bg1, 'envId': env}}])
        if s in (200, 201, 204, 409):
            done['env'] += 1
            continue
        s, _ = api.call('POST', path, [{'role_id': r['role_id'], 'context_params': {'org': bg1}}])
        if s in (200, 201, 204, 409):
            done['bg'] += 1
            continue
        forbidden.append(r['name'])
    print(f'team {args.team}: env-scoped {done["env"]}, BG-scoped {done["bg"]}, already {done["already"]}, '
          f'not assignable {len(forbidden)}')


def cmd_users(api, args):
    root, bg1, _ = ids(api, args)
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
            pw = args.password
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
        if bg1:
            # the BG a user lands in after login (the root org by default); only the admin's PUT can set it
            s, _ = api.call('PUT', f'/accounts/api/organizations/{root}/users/{uid}',
                            {'properties': {'cs_auth': {'activeOrganizationId': bg1}}})
            if s != 200:
                print(f'{username}: setting the default BG failed {s}')
            # the profile's "Selected Environment in BG1" (without it Runtime Manager opens on Choose Environment)
            s, _ = api.call('PUT', f'/accounts/api/organizations/{root}/users/{uid}',
                            {'id': uid, 'organizationPreferences': {bg1: {'defaultEnvironment': sandbox_env(api, bg1)}}})
            if s != 200:
                print(f'{username}: setting the default environment failed {s}')
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


PAGE_HOME = '''# AI Workshop 当日ガイド

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

**ほかの場所 (GitHub やテンプレート) のファイルは使わないでください。** LLM のモデル名がこのページでは `openai/gpt-5-mini` になっていて、
`gpt-5-mini` のままだと broker が `An internal error occurred` で失敗します (Model Proxy が 400 を返す)。

## 呼んでみる

配備したら、broker の URL は `{gw}/onboarding-broker-wsXX/` です (最後の `/` が要ります)。

```bash
curl -s {gw}/onboarding-broker-wsXX/ \\
  -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \\
  -d '{{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{{"message":{{"role":"ROLE_USER","parts":[{{"text":"Please start onboarding for new employee Taro Tanaka (tanaka.taro@example.com)"}}],"messageId":"11111111-1111-1111-1111-111111111111"}}}}}}'
```
{atelier}'''

PAGE_ATELIER = '''
## ブラウザから呼ぶ (A2A クライアント)

A2A クライアントを開き、**import configuration** → **Repository** → タブ **Local** で、自分の番号の
「AI Workshop — wsXX」を選びます。
(一覧に無いときは **Direct URL** に `{url}/scenarios/{snapshot}` を入れても読み込めます。`wsXX` は自分の番号)
タブ「Brokerなし」にメンバーの 3 つ、「Brokerあり」に自分の broker のウインドウがあります。

- A2A クライアント: {url}/
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
                                      db=values['employee-db-app-url'], jwt=jwt['token'], jwt_exp=jwt['exp'],
                                      atelier=PAGE_ATELIER.format(url=urls['atelier'], snapshot=atelier_snapshot_name('wsXX'))
                                      if 'atelier' in urls else '')}
    for name, path, lang in files:
        text = fill(open(os.path.join(net, *path), encoding='utf-8').read(), values)
        # with two providers on the Model Proxy a bare model name is ambiguous (400), so name the provider
        text = text.replace('model: "gpt-5-mini"', f'model: "{args.llm_model}"')
        text = text.replace('          - gpt-5-mini\n', f'          - {args.llm_model}\n')
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
                      '--name', args.page_name,
                      '--description', 'Values and files for the new hire onboarding hands-on')
        print(f'asset {args.page_asset}: {"created" if rc == 0 else out[-300:]}')
    else:
        rc, out = cli('exchange', 'asset', 'modify', asset, '--name', args.page_name)
        print(f'asset {args.page_asset} name: {"ok" if rc == 0 else out[-300:]}')
    # the CLI's --tags leaves the labels empty; the tags endpoint works
    s, _ = api.call('PUT', f'/exchange/api/v2/assets/{bg1}/{args.page_asset}/1.0.0/tags',
                    [{'value': t.strip()} for t in args.page_tags.split(',') if t.strip()])
    print(f'asset {args.page_asset} tags {args.page_tags}: {s}')
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


ATELIER_REPO = 'https://github.com/tmiya4ta/agent-atelier'


def atelier_snapshot_name(name):
    return f'new-hire-onboarding-{name}.json'


def atelier_snapshot(gw, urls, name):
    """1 人分の Atelier の snapshot (Import で読む)。リポジトリの AI-Workshop-Step2.json と同じ形で、
    タブ「Brokerなし」にメンバーの 3 つ、「Brokerあり」にその受講者の broker。"""
    def conn(proto, url, label):
        return {'key': f'{proto}::{url}', 'protoId': proto, 'url': url, 'name': label}

    def window(c):
        return {'protoId': c['protoId'], 'config': {'url': c['url'], 'name': c['name'], 'auth': ''}, 'pinned': False}

    members = [conn('a2a', urls['it-provisioning-agent'] + '/', 'ITプロビジョニング'),
               conn('a2a', urls['office-concierge-agent'] + '/', 'オフィスコンシェルジュ'),
               conn('mcp', urls['employee-db-app'] + '/mcp', '社員MCPサーバー')]
    broker = conn('a2a', f'{gw}/onboarding-broker-{name}/', f'Employee Onboarding Broker {name}')
    return {'meta': {'name': f'AI Workshop — {name}',
                     'description': 'IT プロビジョニング / オフィスコンシェルジュ / 社員 MCP サーバー / Onboarding Broker'},
            'app': 'atelier', 'exportedAt': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            'includesSecrets': False,
            'state': {'v': 1, 'zoom': 1, 'theme': 'light', 'identities': [], 'catalogs': [], 'scripts': [],
                      'selectedScriptId': None, 'scriptPinned': False, 'bookmarks': members + [broker],
                      'closedWindows': [], 'activeWsIdx': 0,
                      'workspaces': [{'name': 'Brokerなし', 'windows': [window(m) for m in members]},
                                     {'name': 'Brokerあり', 'windows': [window(broker)]}]}}


def cmd_atelier(api, args):
    """A2A のクライアント Atelier (GitHub の最新) を APPBG / Sandbox に配備し、受講者ごとの snapshot を同梱する。"""
    _, bg1, appbg = ids(api, args)
    gw = gateway_url(api, bg1, sandbox_env(api, bg1), args.gateway)
    urls = member_urls(api, appbg)
    # --names ws00,ws01,ws99 picks participants one by one; otherwise --start / --count make a run of numbers
    if args.names:
        names = [n.strip() for n in args.names.split(',') if n.strip()]
    else:
        names = [f'ws{i:02d}' for i in range(args.start, args.start + args.count)]
    snapshots = {atelier_snapshot_name(n): atelier_snapshot(gw, urls, n) for n in names}
    # a new GAV every time, so yc uploads it; int() drops the leading zero before 10:00 (0836 is not semver)
    version = f"1.{time.strftime('%y%m%d')}.{int(time.strftime('%H%M'))}"
    run = lambda cmd, **kw: subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', **kw)
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'atelier')
        if re.match(r'https?://', args.atelier):
            r = run(['git', '-c', 'core.symlinks=false', 'clone', '-q', '--depth', '1', args.atelier, src])
            if r.returncode != 0:
                sys.exit(f'git clone {args.atelier}: {r.stderr[-300:]}')
        else:
            shutil.copytree(os.path.expanduser(args.atelier), src, ignore=shutil.ignore_patterns('target', '.git'))
        # the snapshots hold this org's URLs, so they go into the copy only, never into the Atelier repository
        for file, snap in snapshots.items():
            json.dump(snap, open(os.path.join(src, 'ui', 'scenarios', file), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=2)
        # list them first in the app's own index, which Import > Repository shows on its Local tab
        index_path = os.path.join(src, 'ui', 'scenarios', 'index.json')
        index = json.load(open(index_path, encoding='utf-8')) if os.path.exists(index_path) else {'items': []}
        mine = [{'id': file[:-len('.json')], 'name': snap['meta']['name'], 'description': snap['meta']['description'],
                 'url': f'/scenarios/{file}', 'counts': {'scripts': 0}} for file, snap in snapshots.items()]
        index['items'] = mine + [it for it in index.get('items', []) if it.get('url') not in {m['url'] for m in mine}]
        json.dump(index, open(index_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        app = os.path.join(src, 'mule-app')
        pom = os.path.join(app, 'pom.xml')
        text = open(pom, encoding='utf-8').read()
        text = re.sub(r'<groupId>[0-9a-f-]{36}</groupId>', f'<groupId>{appbg}</groupId>', text, count=1)
        text = re.sub(r'(<artifactId>atelier-static</artifactId>.*?<version>)[^<]+', rf'\g<1>{version}', text,
                      count=1, flags=re.S)
        # the JMX module (only for /logs) is a private build that is not in every Maven repository; leave it out
        text = re.sub(r'\s*<dependency>\s*<groupId>com\.demo-group</groupId>\s*<artifactId>mule-jmx-module</artifactId>'
                      r'.*?</dependency>', '', text, count=1, flags=re.S)
        open(pom, 'w', encoding='utf-8').write(text)
        jmx = os.path.join(app, 'src', 'main', 'mule', 'impl', 'jmx-endpoints.xml')
        if os.path.exists(jmx):
            os.remove(jmx)
        conf = os.path.join(app, 'src', 'main', 'mule', 'global-config.xml')
        text = open(conf, encoding='utf-8').read()
        open(conf, 'w', encoding='utf-8').write(re.sub(r'\s*<jmx:config [^>]*/>', '', text))
        r = run(['mvn', '-q', '-f', pom, 'clean', 'package', '-DskipTests'], shell=(os.name == 'nt'))
        if r.returncode != 0:
            sys.exit(f'mvn package failed:\n{(r.stdout + r.stderr)[-1500:]}')
        jar = os.path.join(app, 'target', f'atelier-static-{version}-mule-application.jar')
        r = run(['yc', 'deploy', 'file', appbg, sandbox_env(api, appbg), appbg, 'atelier', version, jar,
                 f'target=ch2:{args.target}', 'name=atelier', '+mule.env=ch2'])
        print((r.stdout + r.stderr).strip()[-800:])
    print(f'snapshots: Import > Repository > Local, or /scenarios/{atelier_snapshot_name("wsXX")} (Import > Direct URL)')


def cmd_teardown(api, args):
    """後片付け。アプリ → API インスタンス → ネットワークの Exchange 資産 → Gateway → ユーザー → チーム → BG の順に消す。
    --participant wsXX なら、その受講者の broker (アプリ、API インスタンス、ネットワークの資産) だけを消す。"""
    root, bg1, appbg = ids(api, args)
    plan = []  # (label, path) to DELETE; a path starting with "unpublish:" is a network GAV for the CLI
    mine = (lambda name: True) if not args.participant else \
        (lambda name: name.endswith(f'-{args.participant}') or name.endswith(f'_{args.participant}'))
    for bg in (bg1, appbg):
        if not bg:
            continue
        env = sandbox_env(api, bg)
        dep = f'/amc/application-manager/api/v2/organizations/{bg}/environments/{env}/deployments'
        for d in api.get(dep).get('items', []):
            if mine(d['name']):
                plan.append((f'app {d["name"]}', f'{dep}/{d["id"]}'))
        apis = f'/apimanager/api/v1/organizations/{bg}/environments/{env}/apis'
        for a in api.get(apis).get('assets', []):
            for i in a['apis']:
                if mine(a['assetId']):
                    plan.append((f'api {a["assetId"]} {i["id"]}', f'{apis}/{i["id"]}'))
        # agent network assets refuse the Exchange DELETE (403, even for the admin and the publisher);
        # only `agent-network project unpublish` removes them, together with their agent / mcp / llm assets
        for a in api.get(f'/exchange/api/v2/assets/search?organizationId={bg}&types=agent-network&limit=100'):
            if a.get('type') == 'agent-network' and mine(a['assetId']):
                versions = api.get(f'/exchange/api/v2/assets/{bg}/{a["assetId"]}').get('versions', [])
                for v in sorted({x['version'] for x in versions}, reverse=True):
                    plan.append((f'network {a["assetId"]} {v}', f'unpublish:{bg}:{a["assetId"]}:{v}'))
        if args.participant:
            continue
        gws = f'/gatewaymanager/api/v1/organizations/{bg}/environments/{env}/gateways'
        for g in api.get(gws)['content']:
            plan.append((f'gateway {g["name"]}', f'{gws}/{g["id"]}'))
    if args.date and not args.participant:
        users = api.get(f'/accounts/api/organizations/{root}/users?search=_{args.date}&limit=100')['data']
        for u in users:
            if re.fullmatch(rf'ws\d\d_{args.date}', u['username']):
                plan.append((f'user {u["username"]}', f'/accounts/api/organizations/{root}/users/{u["id"]}'))
    team, _ = find_team(api, root, args.team)
    if team and not args.participant:
        plan.append((f'team {args.team}', f'/accounts/api/organizations/{root}/teams/{team}'))
    for name, bg in ((args.bg1, bg1), (args.appbg, appbg)):
        if bg and not args.participant:
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
        if path.startswith('unpublish:'):
            _, bg, asset, version = path.split(':')
            r = subprocess.run(['anypoint-cli-v4', 'agent-network', 'project', 'unpublish', '--gav', f'{bg}:{asset}:{version}',
                                '--hard-delete', '--username', os.environ['ANYPOINT_USERNAME'],
                                '--password', os.environ['ANYPOINT_PASSWORD'], '--organization', bg],
                               input='yes\n', capture_output=True, text=True, encoding='utf-8', errors='replace',
                               shell=(os.name == 'nt'))
            print(f'{label}: {"ok" if r.returncode == 0 else (r.stdout + r.stderr)[-200:]}')
            continue
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
    p.add_argument('step', choices=['org', 'team', 'users', 'proxy-jwt', 'atelier', 'page', 'show', 'teardown'])
    p.add_argument('--org', help='root org ID (default: the login user\'s org)')
    p.add_argument('--bg1', default='BG1')
    p.add_argument('--appbg', default='APPBG')
    p.add_argument('--appbg-vcores', type=float, default=0.4, help='0.1 per member app and Atelier')
    p.add_argument('--gateway', default='agent-network-shared-gw')
    p.add_argument('--target', default='cloudhub-us-east-2')
    p.add_argument('--team', default='workshop')
    p.add_argument('--count', type=int, default=6)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--names', help='atelier: participants by name, e.g. ws00,ws01,ws99 (instead of --start / --count)')
    p.add_argument('--date', help='YYYYMMDD of the workshop, used in user names')
    p.add_argument('--email', default='tmiyashita+{name}@salesforce.com')
    # an admin can't change a password later (only the e-mailed reset link can), so decide it here
    p.add_argument('--password', default=os.environ.get('WORKSHOP_PASSWORD'),
                   help='users: password of every new participant (default: $WORKSHOP_PASSWORD; not kept in git)')
    p.add_argument('--proxy', default='workshop-llm-proxy')
    p.add_argument('--proxy-path', default='llm', help='Model Proxy base path')
    p.add_argument('--page-asset', default='new-hire-onboarding-handson')
    p.add_argument('--page-tags', default='guide', help='page: comma-separated tags of the Exchange asset')
    p.add_argument('--page-name', default='AI Workshop当日ガイド', help='page: name of the Exchange asset')
    p.add_argument('--llm-model', default='openai/gpt-5-mini', help='page: model the broker asks the Model Proxy for (<provider>/<model>)')
    p.add_argument('--jwt-days', type=int, default=90, help='proxy-jwt: lifetime of a new JWT')
    p.add_argument('--atelier', default=ATELIER_REPO, help='atelier: the Atelier repository (git URL or folder)')
    p.add_argument('--yes', action='store_true', help='teardown: really delete')
    p.add_argument('--participant', help='teardown: only this participant\'s broker (e.g. ws00)')
    p.add_argument('--env', help='environment name for ~/.config/handson/new-hire-onboarding/<env>/ (default: --date)')
    p.add_argument('--out', help='users: where to write passwords (default: <env folder>/users.json)')
    args = p.parse_args()
    if args.step == 'users' and not args.date:
        p.error('users needs --date')
    if args.step == 'users' and not args.password:
        p.error('users needs --password or WORKSHOP_PASSWORD')
    if args.step == 'users' and not args.out:
        envdir = os.path.join(os.path.expanduser('~'), '.config', 'handson', 'new-hire-onboarding', args.env or args.date)
        os.makedirs(envdir, exist_ok=True)
        args.out = os.path.join(envdir, 'users.json')
    api = Api(os.environ['ANYPOINT_USERNAME'], os.environ['ANYPOINT_PASSWORD'])
    {'org': cmd_org, 'team': cmd_team, 'users': cmd_users,
     'proxy-jwt': cmd_proxy_jwt, 'atelier': cmd_atelier, 'page': cmd_page, 'show': cmd_show,
     'teardown': cmd_teardown}[args.step](api, args)


if __name__ == '__main__':
    main()
