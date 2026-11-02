# Méthodologie scientifique — MVP 0.2.0

## Périmètre et collecte

17 États : Bénin, Burkina Faso, Cabo Verde, Côte d’Ivoire, Gambie, Ghana, Guinée, Guinée-Bissau, Liberia, Mali, Mauritanie, Niger, Nigeria, Sénégal, Sierra Leone, Togo, plus Kenya. L’Afrique de l’Ouest est géographique ; les changements d’appartenance à la CEDEAO ne changent pas le périmètre. Les territoires non souverains ne sont pas inclus. Extension aux autres États africains : ultérieure.

La série cible 1960 à la dernière année civile complète (2025 lors des essais du 2 novembre 2026). Les données de l’année en cours ne sont pas demandées par défaut ; `--end` permet de les demander. Aucune donnée n’est générée pour remplir un trou. Une grille annuelle explicite permet de mesurer la couverture, même lorsque l’API omet certaines cellules.

Les 11 indicateurs couvrent PIB nominal et croissance réelle, inflation, emploi et chômage modélisés, importations, exportations, IDE nets et valeurs ajoutées agriculture/industrie/services. Les montants nominaux ne mesurent pas la croissance réelle ; les parts du PIB ne mesurent pas le volume commercial. L’IDE net peut être négatif et une part d’exportation peut dépasser 100 % : ces situations ne sont pas rejetées arbitrairement.

## Provenance, statuts et dates

- `observed` : réservé à une observation attestée par une convention de source validée. Aucun statut vide WDI n’est automatiquement converti en observed.
- `estimated` : les deux indicateurs OIT modélisés du catalogue sont explicitement identifiés.
- `projected` : champ WDI `obs_status=F` (forecast), prioritaire sur le statut du catalogue ; sorties OpenBIL conservées séparément.
- `missing` : NULL source ou cellule absente de la réponse ; cette dernière est marquée `absent_from_response`.
- `unspecified` : valeur publiée dont la nature n’est pas établie par les champs retenus. Elle peut être une estimation ; ne pas la présenter comme une mesure directe.

`collected_at` est l’horodatage UTC du snapshot. Les dates de réception détaillées sont dans le manifeste. `source_updated_at` est `lastupdated` du dataset : **ce n’est pas la date de publication de chaque observation**. `published_at` reste NULL lorsque cette date n’est pas fournie. Les métadonnées et `sourceOrganization` identifient le producteur primaire lorsque renseigné ; Banque mondiale peut être agrégateur.

Les unités sont un mapping révisé dans `catalog.py` correspondant aux intitulés WDI, conservés en métadonnées. Aucune conversion d’échelle, arrondi des données stockées, correction de devise, désaisonnalisation ou imputation. Paramètre `scale=n`. Toute évolution de transformation doit changer la version logicielle.

## Contrôles

Contrôles bloquants : enveloppe API, erreurs applicatives, nombre de pages/lignes, stabilité de `lastupdated` et du total entre pages, code pays/indicateur, année, doublons, booléens/chaînes ou nombres non finis. Une violation bloque le commit du dataset et conserve la version précédente. Une réponse totalement vide est traitée comme un échec à revoir, pas une suppression massive.

Contrôles conservés avec rejet : PIB nominal négatif, emploi/chômage hors [0,100]. La valeur d’origine demeure en base mais `rejected` l’exclut des analyses et prévisions ; elle reste exportable avec son statut.

Alertes non bloquantes : note de source, statut non interprété, modification de métadonnées et variation annuelle absolue supérieure à `max(2 × |valeur précédente|, 20)`. Ce seuil grossier est une heuristique de revue, pas un test statistique universel ni la preuve d’une rupture. Pas de comparaison à travers un trou annuel. Les alertes nécessitent expertise et confrontation aux métadonnées nationales ; le MVP ne certifie pas la comparabilité.

Couverture : nombre de cellules non nulles et non rejetées / (pays sélectionnés × années de la fenêtre). Présenter séparément avertissements, rejets, manque et statut statistique. Une qualité technique `pass` ne prouve ni exactitude économique, ni qualité de l’enquête, ni nature observée.

## Prévisions et évaluation

Modèles candidats : dernière valeur (naïf) et marche avec dérive moyenne depuis le premier point. Retenir le dernier segment annuel contigu admissible, sans valeurs source projetées ni rejetées. Minimum 14 années. Les filtres de période délimitent l’échantillon.

1. Réserver les trois dernières années comme test final.
2. Sur le passé restant, comparer les modèles sur quatre origines croissantes, chacune prédisant un an en avant ; MAE de validation pour la sélection, naïf en cas d’égalité.
3. Sans accéder aux vérités test, produire trois prévisions depuis la même origine ; rapporter MAE et RMSE du modèle sélectionné et MAE du naïf. La comparaison finale ne resélectionne pas le modèle.
4. Réajuster le modèle sélectionné sur tout l’historique admissible pour une prévision de 1 à 5 années après le dernier point.

Aucun intervalle d’incertitude n’est présenté comme calibré : le MVP ne fournit que des prévisions ponctuelles. Pas de clipping artificiel : contrôler la plausibilité des projections, notamment les taux bornés. Les tests évaluent trois horizons ; la qualité à 4–5 ans n’est pas évaluée. Trois points test et quatre validations donnent une forte incertitude sur la performance.

Les données sont le millésime courant, potentiellement révisé : l’exercice **n’est pas un backtest en information réellement disponible à chaque date historique**. Les versions commenceront à permettre ce protocole dans le futur. Les ruptures structurelles, chocs et définitions ne sont pas modélisés ; absence de causalité, de recommandation d’investissement ou de garantie prédictive.

## Analyses stratégiques

Le générateur déterministe cite la dernière valeur admissible, son année, son unité, son statut et sa version. Il distingue les observations des interprétations, des hypothèses non testées et des recommandations de vérification. Les comparaisons pays se font à année commune ; jamais une hiérarchie de pays à partir de « dernières valeurs » d’années différentes. Les modèles ne génèrent aucun fait historique.

## Limites à déclarer dans une étude

Couverture inégale ; valeurs révisables et disponibilité tardive ; nature statistique parfois non déterminée ; éventuelles ruptures non détectées ; harmonisation WDI imparfaite ; dépendance à des fournisseurs primaires aux droits spécifiques ; unités agrégées et risques d’erreur écologique ; absence de validation externe de l’exactitude ; petit échantillon de backtest et millésime révisé ; seuls WDI et la fréquence annuelle sont intégrés dans ce MVP. Les résultats techniques ne constituent pas une validation scientifique générale.
