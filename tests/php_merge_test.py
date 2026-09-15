# -*- coding: utf-8 -*-
"""Transcription fidèle en Python de crm_merge_row / crm_norm_date (api.php v3.66)
   + les mêmes scénarios que le test JS, pour vérifier la logique serveur."""
import re

def crm_norm_date(v):
    s = str(v if v is not None else '').strip()
    if s == '':
        return ''
    m = re.match(r'^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', s)
    if m:
        return '%s-%s-%s' % (m.group(1), m.group(2).zfill(2), m.group(3).zfill(2))
    m = re.match(r'^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$', s)
    if m:
        dd, mm, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            return '%s-%s-%s' % (yy, str(mm).zfill(2), str(dd).zfill(2))
    return s[:10]


def crm_merge_row(a, b):
    ua = float(a.get('_u') or 0)
    ub = float(b.get('_u') or 0)
    if a.get('_del'):
        r = dict(a); r['_u'] = max(ua, ub); return r
    if b.get('_del'):
        r = dict(b); r['_u'] = max(ua, ub); return r
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
        if isinstance(sv, (list, dict)) or isinstance(iv, (list, dict)):
            it0 = float(bf.get(k) or 0); st0 = float(sf.get(k) or 0)
            if it0 > st0:
                out[k] = iv
                if nf is None: nf = dict(sf)
                nf[k] = it0
            continue
        st = float(sf.get(k) or 0)
        it = float(bf.get(k) or 0)

        def sstr(x):
            return '' if x is None else str(x)
        if sstr(sv) == sstr(iv):
            if it > st:
                if nf is None: nf = dict(sf)
                nf[k] = it
            continue
        if k == '_d':
            if sstr(iv) == '1':
                if it > st:
                    out[k] = iv
                    if nf is None: nf = dict(sf)
                    nf[k] = it
            elif ub > ua:
                out[k] = iv
            continue
        if k not in a:
            out[k] = iv
            if it > st:
                if nf is None: nf = dict(sf)
                nf[k] = it
            continue
        if it > st:
            out[k] = iv
            if nf is None: nf = dict(sf)
            nf[k] = it
            continue
        kept.append(k)
    out['_u'] = max(ua, ub)
    if nf is not None:
        out['_f'] = nf
    out['__kept'] = kept
    return out


def server_write(cur, inc):
    by = {str(o['id']): o for o in cur if o.get('id') is not None}
    for o in inc:
        if o.get('id') is None:
            continue
        i = str(o['id'])
        by[i] = crm_merge_row(by[i], o) if i in by else o
    return list(by.values())


T0, TA, TB, TC = 1789000000000, 1789100000000, 1789200000000, 1789300000000
base = {'id': 1, 'dateCreation': '2026-09-10', 'statut': '', 'livraison': '',
        'nom': 'Zineb', 'ville': 'Casa', '_u': T0}
P = total = 0


def chk(name, ok, info=''):
    global P, total
    print(('  ✅ ' if ok else '  ❌ ') + name + (' — ' + info if info else ''))
    total += 1
    P += 1 if ok else 0


print('=== crm_norm_date ===')
chk('ISO', crm_norm_date('2026-08-01') == '2026-08-01', crm_norm_date('2026-08-01'))
chk('ISO datetime', crm_norm_date('2026-08-01T23:00:00.000Z') == '2026-08-01', crm_norm_date('2026-08-01T23:00:00.000Z'))
chk('jj/mm/aaaa', crm_norm_date('01/08/2026') == '2026-08-01', crm_norm_date('01/08/2026'))
chk('jj-mm-aaaa', crm_norm_date('01-08-2026') == '2026-08-01', crm_norm_date('01-08-2026'))
chk('vide', crm_norm_date('') == '')

