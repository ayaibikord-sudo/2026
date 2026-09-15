<?php
/**
 * Paraveda CRM — api.php (v3.66)
 *
 * Contract used by index.html (unchanged):
 *   GET  api.php                       → { key: {t, d}, ... }
 *   POST api.php {key, t, d}           → {ok:true}        (header X-Sync-Token required)
 *   POST api.php {action: ...}         → Digylog actions  (header X-Sync-Token required)
 *   GET  api.php                       → ...+ "_v": version déployée (l'app se recharge si elle est en retard)
 *
 * v3.66 — les modifications ne se perdent plus :
 *   - règle de fusion stricte : une valeur déjà stockée n'est remplacée QUE par une
 *     modification explicite plus récente (tampon _f[champ] strictement supérieur).
 *     Une copie périmée (ancien cache navigateur) ne peut plus écraser une date, un prix,
 *     un statut... même si son _u est plus récent.
 *   - les tombes (_del) sont définitives : une ligne supprimée ne ressuscite plus.
 *   - normalisation des dates (jj/mm/aaaa → aaaa-mm-jj) à l'écriture.
 *   - garde-fou d'horloge : les tampons _u / _f venant d'un PC en avance sont bornés
 *     à l'heure du serveur + 60 s (sinon un poste décalé bloquait les autres).
 *   - journal (audit.log) dès qu'une valeur protégée est conservée.
 *
 * v3.41 hardening:
 *   - key whitelist (only known CRM keys are accepted)
 *   - stale-write rejection (older `t` than stored never overwrites newer data)
 *   - unwrap protection (rejects double-wrapped {t,d:{t,d}} payloads → fixes corrupted custom_sheets / team_photos)
 *   - exclusive lock around read-modify-write (two agents saving at once no longer lose a write)
 *   - rotating backups (last 30 writes + 1 per day) instead of a single .backup that got overwritten
 *   - payload size limit + minimal audit log
 *   - data dir outside public_html when available (../crm-paraveda-data), falls back to local file
 */
error_reporting(E_ALL);
ini_set('display_errors', '0');

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: Content-Type, X-Sync-Token');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') { exit; }

/* ---------- config ---------- */
$SECRET = 'c6e04cb5de9088be01a685abc243995a80426eba45de2060';

$DATA_DIR = __DIR__ . '/../crm-paraveda-data';
if (!is_dir($DATA_DIR) || !is_writable($DATA_DIR)) { $DATA_DIR = __DIR__; }
$DATA_FILE   = $DATA_DIR . '/crm_data.json';
$LOCK_FILE   = $DATA_DIR . '/.crm.lock';
$BACKUP_DIR  = $DATA_DIR . '/backups';
$AUDIT_FILE  = $DATA_DIR . '/audit.log';
$MAX_BODY    = 12 * 1024 * 1024;   // 12 MB per write
$KEEP_WRITES = 30;                 // rotating pre-write backups
$KEEP_DAYS   = 30;                 // daily snapshots

$ALLOWED_KEYS = array(
  'paraveda_users_v1','paraveda_orders_v5','paraveda_agent_names_v1','paraveda_chat_v1',
  'paraveda_worktimes_v1','paraveda_remarques_v1','paraveda_avances_v1','paraveda_adspend_v1',
  'paraveda_perfrows_v1','paraveda_livraison_v1','paraveda_history_v1','paraveda_villes_v2',
  'paraveda_catalog_v1','sheet_pièce','paraveda_team_photos_v1','tabs_list_v1',
  'custom_sheets_v1','paraveda_period_v1','paraveda_period_v2',
  'paraveda_backup_v1','paraveda_backup_v1_agents','paraveda_reset_v1'
);

