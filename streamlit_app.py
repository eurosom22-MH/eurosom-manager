import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="EUROSOM Manager", layout="wide")

# Style épuré Bordeaux & Gris
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f1f1 100%);
        border-left: 6px solid #800020;
        padding: 20px; border-radius: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] { background-color: #800020 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS DE SÉCURITÉ ---
def format_euro(valeur):
    return f"{valeur:,.0f} €".replace(",", " ")

def get_col(df, keyword):
    for c in df.columns:
        if keyword.upper() in str(c).upper():
            return c
    return None

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read()
    except:
        return pd.DataFrame()

# --- 3. TRAITEMENT DES DONNÉES ---
df_raw = load_data()

if not df_raw.empty:
    df = df_raw.copy()
    
    # Identification des colonnes dynamiques
    c_client = get_col(df, "CLIENT") or "CLIENT"
    c_ville = get_col(df, "VILLE") or "VILLE"
    c_mt = get_col(df, "MONTANT") or "MONTANT HT COMMANDE"
    c_date_c = get_col(df, "DATE DE LA COMMANDE") or "DATE DE LA COMMANDE"
    c_date_p = get_col(df, "DATE PREVUE") or "DATE PREVUE DELAI"
    c_statut = get_col(df, "STATUT MESURES") or "STATUT MESURES"
    c_comm = get_col(df, "COMMERCIAL") or "COMMERCIAL"
    c_cp = get_col(df, "CP") or "CP"
    c_h = get_col(df, "HEURE") or "NOMBRE HEURES"

    # Nettoyage numérique
    def to_f(x):
        try: return float(str(x).replace('€','').replace(' ','').replace(',','.'))
        except: return 0.0

    df['MT_NUM'] = df[c_mt].apply(to_f) if c_mt in df.columns else 0.0
    df['H_NUM'] = pd.to_numeric(df[c_h], errors='coerce').fillna(0) if c_h in df.columns else 0.0
    df['D_CMD'] = pd.to_datetime(df[c_date_c], errors='coerce', dayfirst=True)
    df['D_POSE'] = pd.to_datetime(df[c_date_p], errors='coerce', dayfirst=True)
    df['M_CMD'] = df['D_CMD'].dt.strftime('%Y-%m')
    df['M_POSE'] = df['D_POSE'].dt.strftime('%Y-%m')
    df['DEPT'] = df[c_cp].astype(str).str[:2]

    # --- 4. INTERFACE ---
    st.title("🛡️ EUROSOM Manager")
    tab1, tab2, tab3 = st.tabs(["📊 DASHBOARD", "✍️ SAISIE COMMANDE", "💼 ESPACE COMMERCIAUX"])

    # --- ONGLET 1 : DASHBOARD ---
    with tab1:
        c1, c2, c3 = st.columns(3)
        c1.metric("CA TOTAL", format_euro(df['MT_NUM'].sum()))
        c2.metric("COMMANDES", len(df))
        c3.metric("HEURES POSE TOTALES", f"{df['H_NUM'].sum():.0f} h")
        
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("📈 Ventes Mensuelles")
            fig1 = px.bar(df.groupby('M_CMD')['MT_NUM'].sum().reset_index(), x='M_CMD', y='MT_NUM', color_discrete_sequence=['#800020'])
            fig1.update_traces(texttemplate='%{y:,.0f} €', textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)
            
            st.subheader("🌍 Répartition par Dép.")
            fig_geo = px.pie(df.groupby('DEPT')['MT_NUM'].sum().reset_index(), values='MT_NUM', names='DEPT', hole=0.5, color_discrete_sequence=px.colors.sequential.Reds)
            st.plotly_chart(fig_geo, use_container_width=True)

        with g2:
            st.subheader("🎯 Objectif Facturation")
            fig2 = px.bar(df.groupby('M_POSE')['MT_NUM'].sum().reset_index(), x='M_POSE', y='MT_NUM', color_discrete_sequence=['#2E7D32'])
            fig2.update_traces(texttemplate='%{y:,.0f} €', textposition='outside')
            st.plotly_chart(fig2, use_container_width=True)

            st.subheader("⏳ Charge de Pose (Heures)")
            fig3 = px.line(df.groupby('M_POSE')['H_NUM'].sum().reset_index(), x='M_POSE', y='H_NUM', markers=True)
            st.plotly_chart(fig3, use_container_width=True)

    # --- ONGLET 2 : SAISIE ---
    with tab2:
        st.subheader("📝 Nouvelle Commande")
        with st.form("form_saisie", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            # Identification
            n_cde = f1.text_input("N° Commande")
            n_cli = f1.text_input("Nom Client")
            n_ville = f1.text_input("Ville")
            n_cp = f1.text_input("CP")
            # Dates
            n_date_c = f2.date_input("Date Commande")
            n_date_p = f2.date_input("Date Pose Prévue")
            n_type_delai = f2.selectbox("Type de délai", ["ESTIMÉ", "FIXÉ", "À CONFIRMER"])
            n_h = f2.number_input("Heures de pose", min_value=0.0)
            # Montant & Statuts
            n_mt = f3.number_input("Montant HT", min_value=0)
            n_comm = f3.selectbox("Commercial", sorted(df[c_comm].dropna().unique().tolist()))
            n_statut = f3.selectbox("Statut Mesures", ["EN ATTENTE", "REÇUES", "À PRENDRE"])
            n_obs = f3.text_area("Observations")
            
            if st.form_submit_button("💾 ENREGISTRER DANS LE GOOGLE SHEET"):
                try:
                    new_row = pd.DataFrame([{
                        c_date_c: n_date_c.strftime('%d/%m/%Y'), c_client: n_cli, c_ville: n_ville,
                        c_cp: n_cp, c_mt: n_mt, c_comm: n_comm, c_date_p: n_date_p.strftime('%d/%m/%Y'),
                        "TYPE DÉLAI": n_type_delai, c_statut: n_statut, c_h: n_h,
                        "OBSERVATIONS": n_obs, "NUMÉRO DE COMMANDE": n_cde
                    }])
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    current_df = conn.read(ttl=0)
                    updated_df = pd.concat([current_df, new_row], ignore_index=True)
                    conn.update(worksheet="SUIVI COMMANDES EN COURS", data=updated_df)
                    st.cache_data.clear()
                    st.success("✅ Enregistré !")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # --- ONGLET 3 : COMMERCIAUX ---
    with tab3:
        st.subheader("💼 Suivi Commercial")
        sel_c = st.selectbox("Sélectionner un nom", ["Tous"] + sorted(df[c_comm].dropna().unique().tolist()))
        df_view = df if sel_c == "Tous" else df[df[c_comm] == sel_c]
        
        cols_show = [c for c in [c_date_c, c_client, c_ville, c_mt, c_statut] if c in df.columns]
        st.dataframe(df_view[cols_show], use_container_width=True)
        
        st.markdown("### ⚠️ Mesures manquantes")
        df_alerte = df_view[df_view[c_statut].astype(str).str.upper() != "REÇUES"]
        st.table(df_alerte[[c_client, c_ville, c_date_p]] if not df_alerte.empty else "Aucune alerte")

else:
    st.error("Données inaccessibles.")