print('\n=== crm_merge_row (logique serveur v3.66) ===')
s = server_write([dict(base)], [dict(base, dateCreation='2026-08-01', _u=TA, _f={'dateCreation': TA})])
s = server_write(s, [dict(base, statut='Confirmé', _u=TB, _f={'statut': TB})])
r = [x for x in s if x['id'] == 1][0]
chk('1. date corrigée par A + statut par B', r['dateCreation'] == '2026-08-01' and r['statut'] == 'Confirmé',
    "date=%s statut=%s" % (r['dateCreation'], r['statut']))

s = server_write([{'id': 1, 'dateCreation': '2026-08-01', 'statut': '', '_u': TA, '_f': {'dateCreation': TA}}],
                 [{'id': 1, 'dateCreation': '2026-09-14', 'statut': 'Confirmé', '_u': TB, '_f': {'statut': TB}}])
r = [x for x in s if x['id'] == 1][0]
chk('2. copie périmée sans _f : la date est protégée', r['dateCreation'] == '2026-08-01' and r['statut'] == 'Confirmé',
    "date=%s statut=%s" % (r['dateCreation'], r['statut']))

m = crm_merge_row({'id': 1, 'dateCreation': '2026-08-01', '_u': TA, '_f': {'dateCreation': TA}},
                  {'id': 1, 'dateCreation': '2026-09-10', '_u': T0})
chk('3. snapshot serveur + cache local périmé', m['dateCreation'] == '2026-08-01', m['dateCreation'])

s = server_write([{'id': 1, 'dateCreation': '2026-08-01', '_u': TA, '_f': {'dateCreation': TA}}],
                 [{'id': 1, 'dateCreation': '2026-08-05', '_u': TC, '_f': {'dateCreation': TC}}])
chk('4. modification plus récente acceptée', [x for x in s if x['id'] == 1][0]['dateCreation'] == '2026-08-05')

s = server_write([{'id': 2, 'nom': 'A', '_u': TA}], [{'id': 2, 'nom': 'A', '_del': 1, '_u': TB}])
chk('5. suppression propagée', bool([x for x in s if x['id'] == 2][0].get('_del')))

s = server_write([{'id': 2, 'nom': 'A', '_del': 1, '_u': TA}],
                 [{'id': 2, 'nom': 'A', 'statut': 'Confirmé', '_u': TB, '_f': {'statut': TB}}])
chk('6. tombe définitive', bool([x for x in s if x['id'] == 2][0].get('_del')))

s = server_write([{'id': 3, 'ville': 'Rabat', '_u': T0}], [{'id': 3, 'ville': '', '_u': TA, '_f': {'ville': TA}}])
s = server_write(s, [{'id': 3, 'ville': 'Rabat', 'statut': 'Confirmé', '_u': TB, '_f': {'statut': TB}}])
r = [x for x in s if x['id'] == 3][0]
chk('7. vider un champ reste vide', r['ville'] == '' and r['statut'] == 'Confirmé', "ville=%r statut=%s" % (r['ville'], r['statut']))

s = server_write([{'id': 4, '_d': 1, '_u': TA}], [{'id': 4, '_d': 0, '_u': TB, '_f': {'_d': TB}}])
r1 = [x for x in s if x['id'] == 4][0]
s = server_write(s, [{'id': 4, '_d': 1, 'statut': 'Confirmé', '_u': TC, '_f': {'statut': TC}}])
r2 = [x for x in s if x['id'] == 4][0]
chk('8. publication + pas de retour brouillon', str(r1['_d']) == '0' and str(r2['_d']) == '0')

s = server_write([{'id': 5, 'nom': 'A', '_u': TA}], [{'id': 6, 'dateCreation': '2026-08-01', 'nom': 'B', '_u': TB}])
r = [x for x in s if x['id'] == 6][0]
chk('9. nouvelle ligne intacte', r['nom'] == 'B' and r['dateCreation'] == '2026-08-01')

print('\n%d/%d cas OK' % (P, total))
raise SystemExit(0 if P == total else 1)
