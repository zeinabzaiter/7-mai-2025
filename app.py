import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Résistance Antibiotiques 2024", layout="wide")
st.title("% de Résistance aux Antibiotiques - Semaine par Semaine (2024)")
st.caption("ℹ️ Une souche est considérée VRSA si la CMI VA ou VAM est ≥ 1 mg/L. Les alertes sont basées sur cette définition pour VRSA et sur la règle de Tukey pour les autres.")

@st.cache_data
def load_data():
    return pd.read_excel("tests_par_semaine_antibiotiques_2024.xlsx")

df = load_data()

# Intégration des données CMI VA + VAM
cmi_raw = pd.read_excel("Saur.xlsx")
cmi_raw["CMI VA"] = cmi_raw["Valeur.37"].astype(str).str.replace("mg/L", "", regex=False).str.replace(">", "", regex=False).str.replace("≤", "", regex=False).str.strip()
cmi_raw["CMI VAM"] = cmi_raw["Valeur.39"].astype(str).str.replace("mg/L", "", regex=False).str.replace(">", "", regex=False).str.replace("≤", "", regex=False).str.strip()
cmi_raw["CMI VA"] = pd.to_numeric(cmi_raw["CMI VA"], errors="coerce")
cmi_raw["CMI VAM"] = pd.to_numeric(cmi_raw["CMI VAM"], errors="coerce")
cmi_raw["VRSA_CMI_fusion"] = (cmi_raw["CMI VA"] >= 1) | (cmi_raw["CMI VAM"] >= 1)
cmi_raw["Semaine"] = pd.to_datetime(cmi_raw["Date de prél."], errors="coerce").dt.isocalendar().week

# Calcul par semaine
weekly_cmi = cmi_raw.groupby("Semaine").agg(
    N_tests_CMI_fusion=("VRSA_CMI_fusion", "count"),
    N_VRSA_CMI_fusion=("VRSA_CMI_fusion", "sum")
).reset_index()

weekly_cmi["% VRSA (CMI fusion ≥ 1)"] = round(
    (weekly_cmi["N_VRSA_CMI_fusion"] / weekly_cmi["N_tests_CMI_fusion"]) * 100, 2
)

# Fusion avec données principales
df = df.merge(weekly_cmi, on="Semaine", how="left")
df["Semaine"] = pd.to_numeric(df["Semaine"], errors="coerce")
df = df.dropna(subset=["Semaine"])
df["Semaine"] = df["Semaine"].astype(int)

# Colonnes %
percent_cols = [col for col in df.columns if "%" in col]

# Application des alertes (Tukey ou seuil fixe)
alert_info = {}
for col in percent_cols:
    if col == "%R VA":
        df["Alerte_VRSA"] = df["R VA"] >= 1
        alert_info[col] = {"Q1": "-", "Q3": "-", "Seuil": "≥ 1 cas (fixe)"}
        continue
    elif col == "% VRSA (CMI fusion ≥ 1)":
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        seuil = q3 + 1.5 * iqr
        df["Alerte_CMI"] = df[col] > seuil
        alert_info[col] = {"Q1": round(q1, 2), "Q3": round(q3, 2), "Seuil": round(seuil, 2)}
        continue
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    seuil = q3 + 1.5 * iqr
    df[f"Alert {col}"] = df[col] > seuil
    alert_info[col] = {"Q1": round(q1, 2), "Q3": round(q3, 2), "Seuil": round(seuil, 2)}

# Sélection affichage
to_plot = st.multiselect("Choisissez les antibiotiques à afficher (colonnes %)", percent_cols, default=percent_cols)

# Slider semaine
semaine_min, semaine_max = st.slider(
    "Filtrer par plage de semaines",
    min_value=int(df["Semaine"].min()),
    max_value=int(df["Semaine"].max()),
    value=(int(df["Semaine"].min()), int(df["Semaine"].max()))
)

filtered_df = df[(df["Semaine"] >= semaine_min) & (df["Semaine"] <= semaine_max)]

# Graphique interactif
fig = px.line(filtered_df, x="Semaine", y=to_plot, markers=True)
fig.update_layout(title="Évolution Hebdomadaire du % de Résistance (CMI ≥ 1 mg/L = VRSA, Tukey pour les autres)")
st.plotly_chart(fig, use_container_width=True)
