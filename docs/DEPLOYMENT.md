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

## Alternative Render

À la suite du blocage d’inscription Railway signalé par le propriétaire, le fichier `render.yaml` prépare une alternative complète : service web Streamlit, worker de collecte et PostgreSQL 16. Le runtime Python natif évite de dépendre des permissions d’un volume Docker ; les fichiers bruts et le catalogue résident sur le disque du worker, monté à `/opt/render/project/src/data`. La connexion PostgreSQL est injectée par Render et l’accès externe à la base est désactivé (`ipAllowList: []`).

**Statut : configuration préparée, pas de déploiement réalisé.** Il faut connecter le compte Render et examiner son estimation avant d’appliquer le Blueprint : les deux services `starter`, le stockage persistant et la base `basic-256mb` sont payants. Aucune ressource payante n’a été créée. Ces noms de plans historiques restent documentés par Render ; vérifier les équivalents et tarifs présentés à l’activation.

La base gratuite Render expire après 30 jours et ne convient pas à une base autonome durable. Ne pas remplacer la configuration persistante par un disque éphémère sans accepter la perte des archives à chaque redéploiement.

Après activation : attendre le succès de la première collecte, vérifier les alertes du dashboard, l’accès HTTPS et les sauvegardes. La validation YAML locale ne vaut pas validation serveur Render ni test de déploiement.

Références : https://render.com/docs/blueprint-spec ; https://render.com/docs/disks ; https://render.com/docs/free ; https://render.com/docs/compute-plans (consultées le 2 novembre 2026).

## Mode gratuit retenu

Le propriétaire a choisi l’hébergement gratuit. `render.yaml` remplace désormais le Blueprint payant par **un seul service web `plan: free`** ; il ne déclare aucune base Render, aucun disque ni worker payants. Lancer `app_free.py`, qui conserve l’interface et les modèles du projet.

Le cache SQLite et les réponses brutes sont temporaires. La première visite reconstruit la base depuis WDI ; les visites suivantes relancent la collecte si la dernière réussite a plus de 24 heures. Les échecs sont retentés au plus une fois par heure. Un verrou local sérialise les collectes au sein de l’instance. Le service gratuit se met en veille sans visiteurs : ce mode ne garantit ni actualisation quotidienne sans visite, ni historique de révisions durable. Les exports restent disponibles avant une éventuelle perte du cache.

PostgreSQL, ses migrations et le collecteur permanent restent disponibles avec Docker Compose pour une installation autonome. Le code OpenBIL, Streamlit et SQLite sont open source ; Render est le fournisseur d’hébergement et n’est pas présenté comme un logiciel open source.

Aucune carte, souscription payante ni base PostgreSQL temporaire de 30 jours n’est requise par cette configuration. Si Render exige malgré tout une vérification de compte pour le service gratuit, ne pas passer à un plan payant automatiquement.
