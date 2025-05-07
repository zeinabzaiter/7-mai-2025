import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Résistance Antibiotiques 2024", layout="wide")
st.title("% de Résistance aux Antibiotiques - Semaine par Semaine (2024)")
st.caption("ℹ️ Une souche est considérée VRSA si CMI VA ≥ 1 mg/L. Les alertes sont basées sur cette définition clinique ainsi que sur la règle de Tukey pour les autres antibiotiques.")

# Chargement des données
@st.cache_data
def load_data():
    df = pd.read_excel("tests_par_semaine_antibiotiques_2024.xlsx")
    return df

df = load_data()

# Intégration des données CMI VA
cmi_raw = pd.read_excel("Saur.xlsx")

# Accès par position (CL = 88e, CP = 92e colonne => index 87 et 91)
cmi_raw["CMI VA"] = cmi_raw.iloc[:, 87].astype(str).str.replace("mg/L", "").str.replace("<", "").str.replace(">", "").str.strip()
cmi_raw["CMI VAM"] = cmi_raw.iloc[:, 91].astype(str).str.replace("mg/L", "").str.replace("<", "").str.replace(">", "").str.strip()

cmi_raw["CMI VA"] = pd.to_numeric(cmi_raw["CMI VA"], errors="coerce")
cmi_raw["CMI VAM"] = pd.to_numeric(cmi_raw["CMI VAM"], errors="coerce")

# Détection VRSA si l'un des deux CMI est >= 1
cmi_raw["VRSA_CMI"] = (cmi_raw["CMI VA"] >= 1) | (cmi_raw["CMI VAM"] >= 1)
cmi_raw["Semaine"] = pd.to_datetime(cmi_raw["Date de prél."], errors="coerce").dt.isocalendar().week

# Regrouper les données CMI par semaine
weekly_cmi = cmi_raw.groupby("Semaine").agg(
    N_tests_CMI_VA=("CMI VA", "count"),
    N_VRSA_CMI=("VRSA_CMI", "sum")
).reset_index()
weekly_cmi["% VRSA (CMI fusion ≥ 1)"] = round((weekly_cmi["N_VRSA_CMI"] / weekly_cmi["N_tests_CMI_VA"]) * 100, 2)

# Fusionner avec le df principal
df = df.merge(weekly_cmi, on="Semaine", how="left")

# Nettoyage de la colonne Semaine
df["Semaine"] = pd.to_numeric(df["Semaine"], errors="coerce")
df = df.dropna(subset=["Semaine"])
df["Semaine"] = df["Semaine"].astype(int)

# Identifier les colonnes de %
percent_cols = [col for col in df.columns if "%" in col]

# Appliquer la règle de Tukey pour les autres colonnes
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
        threshold = q3 + 1.5 * iqr
        df["Alerte_CMI"] = df[col] > threshold
        alert_info[col] = {"Q1": round(q1, 2), "Q3": round(q3, 2), "Seuil": round(threshold, 2)}
        continue
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    threshold = q3 + 1.5 * iqr
    df[f"Alert {col}"] = df[col] > threshold
    alert_info[col] = {"Q1": round(q1,2), "Q3": round(q3,2), "Seuil": round(threshold,2)}

# Sélection d'antibiotiques à afficher
to_plot = st.multiselect("Choisissez les antibiotiques à afficher (colonnes %)", percent_cols, default=percent_cols)

# Filtrage par plage de semaines
semaine_min, semaine_max = st.slider(
    "Filtrer par plage de semaines",
    min_value=int(df["Semaine"].min()),
    max_value=int(df["Semaine"].max()),
    value=(int(df["Semaine"].min()), int(df["Semaine"].max()))
)

# Filtrage du dataframe
filtered_df = df[(df["Semaine"] >= semaine_min) & (df["Semaine"] <= semaine_max)]

# Tracer le graphique avec le nombre de tests en secondaire
to_plot_cols = to_plot.copy()
if "% VRSA (CMI fusion ≥ 1)" in df.columns and "N_tests_CMI_VA" in df.columns:
    fig = go.Figure()
    for col in to_plot_cols:
        fig.add_trace(go.Scatter(x=filtered_df["Semaine"], y=filtered_df[col], mode='lines+markers', name=col))
    fig.add_trace(go.Bar(x=filtered_df["Semaine"], y=filtered_df["N_tests_CMI_VA"], name="Nb tests CMI", yaxis="y2", marker=dict(color='lightgrey')))
    fig.update_layout(
        title="Evolution Hebdomadaire du % de Résistance (CMI ≥ 1 mg/L = VRSA, Tukey pour les autres)",
        yaxis=dict(title="% Résistance"),
        yaxis2=dict(title="Nb de tests CMI", overlaying='y', side='right', showgrid=False),
        legend=dict(x=1.01, y=1)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    fig = px.line(filtered_df, x="Semaine", y=to_plot, markers=True)
    fig.update_layout(title="Evolution Hebdomadaire du % de Résistance (CMI ≥ 1 mg/L = VRSA, Tukey pour les autres)")
    st.plotly_chart(fig, use_container_width=True)

# Afficher le tableau des semaines en alerte
st.subheader("📋 Semaines avec Alerte de Résistance")
alert_cols = [col for col in df.columns if col.startswith("Alerte_") or col.startswith("Alert ")]
if alert_cols:
    alert_table = df[["Semaine"] + alert_cols].copy()
    st.dataframe(alert_table.sort_values(by="Semaine"))
