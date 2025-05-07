import streamlit as st
import pandas as pd
import plotly.express as px

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
import pandas as pd
cmi_raw = pd.read_excel("Saur.xlsx")
cmi_raw["CMI VA"] = cmi_raw["Valeur.37"].str.replace("mg/L", "", regex=False)
cmi_raw["CMI VA"] = cmi_raw["CMI VA"].str.replace(">", "", regex=False).str.strip()
cmi_raw["CMI VA"] = pd.to_numeric(cmi_raw["CMI VA"], errors="coerce")
cmi_raw["VRSA_CMI"] = cmi_raw["CMI VA"] >= 1
cmi_raw["Semaine"] = pd.to_datetime(cmi_raw["Date de prél."], errors="coerce").dt.isocalendar().week

# Regrouper les données CMI par semaine
weekly_cmi = cmi_raw.groupby("Semaine").agg(
    N_tests_CMI_VA=("CMI VA", "count"),
    N_VRSA_CMI=("VRSA_CMI", "sum")
).reset_index()
weekly_cmi["% VRSA (CMI VA ≥ 1)"] = round((weekly_cmi["N_VRSA_CMI"] / weekly_cmi["N_tests_CMI_VA"]) * 100, 2)

# Fusionner avec le df principal si Semaine est commun
df = df.merge(weekly_cmi, on="Semaine", how="left")

# Nettoyage de la colonne Semaine pour éviter erreurs de type
df["Semaine"] = pd.to_numeric(df["Semaine"], errors="coerce")
df = df.dropna(subset=["Semaine"])
df["Semaine"] = df["Semaine"].astype(int)

# Identifier les colonnes de %
percent_cols = [col for col in df.columns if "%" in col]

# Appliquer la règle de Tukey pour détecter les alertes (sauf %R VA et % VRSA CMI)
alert_info = {}
for col in percent_cols:
    if col == "%R VA":
        df["Alerte_VRSA"] = df["R VA"] >= 1
        alert_info[col] = {"Q1": "-", "Q3": "-", "Seuil": "≥ 1 cas (fixe)"}
        continue
    elif col == "% VRSA (CMI VA ≥ 1)":
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

# Ajouter la courbe % VRSA (CMI VA ≥ 1) si elle existe
if "% VRSA (CMI VA ≥ 1)" not in percent_cols:
    percent_cols.append("% VRSA (CMI VA ≥ 1)")
fig = px.line(filtered_df, x="Semaine", y=to_plot, markers=True)
fig.update_layout(title="Evolution Hebdomadaire du % de Résistance (CMI ≥ 1 mg/L = VRSA, Tukey pour les autres)")")")"))
st.plotly_chart(fig, use_container_width=True)

# Affichage des alertes
tab1, tab2 = st.tabs(["Tableau d'alerte", "Seuils Tukey"])

with tab1:
    alert_table = pd.DataFrame()
    for col in percent_cols:
        if col == "%R VA":
            semaines_alertes = df[df["Alerte_VRSA"]]["Semaine"].tolist()
        elif col == "% VRSA (CMI VA ≥ 1)":
            semaines_alertes = df[df["Alerte_CMI"]]["Semaine"].tolist()
        else:
            semaines_alertes = df[df[f"Alert {col}"]]["Semaine"].tolist()
        for s in semaines_alertes:
            alert_table = pd.concat([alert_table, pd.DataFrame({"Antibiotique": [col], "Semaine": [s], "% R": [df.loc[df["Semaine"] == s, col].values[0]]})])

    # Nettoyer et forcer le format des semaines
    alert_table["Semaine"] = pd.to_numeric(alert_table["Semaine"], errors="coerce")
    alert_table = alert_table.dropna(subset=["Semaine"])
    alert_table["Semaine"] = alert_table["Semaine"].astype(int)

    st.subheader(":rotating_light: Semaines en alerte selon Tukey ou seuil fixe (VRSA)")
    def highlight_vrsa(row):
        if row['Antibiotique'] == "% VRSA (CMI VA ≥ 1)":
            return ['background-color: #ffcccc']*len(row)
        return ['']*len(row)

    st.dataframe(alert_table.sort_values(by="Semaine").style.apply(highlight_vrsa, axis=1))

with tab2:
    st.subheader("Seuils d'alerte calculés (Tukey ou fixe)")
    seuils_df = pd.DataFrame(alert_info).T
    st.dataframe(seuils_df)

# Option d'affichage des données brutes
with st.expander("Afficher les données complètes"):
    st.dataframe(df)
