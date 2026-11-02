# Rapport de validation — 2 novembre 2026

## Mise à jour après publication GitHub

Le dépôt public https://github.com/abdoulbi/openbil a été publié avec autorisation. La CI du commit `64720d4967e5548e9c9499356a577748c83d1a75` est **réussie : 38 tests, aucun ignoré**, avec service PostgreSQL 16. Le test `test_postgres_migration_collect_and_lock` a donc été exécuté : migrations répétées, collecte, idempotence et verrou concurrent validés.

Exécution : https://github.com/abdoulbi/openbil/actions/runs/41438559628 ; job `125254386856`. Résultat final pytest : `38 passed in 2.89s`. L’application complète chez l’hébergeur et le cycle réel de collecte sous PostgreSQL de production restent à vérifier. Les limitations « PostgreSQL non exécuté » ci-dessous décrivent uniquement la première livraison locale, avant cette CI.

Le code inclut désormais la normalisation des URI PostgreSQL des hébergeurs et un démarrage avec port configurable et attente bornée de la base. Les snapshots privés restent exclus du dépôt.

---

# Rapport initial de construction locale

## Résultat et périmètre réellement testé

MVP Banque mondiale testé avec des appels Internet réels et une base locale **SQLite**. Le code cible PostgreSQL et fournit son schéma, ses migrations, son verrouillage et un test CI dédié. **PostgreSQL et Docker n’ont pas été exécutés dans cet environnement.** Ne pas assimiler la compilation du SQL ou la validation YAML à un test d’exploitation PostgreSQL/Compose.

Environnement Python 3.12 ; versions exactes dans `requirements.lock`. Première collecte complète du 2026-11-02 11:18:10 environ à 11:19:17 UTC ; identifiant `14dc2d3f-8957-4fb7-8850-1b780c7d8e76`. Statut success, 11 datasets commités, zéro erreur de collecte finale. Période demandée 1960–2025, 17 pays.

| Mesure de la vue courante | Résultat |
|---|---:|
| Pays | 17 |
| Indicateurs | 11 |
| Séries pays × indicateur | 187 |
| Cellules annuelles attendues | 12 342 |
| Valeurs non manquantes | 9 736 |
| Valeurs manquantes | 2 606 |
| Couverture non manquante | 78,89 % |
| Valeurs avec alerte | 38 |
| Valeurs rejetées par les règles de domaine | 0 |
| Valeurs estimées identifiées | 1 190 |
| Valeurs de nature non établie (`unspecified`) | 8 546 |

La grille contient des NULL explicites ; 12 342 ne signifie donc pas 12 342 valeurs économiques disponibles. Aucune valeur n’a été imputée. Aucune observation source projetée n’a été rencontrée dans cet échantillon ; cela ne prouve pas que toutes les autres valeurs soient observées.

## Contrôles réels

- 33 réponses API (métadonnées et données paginées) pour la collecte initiale : HTTP 200, pagination complète.
- Essai additionnel sur PIB Burkina Faso, puis même requête répétée : seconde exécution `unchanged`, pas de nouvelles observations pour cette répétition.
- Après ces essais : 12 versions et 12 408 lignes historiques, mais toujours 12 342 cellules dans la vue courante. Le scope additionnel explique la version et les 66 lignes supplémentaires.
- Audit hors réseau : 35 références de fichiers bruts vérifiées, 12 digests sémantiques reproduits, 12 408 valeurs/lignes historiques comparées ; zéro erreur. Le comptage de 35 concerne les références de snapshots, pas les fichiers uniques du répertoire.
- Découverte WDI réelle : **1 498 entrées** récupérées sur deux pages ; catalogue privé conservé, aucun indicateur supplémentaire activé.
- Dashboard Streamlit : démarrage HTTP local 200 sur `/` et `/_stcore/health` ; chargement des données réelles et changements pays/indicateur sans exception via AppTest. Processus de vérification arrêté ensuite, aucune application hébergée.
- YAML Compose et services vérifiés, SQL PostgreSQL généré et testé par comparaison au schéma SQLAlchemy.