/* ---------- helpers ---------- */
function crm_token() {
  if (isset($_SERVER['HTTP_X_SYNC_TOKEN'])) return (string)$_SERVER['HTTP_X_SYNC_TOKEN'];
  if (isset($_GET['token'])) return (string)$_GET['token'];
  return '';
}
function crm_out($arr, $code = 200) {
  if ($code !== 200) http_response_code($code);
  echo json_encode($arr, JSON_UNESCAPED_UNICODE);
  exit;
}
function crm_audit($line) {
  global $AUDIT_FILE;
  $ip = $_SERVER['REMOTE_ADDR'] ?? '-';
  @file_put_contents($AUDIT_FILE, date('Y-m-d H:i:s') . " | $ip | $line\n", FILE_APPEND | LOCK_EX);
  if (@filesize($AUDIT_FILE) > 2 * 1024 * 1024) { @rename($AUDIT_FILE, $AUDIT_FILE . '.1'); }
}
/** v3.41: afrizon_* → paraveda_* (rename), keeps newest if both exist */
function crm_migrate_keys($j) {
  $o = array();
  foreach ($j as $k => $v) {
    $nk = (strpos($k, 'afrizon_') === 0) ? 'paraveda_' . substr($k, 8) : $k;
    if (isset($o[$nk]) && isset($o[$nk]['t']) && isset($v['t']) && $o[$nk]['t'] >= $v['t']) continue;
    $o[$nk] = $v;
  }
  return $o;
}
function crm_read_raw() {
  global $DATA_FILE;
  if (!file_exists($DATA_FILE)) return array();
  $s = @file_get_contents($DATA_FILE);
  $j = json_decode((string)$s, true);
  if (is_array($j)) return crm_migrate_keys($j);
  // corrupted main file → try newest backup
  global $BACKUP_DIR;
  $c = glob($BACKUP_DIR . '/b-*.json');
  if ($c) { rsort($c); foreach ($c as $f) { $j = json_decode((string)@file_get_contents($f), true); if (is_array($j)) { crm_audit("recover | from=" . basename($f)); return $j; } } }
  return array();
}
/** unwrap {t,d:{t,d:X}} → X (defensive: corruption produced by old import.php) */
function crm_unwrap($v) {
  $g = 0;
  while (is_array($v) && isset($v['t']) && array_key_exists('d', $v) && is_numeric($v['t']) && count($v) <= 2 && $g++ < 5) { $v = $v['d']; }
  return $v;
}
/** v3.66: normalise une date (jj/mm/aaaa ou jj-mm-aaaa → aaaa-mm-jj). Le reste est laissé tel quel. */
function crm_norm_date($v) {
  $s = trim((string)$v);
  if ($s === '') return '';
  if (preg_match('~^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})~', $s, $m)) {
    return $m[1] . '-' . str_pad($m[2], 2, '0', STR_PAD_LEFT) . '-' . str_pad($m[3], 2, '0', STR_PAD_LEFT);
  }
  if (preg_match('~^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$~', $s, $m)) {
    $dd = (int)$m[1]; $mm = (int)$m[2]; $yy = (int)$m[3];
    if ($mm >= 1 && $mm <= 12 && $dd >= 1 && $dd <= 31) {
      return $yy . '-' . str_pad((string)$mm, 2, '0', STR_PAD_LEFT) . '-' . str_pad((string)$dd, 2, '0', STR_PAD_LEFT);
    }
  }
  return substr($s, 0, 10);
}
function crm_backup() {
  global $DATA_FILE, $BACKUP_DIR, $KEEP_WRITES, $KEEP_DAYS;
  if (!file_exists($DATA_FILE)) return;
  if (!is_dir($BACKUP_DIR)) @mkdir($BACKUP_DIR, 0755, true);
  if (!is_dir($BACKUP_DIR)) return;
  @copy($DATA_FILE, $BACKUP_DIR . '/b-' . date('Ymd-His') . '-' . substr((string)microtime(true) * 1000 % 1000, 0, 3) . '.json');
  $daily = $BACKUP_DIR . '/d-' . date('Ymd') . '.json';
  if (!file_exists($daily)) @copy($DATA_FILE, $daily);
  // rotate
  $b = glob($BACKUP_DIR . '/b-*.json'); if ($b && count($b) > $KEEP_WRITES) { sort($b); foreach (array_slice($b, 0, count($b) - $KEEP_WRITES) as $f) @unlink($f); }
  $d = glob($BACKUP_DIR . '/d-*.json'); if ($d && count($d) > $KEEP_DAYS)   { sort($d); foreach (array_slice($d, 0, count($d) - $KEEP_DAYS) as $f) @unlink($f); }
}
// v3.66: règle stricte — $a = ligne déjà stockée (référence), $b = ligne entrante (navigateur).
// Un champ déjà enregistré n'est remplacé QUE si la ligne entrante porte un tampon _f[champ]
// strictement plus récent. Une copie périmée ne peut donc plus écraser une date / un prix / un statut,
// même si son _u est plus récent. Seules les vraies modifications (toujours tamponnées par l'app) passent.
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
    if ($k === '_d') {                                     // brouillon (1) / publié (0)
      if ((string)$iv === '1') { if ($it > $st) { $out[$k] = $iv; if ($nf === null) $nf = $sf; $nf[$k] = $it; } }
      elseif ($ub > $ua) { $out[$k] = $iv; }
      continue;
    }
    if (!array_key_exists($k, $a)) { $out[$k] = $iv; if ($it > $st) { if ($nf === null) $nf = $sf; $nf[$k] = $it; } continue; }
    if ($it > $st) { $out[$k] = $iv; if ($nf === null) $nf = $sf; $nf[$k] = $it; continue; }
    $kept[] = $k;                                          // valeur protégée
  }
  $out['_u'] = max($ua, $ub);
  if ($nf !== null) $out['_f'] = $nf;
  if ($kept && isset($a['id'])) {
    crm_audit('protect | id=' . $a['id'] . ' | fields=' . implode(',', array_slice($kept, 0, 8))
      . ' | in_u=' . (int)$ub . ' | srv_u=' . (int)$ua);
  }
  return $out;
}
function crm_merge_orders($cur, $in, $reset = 0) {
  $byId = array(); $order = array();
  foreach ($cur as $o) { if (!is_array($o) || !isset($o['id'])) continue; $id = (string)$o['id']; $byId[$id] = $o; $order[] = $id; }
  foreach ($in as $o) {
    if (!is_array($o) || !isset($o['id'])) continue;
    $id = (string)$o['id'];
    if (!isset($byId[$id])) {
      // v3.62: rows older than the last reset (coming from a stale browser cache) are never resurrected
      $u = isset($o['_u']) ? (float)$o['_u'] : 0;
      if ($reset > 0 && $u < $reset) continue;
      $byId[$id] = $o; $order[] = $id; continue;
    }
    $byId[$id] = crm_merge_row($byId[$id], $o);
  }
  $out = array(); foreach (array_unique($order) as $id) $out[] = $byId[$id];
  usort($out, function($x, $y) { $a = (float)$x['id']; $b = (float)$y['id']; return $a == $b ? 0 : ($a < $b ? 1 : -1); });
  return $out;
}
function crm_write($data) {
  global $DATA_FILE;
  $tmp = $DATA_FILE . '.tmp.' . getmypid();
  $json = json_encode($data, JSON_UNESCAPED_UNICODE);
  if ($json === false) return false;
  if (@file_put_contents($tmp, $json, LOCK_EX) === false) return false;
  if (!@rename($tmp, $DATA_FILE)) { @unlink($tmp); return false; }
  return true;
}

