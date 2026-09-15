# Paraveda / SAS CRM

Application CRM (PHP + React bundle statique) déployée sur un hébergement mutualisé.

## Arborescence

```
public_html/
  index.html      application (bundle React, v3.66)
  api.php         API de synchronisation (lecture/écriture de crm_data.json)
  import.php      page d'import localStorage
  INSTALL.txt     journal des versions (arabe marocain)
  crm_data.json   données (utilisé si ../crm-paraveda-data n'existe pas)
crm-paraveda-data/
  crm_data.json   données hors web root (prioritaire si le dossier est accessible en écriture)
tests/            scénarios de synchronisation (node + python) — non déployés
tools/            scripts de patch utilisés pour produire la v3.66 — non déployés
paraveda-crm-v3.65.zip   archive d'origine
paraveda-crm-v3.66.zip   archive à déployer
```

## v3.66 — les modifications ne se perdent plus

Règle de fusion stricte, appliquée **côté client (`__pvMergeRow`) et côté serveur
(`crm_merge_row`)** : une valeur déjà enregistrée n'est remplacée que par une
modification **explicite et plus récente** (tampon par champ `_f[champ]`
strictement supérieur). Une copie périmée (ancien cache navigateur) ne peut plus
écraser une date, un prix, un statut… même si son `_u` est plus récent.

Détails dans `public_html/INSTALL.txt` (section v3.66).

## Tests

```bash
node tests/sync-sim.mjs        # scénario complet 2 admins + serveur (9 cas)
node tests/extracted-test.mjs  # fonctions extraites de index.html (15 cas)
python3 tests/php_merge_test.py# logique api.php (14 cas)
node tests/merge-test.mjs      # comparaison ancienne/nouvelle règle
```
