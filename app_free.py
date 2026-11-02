"""Free public demonstration, backed only by a disposable local SQLite cache."""

import os
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
    st.error(
        "Impossible de préparer les données. Réessayez plus tard ; aucune valeur fictive ne sera affichée."
    )
    st.stop()
os.environ["DATABASE_URL"] = state["url"]
if state["refreshed"]:
    st.cache_data.clear()
if state["status"] != "success":
    st.warning(
        "La collecte est partielle ou indisponible. Les données précédentes, si elles existent, restent consultables. Nouvelle tentative possible après une heure."
    )
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
