def strategic(frame):
    """Deterministic evidence template; no causal or fabricated claims."""
    good = frame[
        frame.value.notna()
        & (frame.quality_status != "rejected")
        & (frame.data_status != "projected")
    ].sort_values("period")
    if good.empty:
        return {
            "Observations": "Aucune donnée admissible.",
            "Interprétations": "Non établies.",
            "Hypothèses": "Non testées.",
            "Recommandations": "Vérifier la couverture avant toute analyse.",
        }
    last = good.iloc[-1]
    text = f"Dernière valeur publiée : {last.value:.4g} {last.unit}, en {int(last.period)}. Statut : {last.data_status}. Version : {last.version_id}."
    if len(good) > 1:
        previous = good.iloc[-2]
        text += f" Écart entre {int(previous.period)} et {int(last.period)} : {last.value - previous.value:+.4g} {last.unit}."
    return {
        "Observations": text,
        "Interprétations": "Ce changement décrit cette série et cette unité ; il ne démontre ni causalité ni amélioration générale de l’économie.",
        "Hypothèses": "Comparabilité des définitions et absence de rupture majeure à confirmer dans les métadonnées et notes de source.",
        "Recommandations": "Examiner les alertes, confronter aux statistiques nationales et comparer les pays sur une même année avant de retenir une orientation stratégique.",
    }
