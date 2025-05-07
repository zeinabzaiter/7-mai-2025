import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Résistance Antibiotiques 2024", layout="wide")
st.title("📈 % de Résistance aux Antibiotiques - Semaine par Semaine (2024)")

# Chargement des données
@st.cache_data

def load_data():
    df = pd.read_excel("tests_par_semaine_antibiotiques_2024.xlsx")
    return df

df = load_data()

# Identifier les colonnes de %
percent_cols = [col for col in df.columns if "%" in col]

# Appliquer la règle de Tukey pour détecter les alertes
alert_info = {}
for col in percent_cols:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    threshold = q3 + 1.5 * iqr
    df[f"Alert {col}"] = df[col] > threshold
    alert_info[col] = {"Q1": round(q1,2), "Q3": round(q3,2), "Seuil": round(threshold,2)}

# Sélection d'antibiotiques à afficher
to_plot = st.multiselect("Choisissez les antibiotiques à afficher (colonnes %)", percent_cols, default=percent_cols)

# Affichage du graphe
fig = px.line(df, x="Semaine", y=to_plot, markers=True)
fig.update_layout(title="Evolution Hebdomadaire du % de Résistance", yaxis=dict(range=[0, 100]))
st.plotly_chart(fig, use_container_width=True)

# Affichage des alertes
tab1, tab2 = st.tabs(["Tableau d'alerte", "Seuils Tukey"])

with tab1:
    alert_table = pd.DataFrame()
    for col in percent_cols:
        semaines_alertes = df[df[f"Alert {col}"]]["Semaine"].tolist()
        for s in semaines_alertes:
            alert_table = pd.concat([alert_table, pd.DataFrame({"Antibiotique": [col], "Semaine": [s], "% R": [df.loc[df["Semaine"] == s, col].values[0]]})])
    st.subheader(":rotating_light: Semaines en alerte selon la règle de Tukey")
    st.dataframe(alert_table.sort_values(by="Semaine"))

with tab2:
    st.subheader("Seuils d'alerte calculés (Tukey)")
    seuils_df = pd.DataFrame(alert_info).T
    st.dataframe(seuils_df)

# Option d'affichage des données brutes
with st.expander("Afficher les données complètes"):
    st.dataframe(df)