$m = $_SERVER['REQUEST_METHOD'] ?? 'GET';

/* ---------- GET: full snapshot ---------- */
if ($m === 'GET') {
  // v3.41: la lecture exige aussi le token (avant: n'importe qui avec l'URL téléchargeait tous les clients)
  if (!hash_equals($SECRET, crm_token())) crm_out(array('ok'=>false, 'err'=>'token'), 403);
  $data = crm_read_raw();
  // normalise on the way out so old corrupted entries never reach the browser
  foreach ($data as $k => $v) {
    if (is_array($v) && array_key_exists('d', $v)) { $data[$k]['d'] = crm_unwrap($v['d']); }
  }
  $data['_v'] = '3.66';   // v3.66: l'application se recharge automatiquement si elle est en retard
  echo json_encode($data, JSON_UNESCAPED_UNICODE);
  exit;
}

/* ---------- POST ---------- */
if ($m === 'POST') {
  if (!hash_equals($SECRET, crm_token())) crm_out(array('ok'=>false, 'err'=>'token'), 403);

  $raw = file_get_contents('php://input');
  if (strlen($raw) > $MAX_BODY) crm_out(array('ok'=>false, 'err'=>'too-large'), 413);
  $b = json_decode($raw, true);
  if (!is_array($b)) crm_out(array('ok'=>false, 'err'=>'bad-json'), 400);

  /* -- actions (Digylog etc.) -- */
  if (isset($b['action'])) {
    $a = (string)$b['action'];
    if ($a === 'ping') crm_out(array('ok'=>true, 'v'=>'3.66'));
    if ($a === 'restore') crm_out(array('ok'=>false, 'err'=>'restore-not-implemented', 'msg'=>'الاسترجاع كيدار يدوياً من مجلد backups'), 501);
    if (strpos($a, 'digylog') === 0) crm_out(array('ok'=>false, 'err'=>'digylog-removed', 'msg'=>'الربط مع Digylog تحيد فـ v3.41'), 410);
    crm_out(array('ok'=>false, 'err'=>'unknown-action'), 400);
  }

  /* -- normal key write -- */
  if (!isset($b['key']) || !array_key_exists('d', $b)) crm_out(array('ok'=>false, 'err'=>'bad-body'), 400);
  $k = (string)$b['key'];
  if (strpos($k, 'afrizon_') === 0) $k = 'paraveda_' . substr($k, 8); // old tabs
  if (!in_array($k, $ALLOWED_KEYS, true)) { crm_audit("reject | key=$k | not-allowed"); crm_out(array('ok'=>false, 'err'=>'key-not-allowed'), 400); }

  $d = crm_unwrap($b['d']);
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

  // v3.62: reset epoch — writes of wiped keys carrying data older than the reset are ignored
  $__cur0 = crm_read_raw();
  $RESET_T = isset($__cur0['paraveda_reset_v1']['t']) ? (int)$__cur0['paraveda_reset_v1']['t'] : 0;
  $RESET_KEYS = array('paraveda_catalog_v1','sheet_pièce','paraveda_history_v1','paraveda_adspend_v1','paraveda_perfrows_v1','paraveda_backup_v1');
  if ($RESET_T > 0 && in_array($k, $RESET_KEYS, true) && $t < $RESET_T) { crm_audit("reset-stale | key=$k | t=$t < reset=$RESET_T"); crm_out(array('ok'=>true, 'noop'=>'reset-stale', 'reset'=>$RESET_T)); }
  if ($k === 'paraveda_orders_v5' && $RESET_T > 0 && is_array($d)) {
    $__f = array(); foreach ($d as $o) { if (is_array($o) && isset($o['_u']) && (float)$o['_u'] >= $RESET_T) $__f[] = $o; }
    $d = $__f;
  }
  // ghost guard: never let a client wipe orders/users with an empty array while server has data
  if (($k === 'paraveda_orders_v5' || $k === 'paraveda_users_v1' || $k === 'paraveda_villes_v2') && is_array($d) && count($d) === 0) {
    $cur = crm_read_raw();
    if (isset($cur[$k]['d']) && is_array($cur[$k]['d']) && count($cur[$k]['d']) > 0) {
      crm_audit("ghost | key=$k | empty write blocked");
      crm_out(array('ok'=>true, 'noop'=>'ghost'));
    }
  }

  $fh = @fopen($LOCK_FILE, 'c');
  if ($fh) @flock($fh, LOCK_EX);

  $data = crm_read_raw();
  $prevT = isset($data[$k]['t']) ? (int)$data[$k]['t'] : 0;

  if ($t < $prevT && $k !== 'paraveda_orders_v5') { // stale write from a tab that was offline (orders: merged instead)
    if ($fh) { @flock($fh, LOCK_UN); @fclose($fh); }
    crm_audit("stale | key=$k | t=$t < $prevT");
    crm_out(array('ok'=>true, 'noop'=>'stale', 't'=>$prevT));
  }
  $prevJson = isset($data[$k]['d']) ? json_encode($data[$k]['d'], JSON_UNESCAPED_UNICODE) : null;
  $newJson  = json_encode($d, JSON_UNESCAPED_UNICODE);
  if ($prevJson === $newJson) {          // nothing changed: touch time only, no backup churn
    $data[$k]['t'] = $t;
    crm_write($data);
    if ($fh) { @flock($fh, LOCK_UN); @fclose($fh); }
    crm_out(array('ok'=>true, 'noop'=>'same'));
  }

  crm_backup();
  // v3.45: orders are merged row-by-row (newest _u wins, rows never dropped) so
  // several agents/admins writing at the same time never erase each other.
  if ($k === 'paraveda_orders_v5' && is_array($d) && isset($data[$k]['d']) && is_array($data[$k]['d'])) {
    $d = crm_merge_orders($data[$k]['d'], $d, $RESET_T);
  }
  $data[$k] = array('t' => $t, 'd' => $d);
  $ok = crm_write($data);
  if ($fh) { @flock($fh, LOCK_UN); @fclose($fh); }

  if (!$ok) crm_out(array('ok'=>false, 'err'=>'write-failed'), 500);
  crm_audit("write | $k | t=$t | bytes=" . strlen($newJson));
  crm_out(array('ok'=>true));
}

http_response_code(405);
echo '{"ok":false,"err":"method-not-allowed"}';
exit;
