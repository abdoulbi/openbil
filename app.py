import os
import json
import pandas as pd
import streamlit as st
from sqlalchemy import text
from openbil.db import engine
from openbil.catalog import COUNTRIES, INDICATORS, TERMS
from openbil.forecast import forecast
from openbil.analysis import strategic

st.set_page_config(
    page_title="OpenBIL · Intelligence économique", page_icon="🌍", layout="wide"
)
st.title("OpenBIL")
st.caption(
    "Intelligence économique africaine · Données traçables · Banque mondiale / WDI"
)


@st.cache_data(ttl=120)
def load(url):
    e = engine(url)
    try:
        with e.connect() as c:
            return (
                pd.read_sql(text("SELECT * FROM current_observations"), c),
                pd.read_sql(
                    text(
                        "SELECT * FROM collection_runs ORDER BY started_at DESC LIMIT 30"
                    ),
                    c,
                ),
                pd.read_sql(text("SELECT * FROM dataset_versions"), c),
            )
    finally:
        e.dispose()


url = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://openbil:openbil@localhost:5432/openbil"
)
try:
    data, runs, versions = load(url)
except Exception:
    st.error(
        "Base indisponible ou non initialisée. Exécutez les migrations et une collecte ; consultez les journaux serveur."
    )
    st.stop()
if data.empty:
    st.info(
        "Aucune donnée collectée. Lancez openbil collect ; aucune série de démonstration ne sera substituée."
    )
    st.stop()
with st.sidebar:
    st.header("Explorer")
    code = st.selectbox(
        "Indicateur", list(INDICATORS), format_func=lambda k: INDICATORS[k][0]
    )
    choices = st.multiselect(
        "Pays",
        list(COUNTRIES),
        default=["BFA", "KEN", "GHA"],
        format_func=lambda k: COUNTRIES[k],
    )
    lower, upper = int(data.period.min()), int(data.period.max())
    years = (
        st.slider("Années", lower, upper, (max(lower, 2000), upper))
        if lower < upper
        else (lower, upper)
    )
    statuses = st.multiselect(
        "Statuts de données",
        sorted(data.data_status.unique()),
        default=sorted(data.data_status.unique()),
    )
    st.caption(
        "unspecified = nature non établie par les champs source ; estimated = estimation documentée. Les projections source sont distinguées."
    )
    if st.button("Actualiser la vue"):
        st.cache_data.clear()
        st.rerun()
base = data[
    (data.indicator_id == code)
    & data.country_id.isin(choices)
    & data.period.between(*years)
]
filtered = base[base.data_status.isin(statuses)].copy()
valid = base.value.notna() & (base.quality_status != "rejected")
expected = len(choices) * (years[1] - years[0] + 1)
a, b, c, d = st.columns(4)
a.metric("Couverture admissible", f"{valid.sum() / expected:.1%}" if expected else "—")
b.metric("Valeurs admissibles", int(valid.sum()))
c.metric(
    "Alertes / rejets", int(base.quality_status.isin(["warning", "rejected"]).sum())
)
d.metric(
    "Dernière collecte", str(base.collected_at.max())[:10] if not base.empty else "—"
)
st.caption(
    "Couverture calculée sur tous les statuts de la sélection pays/période. Les cellules absentes de la base comptent comme manquantes."
)
if runs.iloc[0]["status"] != "success":
    st.warning(
        "Dernière collecte : "
        + str(runs.iloc[0]["status"])
        + ". Les données précédentes restent visibles ; consulter les exécutions."
    )
