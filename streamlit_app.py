import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="EUROSOM Manager", layout="wide", page_icon="📊")

# --- STYLE PERSONNALISÉ (BORDEAUX) ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #800020; }
    div[data-testid="stSidebar"] { background-color: #800020; }
    div[data-testid="stSidebar"] .stMarkdown { color: white; }
    </style>
    """, unsafe_all_original_headers=True)

# --- CHARGEMENT DES DONNÉES (Simulation de connexion Drive) ---
# Note : Pour la mise en production, on utilisera st.connection("google_drive")
@st.cache_data(ttl=600) # Rafraîchit toutes les 10 min
def load_data():
    # Ici, nous lisons le fichier Excel. 
    # En version finale, le chemin sera l'ID de votre fichier Drive
    try:
        # Simulation lecture (remplacer par votre logique Drive)
        df = pd.read_excel("votre_fichier_drive.xlsx", sheet_name="SUIVI COMMANDES EN COURS")
        # ... (Logique de nettoyage identique au Cahier des Charges)
        return df
    except:
        st.error("Impossible de se connecter au Google Drive.")
        return pd.DataFrame()

# --- BARRE LATÉRALE (FILTRES) ---
with st.sidebar:
    st.image("logo.png") # Si présent dans le dépôt
    st.title("🛡️ Filtres")
    
    view_mode = st.radio("Mode de Vue", ["Exercice Comptable", "Année Civile"])
    
    df = load_data()
    
    if not df.empty:
        list_comm = ["Tous"] + sorted(df["COMMERCIAL"].unique().tolist())
        sel_comm = st.selectbox("Commercial", list_comm)
        
        if view_mode == "Année Civile":
            list_period = sorted(df["Annee_Civile"].unique().tolist())
        else:
            list_period = sorted(df["Exercice_Cpt"].unique().tolist())
        
        sel_period = st.selectbox("Période", list_period, index=len(list_period)-1)

# --- CORPS DE L'APPLICATION ---
st.title("📊 Pilotage Commercial & Logistique")

if not df.empty:
    # Filtrage
    df_filtered = df[df["COMMERCIAL"] == sel_comm] if sel_comm != "Tous" else df
    col_period = "Annee_Civile" if view_mode == "Année Civile" else "Exercice_Cpt"
    df_filtered = df_filtered[df_filtered[col_period] == sel_period]

    # --- INDICATEURS CLÉS (METRICS) ---
    col1, col2, col3 = st.columns(3)
    total_ca = df_filtered["Montant_Clean"].sum()
    nb_cmd = len(df_filtered)
    
    col1.metric("CA Commandé (HT)", f"{total_ca:,.0f} €".replace(",", " "))
    col2.metric("Nombre de Commandes", nb_cmd)
    col3.metric("Moyenne Panier", f"{total_ca/nb_cmd:,.0f} €".replace(",", " ") if nb_cmd > 0 else "0 €")

    # --- GRAPHIQUES ---
    tab1, tab2 = st.tabs(["📈 Analyses Graphiques", "📏 Mesures & Logistique"])

    with tab1:
        c1, c2 = st.columns(2)
        
        # Graphique 1 : CA par Date de Commande
        with c1:
            grp_ca = df_filtered.groupby("Mois_Cmd")["Montant_Clean"].sum().reset_index()
            fig_ca = px.bar(grp_ca, x="Mois_Cmd", y="Montant_Clean", 
                            title="CA par Date de Commande", color_discrete_sequence=['#800020'])
            st.plotly_chart(fig_ca, use_container_width=True)

        # Graphique 2 : Facturation par Date de Pose
        with c2:
            grp_pose = df_filtered.groupby("Mois_Pose")["Montant_Clean"].sum().reset_index()
            fig_pose = px.bar(grp_pose, x="Mois_Pose", y="Montant_Clean", 
                              title="Objectif Facturation (Date de Pose)", color_discrete_sequence=['#2E7D32'])
            st.plotly_chart(fig_pose, use_container_width=True)

    with tab2:
        st.subheader("Dossiers en attente de mesures")
        # Logique de calcul Butoire...
        # Affichage du tableau filtré pour les commerciaux
        st.dataframe(df_filtered[["CMD_NUM", "CLIENT", "VILLE", "STATUT_MES", "Butoire"]], use_container_width=True)

else:
    st.info("Veuillez configurer la connexion au Drive dans les paramètres.")
