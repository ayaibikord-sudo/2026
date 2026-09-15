#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Applique le correctif v3.66 sur public_html/index.html"""
import sys, io, re

P = 'public_html/index.html'
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

# ---------------------------------------------------------------- 1. __pvNormDate
rep(
 'function __pvLocalDate(d){const p=n=>String(n).padStart(2,"0");return d.getFullYear()+"-"+p(d.getMonth()+1)+"-"+p(d.getDate())}',
 'function __pvLocalDate(d){const p=n=>String(n).padStart(2,"0");return d.getFullYear()+"-"+p(d.getMonth()+1)+"-"+p(d.getDate())}'
 'function __pvNormDate(v){let s=String(v??"").trim();if(!s)return"";let m=s.match(/^(\\d{4})[-\\/.](\\d{1,2})[-\\/.](\\d{1,2})/);'
 'if(m)return m[1]+"-"+String(m[2]).padStart(2,"0")+"-"+String(m[3]).padStart(2,"0");'
 'm=s.match(/^(\\d{1,2})[-\\/.](\\d{1,2})[-\\/.](\\d{4})$/);'
 'if(m){const dd=Number(m[1]),mm=Number(m[2]),yy=Number(m[3]);'
 'if(mm>=1&&mm<=12&&dd>=1&&dd<=31)return yy+"-"+String(mm).padStart(2,"0")+"-"+String(dd).padStart(2,"0")}'
 'const t=Date.parse(s);if(!isNaN(t))return __pvLocalDate(new Date(t));return s.slice(0,10)}',
 '1. helper __pvNormDate')

# ---------------------------------------------------------------- 2. nettoyage des dates dans F4
rep('dateCreation:String(i.dateCreation??"").slice(0,10),dateConfirmation:String(i.dateConfirmation??"").slice(0,10)',
    'dateCreation:__pvNormDate(i.dateCreation),dateConfirmation:__pvNormDate(i.dateConfirmation)',
    '2a. F4 normalise dateCreation/dateConfirmation')
rep('dateExp:String(i.dateExp??"").slice(0,10),dateLiv:String(i.dateLiv??"").slice(0,10)',
    'dateExp:__pvNormDate(i.dateExp),dateLiv:__pvNormDate(i.dateLiv)',
    '2b. F4 normalise dateExp/dateLiv')

# ---------------------------------------------------------------- 3. nouvelle fusion (__pvMergeRow)
OLD_MERGE = ('function __pvMergeRow(a,b){const ua=Number(a._u)||0,ub=Number(b._u)||0;let base=ub>ua?b:a,oth=ub>ua?a:b;'
             'if(base._del||oth._del)return ub>ua?b:a;const bf=base._f||{},of=oth._f||{};let out=base,ch=!1;'
             'Object.keys(of).forEach(k=>{const to=Number(of[k])||0,tb=Number(bf[k])||0;'
             'if(to>tb&&k in oth&&String(oth[k]??"")!==String(base[k]??"")){ch||(out={...base,_f:{...bf}},ch=!0);'
             'out[k]=oth[k];out._f[k]=to}});return out}')
NEW_MERGE = ('function __pvMergeRow(a,b){const ua=Number(a._u)||0,ub=Number(b._u)||0;'
 'if(a._del)return{...a,_u:Math.max(ua,ub)};'
 'if(b._del)return{...b,_u:Math.max(ua,ub)};'
 'const sf=(a._f&&typeof a._f==="object")?a._f:{},bf=(b._f&&typeof b._f==="object")?b._f:{};'
 'let out={...a},nf=null;const setF=(k,v)=>{nf||(nf={...sf});nf[k]=v};'
 'const keys=[],seen={};[a,b].forEach(o=>{Object.keys(o).forEach(k=>{if(!seen[k]){seen[k]=1;keys.push(k)}})});'
 'for(const k of keys){'
 'if(k==="id"||k==="_u"||k==="_f"||k==="_del")continue;'
 'const sv=a[k],iv=b[k],st=Number(sf[k])||0,it=Number(bf[k])||0;'
 'if(String(sv??"")===String(iv??"")){if(it>st)setF(k,it);continue}'
 'if(k==="_d"){if(String(iv??"")==="1"){if(it>st){out[k]=iv;setF(k,it)}}else if(ub>ua)out[k]=iv;continue}'
 'if(!(k in a)){out[k]=iv;if(it>st)setF(k,it);continue}'
 'if(it>st){out[k]=iv;setF(k,it);continue}'
 '}'
 'out._u=Math.max(ua,ub);if(nf)out._f=nf;return out}')
rep(OLD_MERGE, NEW_MERGE, '3. __pvMergeRow protegee')

