/* Simulation complète du scénario de l'utilisateur :
 *   - les fonctions de fusion sont EXTRAITES de public_html/index.html (code réellement livré)
 *   - le serveur applique la règle api.php v3.66
 *   - deux navigateurs A et B avec leur propre localStorage
 */
import fs from 'fs';

const html = fs.readFileSync(new URL('../public_html/index.html', import.meta.url), 'utf8');
function extractFn(name) {
  const i = html.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('introuvable: ' + name);
  let d = 0, started = false;
  for (let j = i; j < html.length; j++) {
    if (html[j] === '{') { d++; started = true; }
    else if (html[j] === '}') { d--; if (started && d === 0) return html.slice(i, j + 1); }
  }
  throw new Error('accolades: ' + name);
}
const __pvMergeRow = eval('(' + extractFn('__pvMergeRow') + ')');
const __pvMergeOrders = eval('(' + extractFn('__pvMergeOrders') + ')');

/* ---- localStorage : un par navigateur ---- */
function makeStorage() {
  const m = new Map();
  return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)),
           removeItem: k => m.delete(k), _dump: () => Object.fromEntries(m) };
}
let LS = makeStorage();
globalThis.localStorage = { getItem: k => LS.getItem(k), setItem: (k, v) => LS.setItem(k, v), removeItem: k => LS.removeItem(k) };

/* ---- serveur (règle api.php v3.66) ---- */
const server = { orders: [], t: 0 };
const serverWrite = (key, list, t) => {
  const byId = new Map(server.orders.map(o => [String(o.id), o]));
  for (const o of list) {
    const id = String(o.id);
    byId.set(id, byId.has(id) ? __pvMergeRow(byId.get(id), o) : o);
  }
  server.orders = [...byId.values()];
  server.t = t;
};

/* ---- navigateur ---- */
function browser(name) {
  const store = makeStorage();
  const KEY = 'paraveda_orders_v5', CT = 'ct_' + KEY;
  return {
    name, store,
    load() {                                   // ig()
      LS = store;
      const c = Number(store.getItem(CT) || 0);
      if (server.t > c) {
        const res = __pvMergeOrders(JSON.parse(JSON.stringify(server.orders)), c);
        store.setItem(KEY, JSON.stringify(res.list));
        store.setItem(CT, String(server.t));
      }
      return JSON.parse(store.getItem(KEY) || '[]');
    },
    edit(id, patch, now) {                     // upd()
      LS = store;
      const list = JSON.parse(store.getItem(KEY) || '[]');
      const i = list.findIndex(o => o.id === id);
      const __n = now;
      const __f = { ...(list[i]._f || {}) };
      Object.keys(patch).forEach(q => { if (String(list[i][q] ?? '') !== String(patch[q] ?? '')) __f[q] = __n; });
      list[i] = { ...list[i], ...patch, _u: __n, _f: __f };
      store.setItem(KEY, JSON.stringify(list));
      return list;
    },
    push(now) {                                // aa()  (+ correctif v3.66)
      LS = store;
      const list = JSON.parse(store.getItem(KEY) || '[]');
      serverWrite(KEY, JSON.parse(JSON.stringify(list)), now);
      store.removeItem(CT);                    // le cache local n'est plus considéré à jour
      setTimeout(() => {}, 0);
      this.load();                             // le poll (S4) réapplique le snapshot serveur
    }
  };
}

const T0 = 1789000000000, TA = 1789100000000, TB = 1789200000000, TC = 1789300000000;
server.orders = [{ id: 1, dateCreation: '2026-09-10', statut: '', livraison: '', nom: 'Zineb', ville: 'Casa', prix: 250, _u: T0 }];
server.t = T0;

let pass = 0, total = 0;
const chk = (n, ok, info = '') => { console.log(`  ${ok ? '✅' : '❌'} ${n}${info ? ' — ' + info : ''}`); total++; if (ok) pass++; };

const A = browser('A'), B = browser('B');
A.load(); B.load();                                     // les deux ouvrent le CRM
chk('les deux voient la commande du 10/09', A.load()[0].dateCreation === '2026-09-10' && B.load()[0].dateCreation === '2026-09-10');

A.edit(1, { dateCreation: '2026-08-01' }, TA);          // Admin A met la vraie date (mois dernier)
A.push(TA);
chk('serveur : date = 01/08/2026', server.orders[0].dateCreation === '2026-08-01', server.orders[0].dateCreation);

B.edit(1, { statut: 'Confirmé' }, TB);                  // Admin B (page restée ouverte) change le Statut
B.push(TB);
const srv = server.orders[0];
chk('serveur : la date de A est conservée', srv.dateCreation === '2026-08-01', 'date=' + srv.dateCreation);
chk('serveur : le Statut de B est enregistré', srv.statut === 'Confirmé', 'statut=' + srv.statut);

const bView = B.load().find(o => o.id === 1);           // B reçoit le snapshot serveur
chk('B voit la bonne date (plus celle de son vieux cache)', bView.dateCreation === '2026-08-01', 'B voit ' + bView.dateCreation);
chk("B voit son Statut", bView.statut === 'Confirmé', 'statut=' + bView.statut);

const aView = A.load().find(o => o.id === 1);           // A aussi
chk('A voit la date + le statut de B', aView.dateCreation === '2026-08-01' && aView.statut === 'Confirmé',
    aView.dateCreation + ' / ' + aView.statut);

// un 3e admin arrive après coup : il doit voir la bonne date
const C = browser('C');
const cView = C.load().find(o => o.id === 1);
chk('un nouvel admin voit la bonne date', cView.dateCreation === '2026-08-01', 'C voit ' + cView.dateCreation);

// A corrige encore la date plus tard : la modification la plus récente passe
A.load(); A.edit(1, { dateCreation: '2026-08-05' }, TC); A.push(TC);
chk('une correction plus récente passe quand même', server.orders[0].dateCreation === '2026-08-05', server.orders[0].dateCreation);

console.log(`\n${pass}/${total} cas OK`);
process.exit(pass === total ? 0 : 1);
