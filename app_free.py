"""Free public demonstration, backed only by a disposable local SQLite cache."""

import logging
import os
from datetime import datetime
import runpy
from pathlib import Path
import streamlit as st
from openbil.free_hosting import ensure_data

st.set_page_config(
    page_title="OpenBIL · Version gratuite", page_icon="🌍", layout="wide"
)
st.info(
    "Version gratuite · Base temporaire reconstruite depuis la Banque mondiale. Actualisation à l’ouverture, au plus une fois par jour ; aucune collecte pendant la mise en veille. Les révisions archivées localement peuvent être perdues lors d’un redémarrage."
)
try:
    with st.spinner(
        "Vérification des données Banque mondiale… La première collecte peut prendre quelques minutes."
    ):
        state = ensure_data()
except Exception:
    logging.getLogger(__name__).exception("Free demo data preparation failed")
    st.error(
        "Impossible de préparer les données. Réessayez plus tard ; aucune valeur fictive ne sera affichée."
    )
    st.stop()
last_attempt = datetime.fromisoformat(state["last_attempt_at"]).strftime("%d/%m/%Y à %H:%M UTC")
next_eligible = datetime.fromisoformat(state["next_eligible_at"]).strftime("%d/%m/%Y à %H:%M UTC")
st.caption(
    f"Dernière tentative : {last_attempt}. Une nouvelle collecte pourra être déclenchée "
    f"par une visite à partir du {next_eligible}. Cet horaire ne garantit pas une exécution."
)
os.environ["DATABASE_URL"] = state["url"]
if state["refreshed"]:
    st.cache_data.clear()
if state["status"] != "success":
    st.warning(
        "La collecte est partielle ou indisponible. Les données précédentes, si elles existent, restent consultables. Nouvelle tentative possible après une heure."
    )
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
