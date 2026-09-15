/* Test harness for the v3.66 merge rule.
 *
 * Rule (a = server/reference row, b = incoming row from a browser):
 *   - a field already stored is NEVER replaced unless the incoming row carries
 *     an explicit, strictly NEWER per-field stamp (_f[field]).
 *   - tombstones (_del) and the draft flag (_d) have their own rules.
 *
 * The same function is used by index.html (merge server snapshot + local cache)
 * and by api.php (merge incoming browser write + stored data).
 */
const clone = o => JSON.parse(JSON.stringify(o));

/* ---------- v3.65 (shipped today) ---------- */
function oldMergeRow(a, b) {
  const ua = Number(a._u) || 0, ub = Number(b._u) || 0;
  let base = ub > ua ? b : a, oth = ub > ua ? a : b;
  if (base._del || oth._del) return ub > ua ? b : a;
  const bf = base._f || {}, of = oth._f || {};
  let out = base, ch = false;
  Object.keys(of).forEach(k => {
    const to = Number(of[k]) || 0, tb = Number(bf[k]) || 0;
    if (to > tb && k in oth && String(oth[k] ?? "") !== String(base[k] ?? "")) {
      if (!ch) { out = { ...base, _f: { ...bf } }; ch = true; }
      out[k] = oth[k]; out._f[k] = to;
    }
  });
  return out;
}

/* ---------- v3.66 (new) ---------- */
function newMergeRow(a, b) {
  const ua = Number(a._u) || 0, ub = Number(b._u) || 0;
  if (a._del) return { ...a, _u: Math.max(ua, ub) };   // tomb already there: never resurrect
  if (b._del) return { ...b, _u: Math.max(ua, ub) };   // delete request
  const sf = (a._f && typeof a._f === "object") ? a._f : {};
  const bf = (b._f && typeof b._f === "object") ? b._f : {};
  let out = { ...a }, nf = null;
  const setF = (k, v) => { if (!nf) nf = { ...sf }; nf[k] = v; };
  const keys = [], seen = {};
  [a, b].forEach(o => Object.keys(o).forEach(k => { if (!seen[k]) { seen[k] = 1; keys.push(k); } }));
  for (const k of keys) {
    if (k === "id" || k === "_u" || k === "_f" || k === "_del") continue;
    const sv = a[k], iv = b[k];
    const st = Number(sf[k]) || 0, it = Number(bf[k]) || 0;
    if (String(sv ?? "") === String(iv ?? "")) { if (it > st) setF(k, it); continue; }
    if (k === "_d") {                                   // draft / published flag
      if (String(iv ?? "") === "1") { if (it > st) { out[k] = iv; setF(k, it); } }
      else if (ub > ua) out[k] = iv;
      continue;
    }
    if (!(k in a)) { out[k] = iv; if (it > st) setF(k, it); continue; }  // brand new field
    if (it > st) { out[k] = iv; setF(k, it); continue; }                 // explicit newer edit
    // otherwise: the stored value is protected — a stale copy can never overwrite it
  }
  out._u = Math.max(ua, ub);
  if (nf) out._f = nf;
  return out;
}

/* server write: merge an incoming array into the stored array */
function serverWrite(curList, inList, mergeFn) {
  const byId = new Map(curList.filter(o => o && o.id != null).map(o => [String(o.id), o]));
  for (const o of inList) {
    if (!o || o.id == null) continue;
    const id = String(o.id);
    byId.set(id, byId.has(id) ? mergeFn(byId.get(id), o) : o);
  }
  return [...byId.values()];
}

const T0 = 1789000000000, TA = 1789100000000, TB = 1789200000000, TC = 1789300000000;
const baseRow = { id: 1, dateCreation: "2026-09-10", statut: "", livraison: "", nom: "Zineb", ville: "Casa", _u: T0 };

const cases = [];
const t = (name, fn) => cases.push({ name, fn });

t("1. admin A corrige la date -> admin B (copie perimee) modifie le Statut", fn => {
  let s = serverWrite([clone(baseRow)], [{ ...baseRow, dateCreation: "2026-08-01", _u: TA, _f: { dateCreation: TA } }], fn);
  s = serverWrite(s, [{ ...baseRow, statut: "Confirmé", _u: TB, _f: { statut: TB } }], fn);
  const r = s.find(x => x.id === 1);
  return [r.dateCreation === "2026-08-01" && r.statut === "Confirmé", `date=${r.dateCreation} statut=${r.statut || "(vide)"}`];
});

