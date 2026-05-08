import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Welton Bank", layout="wide", page_icon="🏦")

# 1. CONEXÃO SEGURA COM O FIREBASE
if not firebase_admin._apps:
    try:
        # Puxa os dados direto do cofre do Streamlit
        info_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error("Erro na chave do Banco de Dados. Verifique os Secrets.")
        st.stop()

db = firestore.client()

# 2. CONFIGURAÇÃO DA IA
genai.configure(api_key="AIzaSyCSCgcZYaU8wvCSeZgSlTPgIwJjcjOUjNo")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- FUNÇÕES DE DADOS ---
def carregar_dados(colecao):
    docs = db.collection(colecao).stream()
    return pd.DataFrame([dict(d.to_dict(), id=d.id) for d in docs])

# Tentativa de carregar dados com proteção contra erro de conexão
try:
    df_renda = carregar_dados('rendas')
    df_gastos = carregar_dados('gastos_diarios')
    df_cartoes = carregar_dados('cartoes_vip')
    df_boletos = carregar_dados('boletos_vip')
except:
    st.warning("⚠️ Aguardando conexão com o banco de dados...")
    st.stop()

# --- INTERFACE ---
st.title("🏦 Welton Bank - Gestão Profissional")

menu = st.sidebar.radio("Navegação", ["Visão Geral", "Lançamentos", "Cartões", "Boletos"])

if menu == "Visão Geral":
    st.subheader("📊 Resumo do Mês")
    # Cálculos simplificados para teste inicial
    total_r = df_renda['valor'].sum() if not df_renda.empty else 0.0
    st.metric("Total de Rendas", f"R$ {total_r:,.2f}")
    
    if st.button("🤖 Pedir Dica para IA"):
        res = model.generate_content("Me dê uma dica financeira curta.")
        st.info(res.text)

# O restante do código de lançamentos pode ser adicionado assim que este teste abrir!
