# Sources, accès et feuille de route

Vérification documentaire : 2 novembre 2026. Les documents officiels font autorité ; les limites et conditions peuvent changer. Les essais HTTP réels sont consignés dans `access-probes.json`, avec distinction entre API, documentation et portail. Un portail HTTP 200 ne prouve pas l’accès aux données.

## Banque mondiale — intégré

- Documentation : https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
- Structure des appels : https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures
- Métadonnées indicateurs : https://datahelpdesk.worldbank.org/knowledgebase/articles/898599-indicator-api-queries
- Notes et statut F : https://datahelpdesk.worldbank.org/knowledgebase/articles/1886674-new-features-and-enhancements-in-the-v2-api
- Conditions : https://www.worldbank.org/ext/en/legal/terms-conditions/datasets
- Licences : https://datacatalog.worldbank.org/public-licenses

WDI source 2, HTTPS, JSON, pagination, `footnote=y`, `scale=n`. Aucun token requis pour les appels effectués. Attribution : **The World Bank: World Development Indicators: original data provider where known**. Inclure URL de source, date d’accès, indicateur, années, version et transformations dans une étude. Les versions conservent l’organisme original dans les métadonnées.

CC BY 4.0 est le régime par défaut assorti des conditions Banque mondiale ; certaines données tierces ont des exceptions. Le pipeline collecte à usage privé et conserve les métadonnées ; il ne prétend pas que tous les indicateurs peuvent être redistribués sans revue. MIT ne relicencie pas les données. Les exports affichent les conditions ; leur publication exige une revue des droits.

Quota numérique WDI non établi par les documents consultés. Politique locale prudente : appels séquentiels, intervalle 1 seconde, 1 000 lignes/page, quatre tentatives maximum, backoff exponentiel et respect de Retry-After jusqu’à 300 secondes. Si Retry-After demande davantage, interrompre cette collecte et attendre le prochain job. Aucun contournement d’authentification, de blocage ou de limite.

## Étapes suivantes — non intégrées

| Source | Point d’entrée officiel | Travail préalable nécessaire |
|---|---|---|
| FMI | https://data.imf.org/en/Resource-Pages/IMF-API | API SDMX 2.1/3.0 ; découvrir dataflows, unités, millésimes, clés et statuts estimé/projeté avant tout mapping ; vérifier conditions/quota |
| BAD | https://www.afdb.org/en/knowledge/statistics | Identifier l’accès machine officiellement proposé pour le dataset ciblé ; valider les conditions et les révisions |
| UNCTAD | https://unctadstat.unctad.org/datacentre/ | Vérifier téléchargement autorisé/API, codes, prix courants/constants, mesures IDE flux/stocks |
| UN Comtrade | https://uncomtrade.org/docs/un-comtrade-api/ | Gérer produits HS, partenaires, flux et révisions ; revoir quotas et abonnement avant gros volumes |
| FAOSTAT | https://www.fao.org/faostat/ | Découvrir catalogue/API ou bulk autorisé, éléments/unités et flags, vérifier conditions et volumes |
| ILOSTAT | https://ilostat.ilo.org/data/bulk/ | Télécharger tables et dictionnaires, mapper sexe/âge/source et statuts ; éviter le double compte avec séries OIT déjà distribuées par WDI |

Autres références officielles :
- FMI : https://www.imf.org/external/datamapper/api/
- Comtrade clés : https://uncomtrade.org/docs/api-subscription-keys/
- FAOSTAT annonce API : https://www.fao.org/statistics/highlights-archive/highlights-detail/faostat-launches-a-new-api-developer-portal-to-make-data-access-easier/en
- ILOSTAT guide : https://webapps.ilo.org/ilostat-files/Documents/ILOSTAT_BulkDownload_Guidelines.pdf

Ordre proposé : ILOSTAT / FMI après le MVP, puis Comtrade / FAOSTAT, enfin BAD / UNCTAD selon les accès validés. Ce document n’affirme aucune intégration de ces sources, ni aucune conformité non vérifiée. Aucun scraping général du Web : découverte dans des catalogues institutionnels seulement.
