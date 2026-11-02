# Exploitation

## Migrations, actualisation, reprises

`openbil migrate` initialise la base et la version 001. `openbil collect` peut être lancé ponctuellement ; sortie non nulle en cas de collecte partielle ou échouée. `openbil schedule` exécute une collecte au démarrage, puis chaque jour à 03:00 UTC. Paramètres identiques à collect. APScheduler coalesce les retards, interdit les instances concurrentes et tolère une heure de retard ; le verrou PostgreSQL couvre plusieurs processus. Il ne rejoue pas toutes les dates manquées, car la collecte interroge tout l’historique et récupère aussi les révisions.

Le scheduler ne dépend pas d’une session ChatGPT. Il doit tourner sur la machine Docker de l’utilisateur. Aucun rappel ni tâche distante n’est créé. Les jobs échoués sont retentés à la prochaine exécution ; les datasets inchangés ne créent pas de nouvelles observations. Arrêter le collecteur pour maintenance avec `docker compose stop collector`.

Voir `docker compose logs collector` et les tables `collection_runs`, `quality_checks`. Surveiller absence de succès >48h, variation de couverture, nombre de rejets, erreurs d’accès et changement de métadonnées. Le dashboard indique les échecs récents. Alertes email/Slack non mises en place. La date « dernière collecte » des observations correspond à leur dernière version, pas au dernier contrôle inchangé : voir les runs pour la fraîcheur du contrôle.

## Sauvegardes et restauration

Sauvegarder PostgreSQL via `pg_dump` et le volume brut `raw` dans la même fenêtre (arrêter temporairement le collecteur). Tester régulièrement la restauration sur une instance isolée. Ne jamais supprimer les volumes pour « réparer » un échec de collecte. Les manifests conservent des chemins relatifs à la racine projet ; dans le dossier privé livré, les octets bruts correspondent aux mêmes SHA-256.

## Reproductibilité

`requirements.lock` contient les versions exactes utilisées lors des tests Python. Image PostgreSQL 16 ; image Python 3.12. Les tags Docker restent mutables : fixer leurs digests dans un environnement de production validé. Le fichier `scripts/audit_snapshot.py` vérifie les hashes des réponses et les compteurs sans retéléchargement. Le dépôt garde les transformations et la méthodologie ; les réponses brutes et versions SQL doivent être archivées séparément.

Les tests utilisent des fixtures synthétiques clairement confinées à `tests/`, jamais présentées comme données économiques. Le dashboard ne génère pas de données de démonstration en cas de panne.

## Sécurité et mise en production

Ne pas exposer PostgreSQL sur Internet ; Compose ne publie pas son port. Dashboard limité à localhost. Les rôles SQL minimaux, TLS, gestion de secrets, rétention, surveillance, sauvegardes hors machine et authentification du dashboard sont à configurer avant exposition multiutilisateur. Le MVP utilise un seul compte SQL pour simplifier le démarrage local, pas pour une exploitation sécurisée multiutilisateur.

Le dépôt exclut `.env`, bases, réponses brutes et exports. Aucun secret réel n’est fourni. Ne pas activer une publication GitHub, Streamlit Cloud ou autre hébergement sans accord explicite.

Le planificateur rafraîchit également le catalogue WDI à chaque passage et archive son manifeste. Un échec de découverte est journalisé sans bloquer les indicateurs déjà approuvés. Les nouveaux candidats ne sont activés qu’après revue des unités, définitions et droits.
