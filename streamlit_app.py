import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. CONFIGURATION ET STYLE ---
st.set_page_config(page_title="EUROSOM Manager", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f1f1 100%);
        border-left: 6px solid #800020;
        padding: 20px; border-radius: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #212529; font-family: 'Inter', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f1f1f1; border-radius: 5px; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #800020; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS DE NETTOYAGE ---
def format_euro(valeur):
    """Règle d'or : Euro près, espace pour milliers, pas de 'k'"""
    return f"{valeur:,.0f} €".replace(",", " ")

def clean_data(df):
    if df.empty: return df
    df.columns = df.columns.astype(str).str.upper().str.strip()
    
    # Nettoyage des montants
    col_ca = [c for c in df.columns if "MONTANT" in c]
    if col_ca:
        df['CA_NUM'] = df[col_ca[0]].apply(lambda x: float(str(x).replace('€','').replace(' ','').replace(',','.')) if pd.notnull(x) and str(x).strip() != "" else 0.0)
    
    # Nettoyage des heures
    col_h = [c for c in df.columns if "HEURE" in c or "TEMPS" in c]
    if col_h:
        df['HEURES_NUM'] = pd.to_numeric(df[col_h[0]], errors='coerce').fillna(0)
    
    # Dates
    df['DATE_CMD_DT'] = pd.to_datetime(df['DATE DE LA COMMANDE'], errors='coerce', dayfirst=True)
    df['DATE_POSE_DT'] = pd.to_datetime(df['DATE PREVUE DELAI'], errors='coerce', dayfirst=True)
    
    # Extractions pour graphiques
    df['MOIS_CMD'] = df['DATE_CMD_DT'].dt.strftime('%Y-%m')
    df['MOIS_POSE'] = df['DATE_POSE_DT'].dt.strftime('%Y-%m')
    df['DPT'] = df['CP'].astype(str).str[:2]
    
    return df

# --- 3. CHARGEMENT ---
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read()
    except:
        return pd.DataFrame()

# --- 4. INTERFACE PRINCIPALE ---
st.title("🛡️ EUROSOM Manager")
df_raw = load_data()
df = clean_data(df_raw)

if not df.empty:
    # Onglets de navigation
    tab1, tab2, tab3 = st.tabs(["📊 TABLEAU DE BORD", "✍️ SAISIE COMMANDE", "💼 ESPACE COMMERCIAUX"])

    with tab1:
        # Metrics hauts
        c1, c2, c3 = st.columns(3)
        total_ca = df['CA_NUM'].sum()
        c1.metric("CA TOTAL COMMANDÉ", format_euro(total_ca))
        c2.metric("COMMANDES TOTALES", len(df))
        c3.metric("HEURES DE POSE PRÉVUES", f"{df['HEURES_NUM'].sum():.1f} h")

        st.divider()
        
        # Graphiques
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("📈 Ventes Mensuelles (Date Commande)")
            df_v = df.groupby('MOIS_CMD')['CA_NUM'].sum().reset_index()
            fig_v = px.bar(df_v, x='MOIS_CMD', y='CA_NUM', color_discrete_sequence=['#800020'])
            fig_v.update_traces(texttemplate='%{y:,.0f} €', textposition='outside')
            st.plotly_chart(fig_v, use_container_width=True)

            st.subheader("🌍 Répartition par Département")
            df_geo = df.groupby('DPT')['CA_NUM'].sum().reset_index()
            fig_geo = px.pie(df_geo, values='CA_NUM', names='DPT', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_geo, use_container_width=True)

        with g2:
            st.subheader("🎯 Objectif Facturation (Date Pose)")
            df_f = df.groupby('MOIS_POSE')['CA_NUM'].sum().reset_index()
            fig_f = px.bar(df_f, x='MOIS_POSE', y='CA_NUM', color_discrete_sequence=['#2E7D32'])
            fig_f.update_traces(texttemplate='%{y:,.0f} €', textposition='outside')
            st.plotly_chart(fig_f, use_container_width=True)

            st.subheader("⏳ Charge de Pose (Heures / Mois)")
            df_h = df.groupby('MOIS_POSE')['HEURES_NUM'].sum().reset_index()
            fig_h = px.line(df_h, x='MOIS_POSE', y='HEURES_NUM', markers=True, line_shape='spline')
            st.plotly_chart(fig_h, use_container_width=True)

    with tab2:
        st.subheader("🆕 Saisie d'une nouvelle commande")
        st.info("Cette section permet de préparer les données. Pour l'écriture directe, il est conseillé de remplir le Google Sheet.")
        with st.form("new_cmd"):
            col_a, col_b = st.columns(2)
            num_cmd = col_a.text_input("N° Commande")
            client = col_b.text_input("Nom Client")
            cp = col_a.text_input("Code Postal")
            montant = col_b.number_input("Montant HT", step=100.0)
            date_c = col_a.date_input("Date Commande")
            date_p = col_b.date_input("Date Pose Prévue")
            if st.form_submit_button("Valider la saisie"):
                st.success("Données prêtes à être ajoutées au registre.")

    with tab3:
        st.subheader("💼 Espace Suivi Commerciaux")
        comm_list = ["Tous"] + sorted(df['COMMERCIAL'].dropna().unique().tolist())
        sel_comm = st.selectbox("Sélectionner un commercial", comm_list)
        
        df_comm = df if sel_comm == "Tous" else df[df['COMMERCIAL'] == sel_comm]
        
        st.dataframe(df_comm[['DATE DE LA COMMANDE', 'CLIENT', 'VILLE', 'MONTANT HT COMMANDE', 'STATUT MESURES']], use_container_width=True)
        
        st.markdown("### 📏 Dossiers sans mesures reçues")
        # Filtre les dossiers où les mesures ne sont pas arrivées
        df_alerte = df_comm[df_comm['STATUT MESURES'] != "RECUES"]
        st.warning(f"Il y a {len(df_alerte)} dossiers en attente de mesures.")
        st.table(df_alerte[['CLIENT', 'VILLE', 'DATE PREVUE DELAI']])

else:
    st.error("Impossible de charger les données pour construire les graphiques.")
