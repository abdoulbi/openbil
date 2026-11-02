# Contribuer

Créer une branche, installer `requirements.lock` puis `pip install --no-deps -e .` et exécuter `pytest -q`. Les tests ne doivent pas dépendre du réseau public. Utiliser une base PostgreSQL jetable pour `TEST_DATABASE_URL` ; ce test détruit les tables de la base cible.

Un nouveau connecteur doit documenter l’URL officielle, les droits, quotas et accès requis ; conserver données brutes et métadonnées ; valider dimensions/unités/statuts ; fournir fixtures, tests de pagination, erreurs et révisions ; démontrer une collecte réelle limitée et consigner ses échecs. Ne pas marquer `observed` par simple absence de flag.

Toute modification de schéma publié exige une migration numérotée. Toute transformation statistique exige une version et un test de reproductibilité. Une amélioration de prévision doit conserver un test final hors échantillon et comparer au naïf. Ne pas inclure de secrets, bases ou fichiers bruts dans un commit.

La CI teste Python et PostgreSQL. Publier une version ou des données reste une action séparée à approuver par le propriétaire du projet.
