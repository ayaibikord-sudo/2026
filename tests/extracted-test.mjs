/* Valide les fonctions RÉELLEMENT présentes dans public_html/index.html patché. */
import fs from 'fs';

const html = fs.readFileSync(new URL('../public_html/index.html', import.meta.url), 'utf8');

function extractFn(name) {
  const i = html.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('fonction introuvable: ' + name);
  let depth = 0, started = false;
  for (let j = i; j < html.length; j++) {
    const c = html[j];
    if (c === '{') { depth++; started = true; }
    else if (c === '}') { depth--; if (started && depth === 0) return html.slice(i, j + 1); }
  }
  throw new Error('accolades non équilibrées: ' + name);
}

const srcMerge = extractFn('__pvMergeRow');
const srcNorm = extractFn('__pvNormDate');
const fnMerge = eval('(' + srcMerge + ')');
const fnNorm = eval('(' + srcNorm + ')');

const serverWrite = (curList, inList, mergeFn) => {
  const byId = new Map(curList.filter(o => o && o.id != null).map(o => [String(o.id), o]));
  for (const o of inList) {
    if (!o || o.id == null) continue;
    const id = String(o.id);
    byId.set(id, byId.has(id) ? mergeFn(byId.get(id), o) : o);
  }
  return [...byId.values()];
};

const T0 = 1789000000000, TA = 1789100000000, TB = 1789200000000, TC = 1789300000000;
const baseRow = { id: 1, dateCreation: "2026-09-10", statut: "", livraison: "", nom: "Zineb", ville: "Casa", _u: T0 };
const clone = o => JSON.parse(JSON.stringify(o));

let pass = 0, total = 0;
const check = (name, ok, info) => { console.log(`  ${ok ? '✅' : '❌'} ${name}${info ? ' — ' + info : ''}`); total++; if (ok) pass++; };

console.log('=== __pvNormDate (formats de date) ===');
check('ISO conservé', fnNorm("2026-08-01") === "2026-08-01", fnNorm("2026-08-01"));
check('ISO datetime tronqué', fnNorm("2026-08-01T23:00:00.000Z") === "2026-08-01", fnNorm("2026-08-01T23:00:00.000Z"));
check('jj/mm/aaaa -> aaaa-mm-jj', fnNorm("01/08/2026") === "2026-08-01", fnNorm("01/08/2026"));
check('jj-mm-aaaa -> aaaa-mm-jj', fnNorm("01-08-2026") === "2026-08-01", fnNorm("01-08-2026"));
check('vide', fnNorm("") === "", JSON.stringify(fnNorm("")));
check('nul', fnNorm(null) === "", JSON.stringify(fnNorm(null)));

console.log('\n=== __pvMergeRow (extrait du fichier patché) ===');
{
  let s = serverWrite([clone(baseRow)], [{ ...baseRow, dateCreation: "2026-08-01", _u: TA, _f: { dateCreation: TA } }], fnMerge);
  s = serverWrite(s, [{ ...baseRow, statut: "Confirmé", _u: TB, _f: { statut: TB } }], fnMerge);
  const r = s.find(x => x.id === 1);
  check('1. date corrigée par A + statut par B (copie périmée)', r.dateCreation === "2026-08-01" && r.statut === "Confirmé", `date=${r.dateCreation} statut=${r.statut}`);
}
{
  const srv = [{ id: 1, dateCreation: "2026-08-01", statut: "", _u: TA, _f: { dateCreation: TA } }];
  const s = serverWrite(srv, [{ id: 1, dateCreation: "2026-09-14", statut: "Confirmé", _u: TB, _f: { statut: TB } }], fnMerge);
  const r = s.find(x => x.id === 1);
  check('2. copie périmée sans _f n\'écrase jamais la date', r.dateCreation === "2026-08-01" && r.statut === "Confirmé", `date=${r.dateCreation} statut=${r.statut}`);
}
{
  const m = fnMerge({ id: 1, dateCreation: "2026-08-01", statut: "", _u: TA, _f: { dateCreation: TA } },
                    { id: 1, dateCreation: "2026-09-10", statut: "", _u: T0 });
  check('3. navigateur B : snapshot serveur + cache local périmé', m.dateCreation === "2026-08-01", `date=${m.dateCreation}`);
}
{
  const s = serverWrite([{ id: 1, dateCreation: "2026-08-01", _u: TA, _f: { dateCreation: TA } }],
                        [{ id: 1, dateCreation: "2026-08-05", _u: TC, _f: { dateCreation: TC } }], fnMerge);
  check('4. modification plus récente (stampée) acceptée', s.find(x => x.id === 1).dateCreation === "2026-08-05", s.find(x => x.id === 1).dateCreation);
}
{
  const s = serverWrite([{ id: 2, nom: "A", _u: TA }], [{ id: 2, nom: "A", _del: 1, _u: TB }], fnMerge);
  check('5. suppression propagée', !!s.find(x => x.id === 2)._del);
}
{
  const s = serverWrite([{ id: 2, nom: "A", _del: 1, _u: TA }], [{ id: 2, nom: "A", statut: "Confirmé", _u: TB, _f: { statut: TB } }], fnMerge);
  check('6. ligne supprimée ne ressuscite pas', !!s.find(x => x.id === 2)._del);
}
{
  let s = serverWrite([{ id: 3, ville: "Rabat", _u: T0 }], [{ id: 3, ville: "", _u: TA, _f: { ville: TA } }], fnMerge);
  s = serverWrite(s, [{ id: 3, ville: "Rabat", statut: "Confirmé", _u: TB, _f: { statut: TB } }], fnMerge);
  const r = s.find(x => x.id === 3);
  check('7. vider un champ reste vide', r.ville === "" && r.statut === "Confirmé", `ville="${r.ville}" statut=${r.statut}`);
}
{
  let s = serverWrite([{ id: 4, _d: 1, _u: TA }], [{ id: 4, _d: 0, _u: TB, _f: { _d: TB } }], fnMerge);
  const r1 = s.find(x => x.id === 4);
  s = serverWrite(s, [{ id: 4, _d: 1, statut: "Confirmé", _u: TC, _f: { statut: TC } }], fnMerge);
  const r2 = s.find(x => x.id === 4);
  check('8. publication d\'un brouillon + pas de retour en arrière', String(r1._d) === "0" && String(r2._d) === "0", `_d=${r1._d} puis ${r2._d}`);
}
{
  const s = serverWrite([{ id: 5, nom: "A", _u: TA }], [{ id: 6, dateCreation: "2026-08-01", nom: "B", _u: TB }], fnMerge);
  const r = s.find(x => x.id === 6);
  check('9. nouvelle ligne ajoutée telle quelle', r && r.nom === "B" && r.dateCreation === "2026-08-01", JSON.stringify(r));
}

console.log(`\n${pass}/${total} cas OK`);
process.exit(pass === total ? 0 : 1);
