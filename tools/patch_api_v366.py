#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Applique le correctif v3.66 sur public_html/api.php"""
import sys, io

P = 'public_html/api.php'
s = io.open(P, encoding='utf-8', newline='').read()
orig = s

def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        print('!! ECHEC [%s] : %d occurrence(s) au lieu de %d' % (label, n, count))
        sys.exit(1)
    s = s.replace(old, new, count)
    print('ok  %s' % label)

# ------------------------------------------------------------------ doc
rep(" * Paraveda CRM \u2014 api.php (v3.65)", " * Paraveda CRM \u2014 api.php (v3.66)", '0a. titre v3.66')

rep(""" *   POST api.php {action: ...}         \u2192 Digylog actions  (header X-Sync-Token required)
 *
 * v3.41 hardening:""",
""" *   POST api.php {action: ...}         \u2192 Digylog actions  (header X-Sync-Token required)
 *   GET  api.php                       \u2192 ...+ \"_v\": version d\u00e9ploy\u00e9e (l'app se recharge si elle est en retard)
 *
 * v3.66 \u2014 les modifications ne se perdent plus :
 *   - r\u00e8gle de fusion stricte : une valeur d\u00e9j\u00e0 stock\u00e9e n'est remplac\u00e9e QUE par une
 *     modification explicite plus r\u00e9cente (tampon _f[champ] strictement sup\u00e9rieur).
 *     Une copie p\u00e9rim\u00e9e (ancien cache navigateur) ne peut plus \u00e9craser une date, un prix,
 *     un statut... m\u00eame si son _u est plus r\u00e9cent.
 *   - les tombes (_del) sont d\u00e9finitives : une ligne supprim\u00e9e ne ressuscite plus.
 *   - normalisation des dates (jj/mm/aaaa \u2192 aaaa-mm-jj) \u00e0 l'\u00e9criture.
 *   - garde-fou d'horloge : les tampons _u / _f venant d'un PC en avance sont born\u00e9s
 *     \u00e0 l'heure du serveur + 60 s (sinon un poste d\u00e9cal\u00e9 bloquait les autres).
 *   - journal (audit.log) d\u00e8s qu'une valeur prot\u00e9g\u00e9e est conserv\u00e9e.
 *
 * v3.41 hardening:""", '0b. notes v3.66')

# ------------------------------------------------------------------ crm_norm_date
rep("""/** unwrap {t,d:{t,d:X}} \u2192 X (defensive: corruption produced by old import.php) */
function crm_unwrap($v) {
  $g = 0;
  while (is_array($v) && isset($v['t']) && array_key_exists('d', $v) && is_numeric($v['t']) && count($v) <= 2 && $g++ < 5) { $v = $v['d']; }
  return $v;
}
""",
"""/** unwrap {t,d:{t,d:X}} \u2192 X (defensive: corruption produced by old import.php) */
function crm_unwrap($v) {
  $g = 0;
  while (is_array($v) && isset($v['t']) && array_key_exists('d', $v) && is_numeric($v['t']) && count($v) <= 2 && $g++ < 5) { $v = $v['d']; }
  return $v;
}
/** v3.66: normalise une date (jj/mm/aaaa ou jj-mm-aaaa \u2192 aaaa-mm-jj). Le reste est laiss\u00e9 tel quel. */
function crm_norm_date($v) {
  $s = trim((string)$v);
  if ($s === '') return '';
  if (preg_match('~^(\\d{4})[-/.](\\d{1,2})[-/.](\\d{1,2})~', $s, $m)) {
    return $m[1] . '-' . str_pad($m[2], 2, '0', STR_PAD_LEFT) . '-' . str_pad($m[3], 2, '0', STR_PAD_LEFT);
  }
  if (preg_match('~^(\\d{1,2})[-/.](\\d{1,2})[-/.](\\d{4})$~', $s, $m)) {
    $dd = (int)$m[1]; $mm = (int)$m[2]; $yy = (int)$m[3];
    if ($mm >= 1 && $mm <= 12 && $dd >= 1 && $dd <= 31) {
      return $yy . '-' . str_pad((string)$mm, 2, '0', STR_PAD_LEFT) . '-' . str_pad((string)$dd, 2, '0', STR_PAD_LEFT);
    }
  }
  return substr($s, 0, 10);
}
""", '1. crm_norm_date')

# ------------------------------------------------------------------ crm_merge_row
OLD = """// v3.65: field-level merge \u2014 a field edited later (per-field stamp _f) is never overwritten
// by a whole-row write coming from a browser that still held an older copy of the row.
function crm_merge_row($a, $b) {
  $ua = isset($a['_u']) ? (float)$a['_u'] : 0; $ub = isset($b['_u']) ? (float)$b['_u'] : 0;
  $base = $ub >= $ua ? $b : $a; $oth = $ub >= $ua ? $a : $b;
  if (!empty($base['_del']) || !empty($oth['_del'])) return $base;
  $bf = (isset($base['_f']) && is_array($base['_f'])) ? $base['_f'] : array();
  $of = (isset($oth['_f']) && is_array($oth['_f'])) ? $oth['_f'] : array();
  foreach ($of as $k => $to) {
    $to = (float)$to; $tb = isset($bf[$k]) ? (float)$bf[$k] : 0;
    if ($to > $tb && array_key_exists($k, $oth)) { $base[$k] = $oth[$k]; $bf[$k] = $to; }
  }
  if ($bf) $base['_f'] = $bf;
  return $base;
}"""