Les rapports détaillés sont `snapshot-audit.json`, `forecast-evaluation.json` et `access-probes.json`, dans `validation-privee/reports` du dossier de livraison. Les rapports de couverture et d’accès sont également conservés dans `docs/` ; les valeurs du backtest restent hors du dossier source. Les octets bruts et la base de démonstration sont livrés séparément du dossier de code, dans `validation-privee/data`. Les journaux de collectes réussies y sont conservés.

## Tests automatisés

Commande finale : `pytest -q` → **35 réussis, 1 ignoré**.

Couverture : enveloppe/API erreur 200, pagination incomplète et source changeante, HTTP 429 / 403, archivage brut, NULL/statuts, nombres non finis, valeurs négatives, doublons, mauvais pays, migrations répétées, idempotence, révisions/réversions, scopes chevauchants, rollback d’un dataset invalide, échec partiel et reprise, révision vers NULL, changement de définition, prévisions sans fuite du test, exclusion de projections, refus des trous et doublons, interface vide/chargée/filtres, cohérence du SQL PostgreSQL exporté.

Test ignoré : `test_postgres_migration_collect_and_lock`, car `TEST_DATABASE_URL` absent. Le workflow GitHub Actions fourni instancie PostgreSQL 16 pour ce test, mais **aucun workflow distant n’a été déclenché**. Lint Ruff (symboles et imports) : aucune erreur finale. Compilation Python : réussie.

## Prévisions sur les séries réelles

183 séries admissibles, 4 refusées. Modèles retenus à la validation : naïf 130, dérive 53. Dans 25 cas, le modèle sélectionné a une MAE de test supérieure au naïf ; ce constat reste visible et ne modifie pas rétroactivement la sélection. Il ne faut pas agréger les MAE de différentes unités en un score économique unique.

Séries refusées : exportations/importations Liberia (aucun historique admissible), exportations/importations Nigeria (dernier segment contigu trop court). Les résultats test concernent un horizon de trois années et le millésime courant, pas une prévision causale ou un test historique à millésimes constants.

## Accès aux autres sources

Les sept sondes HTTP sont revenues 200. Pour FMI, BAD, UNCTAD, FAOSTAT et ILOSTAT, il s’agit seulement d’une documentation ou d’un portail, pas d’un téléchargement validé de données. Pour Comtrade, la sonde concerne la liste des publications, pas les séries commerciales. Aucun accès authentifié, quota sous abonnement ou mapping statistique de ces six sources n’a été validé.

## Échecs rencontrés et résolution

1. Python système sans `requests` : sonde initiale non exécutée ; sonde HTTPS ensuite réussie via bibliothèque standard. Environnement dédié et dépendances installés pour l’application.
2. HTTPX sous proxy SOCKS sans `socksio` : premier essai de pipeline arrêté avant collecte ; dépendance `httpx[socks]` et `socksio` ajoutée, collecte complète réussie ensuite.
3. Fichier SQLite initial dans un répertoire inexistant : corrigé en créant `data`, procédure documentée.
4. PostgreSQL/Docker absents. Installation système PostgreSQL impossible (`setgroups/setegid/seteuid: Operation not permitted`). Aucun contournement ; test PostgreSQL laissé explicitement non exécuté.

## Conditions avant validation de production

Exécuter Compose et le test PostgreSQL sur une machine adaptée ; vérifier sauvegarde/restauration et droits SQL ; confirmer les conditions de chaque indicateur avant redistribution ; relire les alertes de source ; choisir un mécanisme d’authentification si le dashboard doit être exposé. La plateforme est un MVP local, pas une exploitation de production certifiée. Aucune publication GitHub, de données ni d’application n’a eu lieu.
