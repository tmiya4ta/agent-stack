"""new-hire-onboarding のハンズオン環境を Anypoint に作る (hosting.md の手順 1〜4 と 6 の後半)。

    export ANYPOINT_USERNAME=... ANYPOINT_PASSWORD=...
    python anypoint_setup.py org                      # BG1 / APPBG、vCore、Gateway
    python anypoint_setup.py team                     # チーム workshop と、BG1 / Sandbox への全ロール
    python anypoint_setup.py users --count 6 --date 20261029 --email tmiyashita+{name}@salesforce.com
    python anypoint_setup.py proxy-auth-off           # Model Proxy の Client ID Enforcement を無効にする
    python anypoint_setup.py show                     # 作ったものの ID と URL

すでにあるもの (同じ名前の BG、Gateway、チーム、ユーザー) は作り直さない。
ユーザーのパスワードは --out (既定 ../credentials.local.json、git に入らない) に書く。
"""
import argparse
import json
import os
import re
import secrets
import string
import sys
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


def cmd_proxy_auth_off(api, args):
    _, bg1, _ = ids(api, args)
    env = sandbox_env(api, bg1)
    base = f'/apimanager/api/v1/organizations/{bg1}/environments/{env}/apis'
    inst = [i for a in api.get(base)['assets'] if a['assetId'] == args.proxy for i in a['apis']]
    if not inst:
        sys.exit(f'model proxy {args.proxy} not found; create it with model-proxy.js first')
    policies = api.get(f'{base}/{inst[0]["id"]}/policies')
    policies = policies.get('policies', policies)
    for p in policies:
        if ((p.get('template') or {}).get('assetId') or p.get('assetId')) == 'client-id-enforcement':
            if p.get('disabled'):
                print('client-id-enforcement is already disabled')
                return
            s, body = api.call('PATCH', f'{base}/{inst[0]["id"]}/policies/{p["policyId"]}', {'disabled': True})
            print(f'client-id-enforcement disabled: {s}')
            return
    # a disabled policy drops out of this list
    print('client-id-enforcement not in the active policies (already disabled)')


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
    p.add_argument('step', choices=['org', 'team', 'users', 'proxy-auth-off', 'show'])
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
    p.add_argument('--out', default=os.path.join(HERE, '..', 'credentials.local.json'))
    args = p.parse_args()
    if args.step == 'users' and not args.date:
        p.error('users needs --date')
    api = Api(os.environ['ANYPOINT_USERNAME'], os.environ['ANYPOINT_PASSWORD'])
    {'org': cmd_org, 'team': cmd_team, 'users': cmd_users,
     'proxy-auth-off': cmd_proxy_auth_off, 'show': cmd_show}[args.step](api, args)


if __name__ == '__main__':
    main()
