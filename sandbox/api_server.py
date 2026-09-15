#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serveur de DÉMONSTRATION (bac à sable) pour tester la v3.66 avant déploiement.

Reproduit le comportement de public_html/api.php (même règle de fusion stricte)
en Python, pour pouvoir lancer le CRM en preview.

Usage:  python3 sandbox/api_server.py [port]
"""
import json, os, re, sys, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from socketserver import ThreadingMixIn

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.dirname(BASE), 'public_html')      # fichiers de l'app
DATA_FILE = os.path.join(BASE, 'data', 'crm_data.json')        # données du bac à sable
SECRET = 'c6e04cb5de9088be01a685abc243995a80426eba45de2060'
VERSION = '3.66'
LOCK = None

ALLOWED_KEYS = [
    'paraveda_users_v1','paraveda_orders_v5','paraveda_agent_names_v1','paraveda_chat_v1',
    'paraveda_worktimes_v1','paraveda_remarques_v1','paraveda_avances_v1','paraveda_adspend_v1',
    'paraveda_perfrows_v1','paraveda_livraison_v1','paraveda_history_v1','paraveda_villes_v2',
    'paraveda_catalog_v1','sheet_pièce','paraveda_team_photos_v1','tabs_list_v1',
    'custom_sheets_v1','paraveda_period_v1','paraveda_period_v2',
    'paraveda_backup_v1','paraveda_backup_v1_agents','paraveda_reset_v1'
]


# ----------------------------------------------------------------- outillage
def now_ms():
    return int(time.time() * 1000)


def norm_date(v):
    s = '' if v is None else str(v).strip()
    if s == '':
        return ''
    m = re.match(r'^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', s)
    if m:
        return '%s-%s-%s' % (m.group(1), m.group(2).zfill(2), m.group(3).zfill(2))
    m = re.match(r'^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$', s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return '%s-%s-%s' % (y, str(mo).zfill(2), str(d).zfill(2))
    return s[:10]


def sstr(x):
    return '' if x is None else str(x)


def merge_row(a, b):
    """a = ligne stockée (référence), b = ligne entrante (navigateur). Règle v3.66."""
    ua = float(a.get('_u') or 0)
    ub = float(b.get('_u') or 0)
    if a.get('_del'):
        return dict(a, _u=max(ua, ub))
    if b.get('_del'):
        return dict(b, _u=max(ua, ub))
    sf = a.get('_f') if isinstance(a.get('_f'), dict) else {}
    bf = b.get('_f') if isinstance(b.get('_f'), dict) else {}
    out = dict(a)
    nf = None
    kept = []
    for k in list(dict.fromkeys(list(a.keys()) + list(b.keys()))):
        if k in ('id', '_u', '_f', '_del'):
            continue
        sv = out.get(k)
        iv = b.get(k)
        st = float(sf.get(k) or 0)
        it = float(bf.get(k) or 0)
        if sstr(sv) == sstr(iv):
            if it > st:
                if nf is None:
                    nf = dict(sf)
                nf[k] = it
            continue
        if k == '_d':
            if sstr(iv) == '1':
                if it > st:
                    out[k] = iv
                    if nf is None:
                        nf = dict(sf)
                    nf[k] = it
            elif ub > ua:
                out[k] = iv
            continue
        if k not in a:
            out[k] = iv
            if it > st:
                if nf is None:
                    nf = dict(sf)
                nf[k] = it
            continue
        if it > st:
            out[k] = iv
            if nf is None:
                nf = dict(sf)
            nf[k] = it
            continue
        kept.append(k)
    out['_u'] = max(ua, ub)
    if nf is not None:
        out['_f'] = nf
    if kept:
        print('   [protect] id=%s champs=%s' % (a.get('id'), ','.join(kept[:8])), flush=True)
    return out


def merge_orders(cur, inc):
    by = {str(o['id']): o for o in cur if isinstance(o, dict) and o.get('id') is not None}
    for o in inc:
        if not isinstance(o, dict) or o.get('id') is None:
            continue
        i = str(o['id'])
        by[i] = merge_row(by[i], o) if i in by else o
    out = list(by.values())
    out.sort(key=lambda r: -float(r.get('id') or 0))
    return out


def read_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def write_data(data):
    tmp = DATA_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)


# ----------------------------------------------------------------- handlers
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Sync-Token')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._json({'ok': True})

    def do_GET(self):
        path = self.path.split('?')[0]
        if path.rstrip('/').endswith('api.php'):
            if self.headers.get('X-Sync-Token') != SECRET:
                return self._json({'ok': False, 'err': 'token'}, 403)
            data = read_data()
            data['_v'] = VERSION
            return self._json(data)
        if path in ('/', ''):
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        path = self.path.split('?')[0]
        if not path.rstrip('/').endswith('api.php'):
            return self._json({'ok': False, 'err': 'not-found'}, 404)
        if self.headers.get('X-Sync-Token') != SECRET:
            return self._json({'ok': False, 'err': 'token'}, 403)
        n = int(self.headers.get('Content-Length') or 0)
        try:
            body = json.loads(self.rfile.read(n).decode('utf-8'))
        except Exception:
            return self._json({'ok': False, 'err': 'bad-json'}, 400)

        if 'action' in body:
            a = str(body.get('action'))
            if a == 'ping':
                return self._json({'ok': True, 'v': VERSION})
            return self._json({'ok': False, 'err': 'unknown-action'}, 400)

        key = body.get('key')
        if key not in ALLOWED_KEYS:
            return self._json({'ok': False, 'err': 'key-not-allowed'}, 400)
        if 'd' not in body:
            return self._json({'ok': False, 'err': 'bad-body'}, 400)

        d = body['d']
        t = int(body.get('t') or now_ms())
        now = now_ms()
        if t > now + 60000:
            t = now

        if key == 'paraveda_orders_v5' and isinstance(d, list):
            cap = now + 60000
            for idx, o in enumerate(d):
                if not isinstance(o, dict):
                    continue
                if o.get('_u') and float(o['_u']) > cap:
                    d[idx]['_u'] = cap
                if isinstance(o.get('_f'), dict):
                    for k, v in list(o['_f'].items()):
                        if float(v or 0) > cap:
                            d[idx]['_f'][k] = cap
                for dk in ('dateCreation', 'dateConfirmation', 'dateExp', 'dateLiv'):
                    if dk in o:
                        d[idx][dk] = norm_date(o[dk])

        data = read_data()
        prev = data.get(key)
        if key == 'paraveda_orders_v5' and isinstance(d, list) and prev and isinstance(prev.get('d'), list):
            d = merge_orders(prev['d'], d)
        data[key] = {'t': t, 'd': d}
        write_data(data)
        print('   [write] %s t=%s rows=%s' % (key, t, len(d) if isinstance(d, list) else '-'), flush=True)
        return self._json({'ok': True})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        write_data({})
    print('Bac a sable Paraveda CRM v%s sur http://0.0.0.0:%d' % (VERSION, port), flush=True)
    Server(('0.0.0.0', port), Handler).serve_forever()
