# Architecture et modèle de données

Flux : catalogue approuvé → API officielle → fichiers bruts immuables adressés par SHA-256 → validation → transaction SQL → vue courante → Streamlit / exports / prévisions.

| Table | Rôle |
|---|---|
| sources | Institution, URL, licence indicative, conditions et date de revue |
| datasets | Un dataset logique par indicateur WDI, attribution et note de droits |
| indicators | Code source, libellé, unité canonique, statut méthodologique connu |
| countries | ISO3 et région géographique |
| collection_runs | Paramètres, logiciel, dates, état success / partial / failed / running / interrupted |
| dataset_versions | Snapshot, scope, hash sémantique, manifeste brut, métadonnées, date de mise à jour source |
| observations | Pays, année, valeur nullable, unité, source/URL, publication, collecte, version, statut source et qualité, notes |
| quality_checks | Contrôles par exécution/version et compteurs ; erreurs et collectes inchangées |

`schema_migrations` est une table technique supplémentaire. Les huit tables métier ont des clés primaires ; les relations ont des clés étrangères. Les snapshots sont append-only par le code applicatif ; les droits SQL d’administration ne sont pas une barrière d’immutabilité cryptographique.

`current_observations` sélectionne la dernière version collectée de chaque pays/indicateur/année/source via `ROW_NUMBER`. Des scopes partiels n’effacent pas les autres pays. Une cellule devenue absente est explicitement conservée à NULL pour remplacer l’ancienne valeur. Les snapshots inchangés consécutifs pour le même scope ne sont pas dupliqués, mais la vérification et son manifeste sont consignés. Une réversion du fournisseur est conservée comme une nouvelle version.

Le hash sémantique couvre les lignes normalisées, les métadonnées et la date de mise à jour du dataset. Le manifeste brut lie chaque réponse à son URL, sa date et son SHA-256. La version logicielle est enregistrée ; `requirements.lock` fixe l’environnement Python testé. La séparation entre hash des octets et hash sémantique évite de confondre format HTTP et contenu statistique.

## Transactions et concurrence

PostgreSQL utilise un verrou consultatif de session global pour la collecte et un verrou transactionnel pour les migrations. Les appels HTTP ont lieu hors transaction longue. Chaque indicateur valide est validé atomiquement en base ; une erreur est journalisée séparément. Au redémarrage, les jobs `running` orphelins sont marqués `interrupted` après acquisition du verrou. Un second collecteur ne démarre pas. SQLite est réservé au développement séquentiel.

Une panne entre l’écriture brute et le commit peut laisser des fichiers orphelins, sans corrompre les snapshots SQL. Sauvegarder les fichiers bruts et la base ensemble. Les volumes et migrations ne remplacent pas une politique de sauvegarde.

## Extensibilité

Pour une autre source, implémenter un adaptateur avec normalisation de ses dimensions, statuts, calendriers, unités et licences. Ne pas fusionner directement WDI et FMI sous un même code : les définitions et millésimes doivent être identifiés. Le schéma MVP annuel ne gère pas encore les données mensuelles, partenaires commerciaux, produits HS, sexe/âge ou niveaux infranationaux. Une migration dédiée sera nécessaire avant Comtrade/ILOSTAT complets.

Le SQL `migrations/001_initial.sql` est généré par `scripts/export_schema.py`. Il sert de schéma initial inspectable pour PostgreSQL ; le CLI `openbil migrate` assure l’idempotence. Les futures évolutions doivent ajouter une migration numérotée et préserver l’historique, pas seulement modifier les modèles.