NEW = """// v3.66: r\u00e8gle stricte \u2014 $a = ligne d\u00e9j\u00e0 stock\u00e9e (r\u00e9f\u00e9rence), $b = ligne entrante (navigateur).
// Un champ d\u00e9j\u00e0 enregistr\u00e9 n'est remplac\u00e9 QUE si la ligne entrante porte un tampon _f[champ]
// strictement plus r\u00e9cent. Une copie p\u00e9rim\u00e9e ne peut donc plus \u00e9craser une date / un prix / un statut,
// m\u00eame si son _u est plus r\u00e9cent. Seules les vraies modifications (toujours tamponn\u00e9es par l'app) passent.
function crm_merge_row($a, $b) {
  $ua = isset($a['_u']) ? (float)$a['_u'] : 0; $ub = isset($b['_u']) ? (float)$b['_u'] : 0;
  if (!empty($a['_del'])) { $r = $a; $r['_u'] = max($ua, $ub); return $r; }   // tombe en place : on ne ressuscite pas
  if (!empty($b['_del'])) { $r = $b; $r['_u'] = max($ua, $ub); return $r; }   // demande de suppression
  $sf = (isset($a['_f']) && is_array($a['_f'])) ? $a['_f'] : array();
  $bf = (isset($b['_f']) && is_array($b['_f'])) ? $b['_f'] : array();
  $out = $a; $nf = null; $kept = array();
  $keys = array_unique(array_merge(array_keys($a), array_keys($b)));
  foreach ($keys as $k) {
    if ($k === 'id' || $k === '_u' || $k === '_f' || $k === '_del') continue;
    $sv = array_key_exists($k, $out) ? $out[$k] : null;
    $iv = array_key_exists($k, $b) ? $b[$k] : null;
    if (is_array($sv) || is_array($iv)) { $it0 = isset($bf[$k]) ? (float)$bf[$k] : 0; $st0 = isset($sf[$k]) ? (float)$sf[$k] : 0; if ($it0 > $st0) { $out[$k] = $iv; if ($nf === null) $nf = $sf; $nf[$k] = $it0; } continue; }
    $st = isset($sf[$k]) ? (float)$sf[$k] : 0;
    $it = isset($bf[$k]) ? (float)$bf[$k] : 0;
    if ((string)$sv === (string)$iv) { if ($it > $st) { if ($nf === null) $nf = $sf; $nf[$k] = $it; } continue; }
    if ($k === '_d') {                                     // brouillon (1) / publi\u00e9 (0)
      if ((string)$iv === '1') { if ($it > $st) { $out[$k] = $iv; if ($nf === null) $nf = $sf; $nf[$k] = $it; } }
      elseif ($ub > $ua) { $out[$k] = $iv; }
      continue;
    }
    if (!array_key_exists($k, $a)) { $out[$k] = $iv; if ($it > $st) { if ($nf === null) $nf = $sf; $nf[$k] = $it; } continue; }
    if ($it > $st) { $out[$k] = $iv; if ($nf === null) $nf = $sf; $nf[$k] = $it; continue; }
    $kept[] = $k;                                          // valeur prot\u00e9g\u00e9e
  }
  $out['_u'] = max($ua, $ub);
  if ($nf !== null) $out['_f'] = $nf;
  if ($kept && isset($a['id'])) {
    crm_audit('protect | id=' . $a['id'] . ' | fields=' . implode(',', array_slice($kept, 0, 8))
      . ' | in_u=' . (int)$ub . ' | srv_u=' . (int)$ua);
  }
  return $out;
}"""
rep(OLD, NEW, '2. crm_merge_row v3.66')

# ------------------------------------------------------------------ normalisation + horloge
rep("""  $d = crm_unwrap($b['d']);
  $t = isset($b['t']) ? (int)$b['t'] : (int)(microtime(true) * 1000);
  $now = (int)(microtime(true) * 1000);
  if ($t > $now + 60000) $t = $now; // clock skew guard
""",
"""  $d = crm_unwrap($b['d']);
  $t = isset($b['t']) ? (int)$b['t'] : (int)(microtime(true) * 1000);
  $now = (int)(microtime(true) * 1000);
  if ($t > $now + 60000) $t = $now; // clock skew guard

  // v3.66: bornage d'horloge + normalisation des dates sur les lignes de commandes
  if ($k === 'paraveda_orders_v5' && is_array($d)) {
    $capMs = (microtime(true) * 1000) + 60000;
    $dateKeys = array('dateCreation', 'dateConfirmation', 'dateExp', 'dateLiv');
    foreach ($d as $idx => $o) {
      if (!is_array($o)) continue;
      if (isset($o['_u']) && (float)$o['_u'] > $capMs) $d[$idx]['_u'] = $capMs;
      if (isset($o['_f']) && is_array($o['_f'])) {
        foreach ($o['_f'] as $fk => $fv) { if ((float)$fv > $capMs) $d[$idx]['_f'][$fk] = $capMs; }
      }
      foreach ($dateKeys as $dk) {
        if (isset($d[$idx][$dk])) $d[$idx][$dk] = crm_norm_date($d[$idx][$dk]);
      }
    }
  }
""", '3. bornage horloge + normalisation dates')

# ------------------------------------------------------------------ GET : version d\u00e9ploy\u00e9e
rep("""  echo json_encode($data, JSON_UNESCAPED_UNICODE);
  exit;
}

/* ---------- POST ---------- */""",
"""  $data['_v'] = '3.66';   // v3.66: l'application se recharge automatiquement si elle est en retard
  echo json_encode($data, JSON_UNESCAPED_UNICODE);
  exit;
}

/* ---------- POST ---------- */""", '4. GET renvoie _v')

rep("if ($a === 'ping') crm_out(array('ok'=>true, 'v'=>'3.38'));",
    "if ($a === 'ping') crm_out(array('ok'=>true, 'v'=>'3.66'));", '5. ping v3.66')

if s == orig:
    print('!! aucun changement')
    sys.exit(1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\napi.php patch\u00e9 (%d -> %d octets)' % (len(orig), len(s)))
