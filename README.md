# Open Business Intelligence Lab — OpenBIL 0.2.0

MVP de collecte économique auditable pour l’Afrique. Code MIT, données soumises aux licences de leurs producteurs. Publication du code autorisée par le propriétaire ; aucun secret ni snapshot privé dans le dépôt.

## Ce qui fonctionne

- Connecteur officiel **World Bank Indicators API v2 / WDI source 2**, pagination complète, catalogue découvrable, archivage des réponses brutes SHA-256, métadonnées par version.
- **17 pays, 11 indicateurs**, de 1960 à la dernière année civile complète par défaut. Les valeurs indisponibles restent NULL. Les 16 États d’Afrique de l’Ouest sont inclus, plus le Kenya ; périmètre géographique, pas appartenance à la CEDEAO.
- PostgreSQL : les huit tables métier demandées, migrations versionnées, clés étrangères, contraintes, vue courante ; conservation des révisions, transactions par indicateur, verrou de collecte interprocessus.
- Planificateur quotidien à **03:00 UTC / Ouagadougou**, collecte au démarrage, reprise des erreurs à la prochaine exécution et reprises HTTP bornées. Un échec partiel ne détruit pas les versions précédentes.
- Streamlit : filtres, comparaison sur la même année, séries, couverture, provenance, exécutions, exports et analyses séparant faits / interprétations / hypothèses / recommandations.
- Prévisions naïves ou à dérive, sélection chronologique puis test final hors échantillon ; pas d’imputation, pas de mélange avec les observations.

**Limites de livraison :** PostgreSQL et Docker ne pouvaient pas tourner dans l’environnement de construction. Les tests locaux utilisent SQLite pour valider la logique ; un test PostgreSQL dédié est fourni pour CI/Docker, mais son succès n’est pas présumé. Voir [rapport de validation](docs/VALIDATION.md). Les six autres institutions sont une feuille de route documentée, pas des connecteurs opérationnels.

## Démarrage recommandé avec PostgreSQL

Prérequis : Docker Engine/Desktop avec Compose v2. Depuis ce dossier :

```bash
cp .env.example .env
# Modifier POSTGRES_PASSWORD : mot de passe aléatoire, sans caractères réservés d’URL.
docker compose up --build -d
docker compose logs -f collector
```

Ouvrir **http://localhost:8501**. Le dashboard est lié uniquement à l’interface locale. Attendre la première collecte (environ 33 requêtes pour le périmètre actuel). Les volumes `postgres` et `raw` persistent entre redémarrages. `docker compose down` les conserve ; **ne pas utiliser `down -v`** pour un arrêt normal.

Relancer une collecte ou limiter son périmètre :

```bash
docker compose run --rm collector openbil collect --countries BFA KEN GHA --indicators NY.GDP.MKTP.CD FP.CPI.TOTL.ZG --start 1960 --end 2025
```

Une collecte active bloque la seconde via verrou PostgreSQL ; le tableau de bord reste consultable. Le scheduler reprend l’ensemble du périmètre à sa prochaine exécution. Les filtres du dashboard ne modifient pas les jobs.

## Exécution Python

```bash
python -m venv .venv
# Linux/macOS : source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements.lock
pip install --no-deps -e .
# Définir DATABASE_URL vers votre PostgreSQL existant :
# postgresql+psycopg://utilisateur:motdepasse@localhost:5432/openbil
openbil migrate
openbil collect
streamlit run app.py
```

Pour un essai local **sans PostgreSQL**, SQLite est un mode de démonstration et de tests, sans garantie de concurrence :

```bash
mkdir -p data
export DATABASE_URL=sqlite:///data/openbil.sqlite
openbil migrate
openbil collect
streamlit run app.py
```

Sous PowerShell : `$env:DATABASE_URL="sqlite:///data/openbil.sqlite"` ; créer `data` avec `New-Item -ItemType Directory -Force data`. Toujours lancer les commandes depuis la racine du projet.

## Découverte et tests

```bash
openbil discover --output data/catalog/worldbank.json
pytest -q
python scripts/probe_sources.py
```

La découverte interroge uniquement le catalogue officiel WDI. Elle ne fait pas de scraping et n’active pas automatiquement un nouvel indicateur : ajouter un code à `catalog.py` après vérification de l’unité, de la définition et des droits.

Pour le test PostgreSQL, définir `TEST_DATABASE_URL` vers une base **jetable** : le test y supprime les tables OpenBIL. La CI fournie crée une base dédiée. Les tests ordinaires sont hors réseau ; les tests réels sont consignés dans `docs/VALIDATION.md`.

## Organisation

```
src/openbil/  catalogue, base, connecteur, qualité, pipeline, prévisions, analyse, CLI
migrations/  schéma PostgreSQL 001 exporté
app.py       dashboard Streamlit
scripts/     contrôles d’accès, export du schéma, audit local
 tests/      tests unitaires, intégration, interface et PostgreSQL
 docs/       architecture, méthodologie, sources, validation, exploitation
```

## Publication et hébergement

Dépôt public : https://github.com/abdoulbi/openbil. Voir [déploiement](docs/DEPLOYMENT.md) pour héberger PostgreSQL, le collecteur et Streamlit. Les réponses brutes, bases, exports, `.env` et secrets ne sont pas versionnés. Avant toute publication : exécuter les tests PostgreSQL/Compose, revoir les licences par indicateur si des données doivent être redistribuées, puis obtenir l’approbation explicite du propriétaire. La licence MIT ne s’applique **qu’au code**.

## Attribution

The World Bank: World Development Indicators: fournisseurs originaux dans `metadata_json.sourceOrganization`. Les URLs exactes, dates de collecte et empreintes sont conservées. Voir [sources](docs/SOURCES.md), [méthodologie](docs/METHODOLOGY.md), [architecture](docs/ARCHITECTURE.md) et [exploitation](docs/OPERATIONS.md).

Ce projet reprend l’intention et la licence MIT du starter OpenBIL fourni, mais remplace son accès direct et ses projections non évaluées par un pipeline persistant et testé. Aucune affiliation ou approbation des fournisseurs n’est revendiquée.

Le planificateur rafraîchit également le catalogue WDI à chaque passage et archive son manifeste. Un échec de découverte est journalisé sans bloquer les indicateurs déjà approuvés. Les nouveaux candidats ne sont activés qu’après revue des unités, définitions et droits.