t("2. copie perimee (sans _f) n'ecrase jamais une date deja en place", fn => {
  const srv = [{ id: 1, dateCreation: "2026-08-01", statut: "", _u: TA, _f: { dateCreation: TA } }];
  const s = serverWrite(srv, [{ id: 1, dateCreation: "2026-09-10", statut: "Confirmé", _u: TB, _f: { statut: TB } }], fn);
  const r = s.find(x => x.id === 1);
  return [r.dateCreation === "2026-08-01" && r.statut === "Confirmé", `date=${r.dateCreation} statut=${r.statut || "(vide)"}`];
});

t("3. navigateur de B: fusion (snapshot serveur + cache local perime)", fn => {
  const m = fn(
    { id: 1, dateCreation: "2026-08-01", statut: "", _u: TA, _f: { dateCreation: TA } },
    { id: 1, dateCreation: "2026-09-10", statut: "", _u: T0 }
  );
  return [m.dateCreation === "2026-08-01", `date affichee=${m.dateCreation}`];
});

t("4. une modification plus recente (stampee) passe quand meme", fn => {
  let s = serverWrite([{ id: 1, dateCreation: "2026-08-01", _u: TA, _f: { dateCreation: TA } }],
    [{ id: 1, dateCreation: "2026-08-05", _u: TC, _f: { dateCreation: TC } }], fn);
  const r = s.find(x => x.id === 1);
  return [r.dateCreation === "2026-08-05", `date=${r.dateCreation}`];
});

t("5. suppression (tombstone) se propage", fn => {
  const s = serverWrite([{ id: 2, nom: "A", _u: TA }], [{ id: 2, nom: "A", _del: 1, _u: TB }], fn);
  const r = s.find(x => x.id === 2);
  return [!!r._del, `_del=${!!r._del}`];
});

t("6. une ligne supprimee ne ressuscite pas", fn => {
  const s = serverWrite([{ id: 2, nom: "A", _del: 1, _u: TA }], [{ id: 2, nom: "A", statut: "Confirmé", _u: TB, _f: { statut: TB } }], fn);
  const r = s.find(x => x.id === 2);
  return [!!r._del, `_del=${!!r._del}`];
});

t("7. vider un champ volontairement reste vide", fn => {
  let s = serverWrite([{ id: 3, ville: "Rabat", _u: T0 }], [{ id: 3, ville: "", _u: TA, _f: { ville: TA } }], fn);
  s = serverWrite(s, [{ id: 3, ville: "Rabat", statut: "Confirmé", _u: TB, _f: { statut: TB } }], fn);
  const r = s.find(x => x.id === 3);
  return [r.ville === "" && r.statut === "Confirmé", `ville="${r.ville}" statut=${r.statut || "(vide)"}`];
});

t("8. publier un brouillon (_d:0) passe, et un brouillon perime ne revient pas", fn => {
  let s = serverWrite([{ id: 4, _d: 1, _u: TA }], [{ id: 4, _d: 0, _u: TB, _f: { _d: TB } }], fn);
  const r1 = s.find(x => x.id === 4);
  s = serverWrite(s, [{ id: 4, _d: 1, statut: "Confirmé", _u: TC, _f: { statut: TC } }], fn);
  const r2 = s.find(x => x.id === 4);
  return [String(r1._d) === "0" && String(r2._d) === "0", `apres publication _d=${r1._d} puis _d=${r2._d}`];
});

t("9. une nouvelle ligne est ajoutee telle quelle", fn => {
  const s = serverWrite([{ id: 5, nom: "A", _u: TA }], [{ id: 6, dateCreation: "2026-08-01", nom: "B", _u: TB }], fn);
  const r = s.find(x => x.id === 6);
  return [r && r.nom === "B" && r.dateCreation === "2026-08-01", `ligne 6 = ${JSON.stringify(r)}`];
});

let pass = 0, total = 0;
for (const [label, fn] of [["v3.65 (actuel)", oldMergeRow], ["v3.66 (nouveau)", newMergeRow]]) {
  console.log(`\n=== ${label} ===`);
  for (const c of cases) {
    const [ok, info] = c.fn(fn);
    console.log(`  ${ok ? "✅" : "❌"} ${c.name} — ${info}`);
    total++; if (ok) pass++;
  }
}
console.log(`\n${pass}/${total} cas OK`);
process.exit(pass === total ? 0 : 1);