# ---------------------------------------------------------------- 4. colonne date dans l'import Excel
rep('const E2=[{key:"agent"',
    'const E2=[{key:"dateCreation",label:"📅 التاريخ (Date)",hint:/^\\W*(date|dates|تاريخ|اليوم|jour)\\W*$/i},{key:"dateConfirmation",label:"📅 تاريخ التأكيد",hint:/confirm|تاكيد|تأكيد/i},{key:"agent"',
    '4. mapping colonne DATE (import Excel)')

# ---------------------------------------------------------------- 5. import Excel : ne plus forcer la date du jour
rep('return{dateCreation:__pvLocalDate(new Date()),dateConfirmation:__pvLocalDate(new Date()),statut:""',
    'const DC=__pvNormDate(E(C,"dateCreation"))||__pvLocalDate(new Date());return{dateCreation:DC,dateConfirmation:__pvNormDate(E(C,"dateConfirmation"))||DC,statut:""',
    '5. import Excel garde la date du fichier')

# ---------------------------------------------------------------- 6. remplissage (fill) : source vide interdite
rep('Pe=[];const __n=se.toIdx-se.fromIdx+1;if((__n>3||Ce)&&!confirm(',
    'Pe=[];const __n=se.toIdx-se.fromIdx+1;if(Ce&&!Le){Sa("⚠️ خانة التاريخ فارغة — التعبئة تّلغات");return}if((__n>3||Ce)&&!confirm(',
    '6. fill: pas de remplissage depuis une date vide')

# ---------------------------------------------------------------- 7. publier un brouillon -> stamp
rep('i(D=>D.map(T=>S.has(T.id)&&T._d?{...T,_d:0,_u:now}:T))',
    'i(D=>D.map(T=>S.has(T.id)&&T._d?{...T,_d:0,_u:now,_f:{...(T._f||{}),_d:now}}:T))',
    '7. publish stamp _f._d')

# ---------------------------------------------------------------- 8. renommer / retirer une fille -> stamp
rep('i(T=>T.map(k=>k.agent.toLowerCase()===v.toLowerCase()?{...k,agent:D}:k))',
    'i(T=>T.map(k=>k.agent.toLowerCase()===v.toLowerCase()?{...k,agent:D,_u:Date.now(),_f:{...(k._f||{}),agent:Date.now()}}:k))',
    '8a. renameAgent stamp')
rep('i(A=>A.map(D=>D.agent.toLowerCase()===v.toLowerCase()?{...D,agent:""}:D))',
    'i(A=>A.map(D=>D.agent.toLowerCase()===v.toLowerCase()?{...D,agent:"",_u:Date.now(),_f:{...(D._f||{}),agent:Date.now()}}:D))',
    '8b. removeAgent stamp')

# ---------------------------------------------------------------- 9. handshake de version (vieux caches)
rep('async function S4(){try{const e=await fetch("api.php",{cache:"no-store",headers:{"X-Sync-Token":Rd}});'
    'if(!e.ok)throw new Error("http "+e.status);const n=await e.json();'
    'if(!n||typeof n!="object"||Array.isArray(n))throw new Error("shape");',
    'const __PV_V="3.66";function __pvCheckVer(v){if(!v||v===__PV_V)return;'
    'try{const k="paraveda_ver_bust",last=Number(sessionStorage.getItem(k)||0);'
    'if(Date.now()-last>36e5){sessionStorage.setItem(k,String(Date.now()));'
    'const u=new URL(location.href);u.searchParams.set("pv",String(Date.now()));location.replace(u.toString());return}}catch{}'
    'try{if(!document.getElementById("pv-oldver")){const b=document.createElement("div");b.id="pv-oldver";'
    'b.style.cssText="position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#b91c1c;color:#fff;'
    'font:700 13px/1.4 system-ui,sans-serif;padding:10px;text-align:center;direction:rtl";'
    'b.textContent="⚠️ نسخة قديمة ديال التطبيق — دير Ctrl+F5 باش تاخد النسخة الجديدة (v"+String(v)+"). حتى ديرها ما يمكنش تبدل التواريخ.";'
    'document.body.appendChild(b)}}catch{}}'
    'async function S4(){try{const e=await fetch("api.php",{cache:"no-store",headers:{"X-Sync-Token":Rd}});'
    'if(!e.ok)throw new Error("http "+e.status);const n=await e.json();'
    'if(!n||typeof n!="object"||Array.isArray(n))throw new Error("shape");try{__pvCheckVer(n._v)}catch{}',
    '9. handshake de version')

# ---------------------------------------------------------------- 10. badge de version
rep('children:"v3.65"', 'children:"v3.66"', '10. badge v3.66')

if s == orig:
    print('!! aucun changement')
    sys.exit(1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\nindex.html patché (%d -> %d octets)' % (len(orig), len(s)))