tabs = st.tabs(
    [
        "Séries & comparaisons",
        "Prévisions",
        "Qualité & provenance",
        "Analyse stratégique",
    ]
)
with tabs[0]:
    st.subheader(INDICATORS[code][0] + " · " + INDICATORS[code][1])
    chart = base.sort_values(["country_id", "period"]).copy()
    chart.loc[
        (chart.quality_status == "rejected") | (~chart.data_status.isin(statuses)),
        "value",
    ] = float("nan")
    # Distinct line segments prevent visually filling missing years or filtered statuses.
    chart["segment"] = (
        (
            (chart.country_id != chart.country_id.shift())
            | (chart.period.diff() != 1)
            | chart.value.isna()
            | chart.value.shift().isna()
            | (chart.data_status != chart.data_status.shift())
        )
        .cumsum()
        .astype(str)
    )
    import altair as alt

    if not chart.empty:
        chart["pays"] = chart.country_id.map(COUNTRIES)
        st.altair_chart(
            alt.Chart(chart)
            .mark_line(point=True)
            .encode(
                x=alt.X("period:O", title="Année"),
                y=alt.Y("value:Q", title=INDICATORS[code][1]),
                color="pays:N",
                strokeDash="data_status:N",
                detail="segment:N",
                tooltip=["pays", "period", "value", "data_status", "quality_status"],
            ),
            width="stretch",
        )
        common_year = st.selectbox(
            "Comparer sur une même année", list(range(years[1], years[0] - 1, -1))
        )
        st.dataframe(
            chart[chart.period == common_year][
                ["pays", "period", "value", "unit", "data_status", "quality_status"]
            ],
            hide_index=True,
        )
    st.download_button(
        "Exporter les données et leur provenance (CSV)",
        filtered.to_csv(index=False).encode("utf-8-sig"),
        "openbil_observations.csv",
        "text/csv",
    )
    st.caption(
        "Citation : The World Bank: World Development Indicators; fournisseurs originaux dans les métadonnées. Conditions : "
        + TERMS
    )
with tabs[1]:
    country = st.selectbox(
        "Pays à prévoir", choices or ["BFA"], format_func=lambda k: COUNTRIES[k]
    )
    h = st.slider("Horizon (années)", 1, 5, 3)
    history = base[base.country_id == country]
    st.info(
        "Naïf / dérive : sélection sur 4 origines, puis test final de 3 années hors échantillon. Série annuelle contiguë, sans imputation. Le filtre de période délimite l’historique."
    )
    try:
        f = forecast(history, h)
        st.write(
            {
                "modèle": f["model"],
                "MAE_validation": f["validation_mae"],
                "MAE_test": f["test_mae"],
                "RMSE_test": f["test_rmse"],
                "MAE_naïf_test": f["naive_test_mae"],
            }
        )
        st.dataframe(f["test"], hide_index=True)
        st.line_chart(f["future"].set_index("period")["value"])
        st.dataframe(f["future"], hide_index=True)
        if f["test_mae"] > f["naive_test_mae"]:
            st.warning(
                "Le modèle sélectionné fait moins bien que le naïf sur le test final."
            )
        st.warning(
            "Prévisions ponctuelles expérimentales, sans intervalle calibré. Test sur les données révisées disponibles aujourd’hui ; pas un test en temps réel. Aucune garantie de continuité structurelle."
        )
        if int(history.period.max()) > f["training_end"]:
            st.warning(
                "La série admissible se termine avant la fin de la période sélectionnée ; les prévisions commencent après sa dernière valeur, pas nécessairement dans le futur calendaire."
            )
        out = f["future"].assign(
            country_id=country,
            indicator_id=code,
            unit=INDICATORS[code][1],
            training_end=f["training_end"],
            test_mae=f["test_mae"],
            source_versions=json.dumps(history.version_id.unique().tolist()),
        )
        st.download_button(
            "Exporter les prévisions séparées",
            out.to_csv(index=False).encode(),
            "openbil_forecasts.csv",
            "text/csv",
        )
    except ValueError as exc:
        st.warning(str(exc))
with tabs[2]:
    st.dataframe(filtered, hide_index=True)
    used = versions[versions.id.isin(filtered.version_id)]
    for _, v in used.iterrows():
        with st.expander(v.dataset_id + " · " + v.id):
            st.json(json.loads(v.metadata_json))
            st.write("Mise à jour du dataset source :", v.source_updated_at)
            st.caption(
                "Date de publication individuelle inconnue : published_at reste NULL."
            )
            st.json(json.loads(v.raw_manifest))
    st.download_button(
        "Exporter les versions et métadonnées",
        used.to_json(orient="records", force_ascii=False),
        "openbil_provenance.json",
        "application/json",
    )
    st.subheader("Exécutions récentes")
    st.dataframe(runs, hide_index=True)
    st.warning(
        "Les alertes de variation sont des indices à examiner, pas des ruptures prouvées. Les ruptures et définitions non documentées par la source peuvent échapper aux contrôles."
    )
with tabs[3]:
    single = st.selectbox(
        "Pays pour la note",
        choices or ["BFA"],
        format_func=lambda k: COUNTRIES[k],
        key="analysis_country",
    )
    for title, body in strategic(base[base.country_id == single]).items():
        st.subheader(title)
        st.write(body)
