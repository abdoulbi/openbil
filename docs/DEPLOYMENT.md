# Hébergement de l’application complète

Le dépôt public contient le code uniquement ; les snapshots de validation privés ne sont pas inclus.

Architecture Railway prévue : PostgreSQL privé + deux services construits depuis le même Dockerfile.

| Service | Configuration |
|---|---|
| PostgreSQL | Service base de données, pas de domaine public nécessaire |
| Dashboard | `APP_ROLE=dashboard`, `DATABASE_URL` référencé depuis PostgreSQL, domaine HTTPS public |
| Collecteur | `APP_ROLE=collector`, même `DATABASE_URL`, aucun domaine public, volume persistant sur `/app/data` |

Le point d’entrée utilise le `PORT` du fournisseur, attend la base avec reprises bornées et applique les migrations avant de démarrer. Les URI `postgres://` et `postgresql://` sont normalisées vers le pilote psycopg installé. Les secrets restent dans les variables du fournisseur, jamais dans GitHub.

Le volume du collecteur doit être accessible en écriture à l’utilisateur `openbil` du conteneur (UID 1000). Vérifier ses permissions avant la première collecte. Sans volume, les réponses brutes seraient perdues à un redéploiement, ce qui compromettrait la reproductibilité.

Le dashboard reste vide jusqu’au premier commit d’un indicateur collecté. Vérifier le statut success de la collecte et le journal des services après déploiement. Le healthcheck HTTP du dashboard est `/_stcore/health` ; il vérifie le serveur HTTP, pas la qualité des données. La collecte quotidienne se poursuit dans le service collecteur, même sans visiteurs.

Le déploiement effectif nécessite une connexion au compte d’hébergement et la vérification du plan et des coûts avant tout engagement payant. Aucune disponibilité en ligne n’est affirmée par ce fichier de configuration.

Références officielles consultées le 2 novembre 2026 :
- https://railway.com/guides/docker-compose
- https://docs.railway.com/databases/postgresql
