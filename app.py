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
        # Tenta ler do novo segredo 'textkey'
        info_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(info_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error("Erro crítico na chave do Banco de Dados. Verifique os Secrets.")
        st.stop()

db = firestore.client()

# 2. CONFIGURAÇÃO DA IA
genai.configure(api_key="AIzaSyCSCgcZYaU8wvCSeZgSlTPgIwJjcjOUjNo")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- FUNÇÕES DE DADOS ---
def carregar_dados(colecao):
    try:
        docs = db.collection(colecao).stream()
        return pd.DataFrame([dict(d.to_dict(), id=d.id) for d in docs])
    except:
        return pd.DataFrame()

# Carregamento inicial
df_renda = carregar_dados('rendas')

# --- INTERFACE ---
st.title("🏦 Welton Bank - Gestão Profissional")

st.sidebar.success("Conectado ao Banco de Dados!")
menu = st.sidebar.radio("Navegação", ["📊 Visão Geral", "💸 Lançamentos", "💳 Cartões", "📄 Boletos"])

if menu == "📊 Visão Geral":
    st.subheader("Resumo do Mês")
    if not df_renda.empty:
        total_r = df_renda['valor'].sum()
        st.metric("Total de Receitas", f"R$ {total_r:,.2f}")
    else:
        st.info("Nenhum dado encontrado. Comece fazendo um lançamento!")
    
    if st.button("🤖 Gerar Dica da IA"):
        res = model.generate_content("Me dê uma dica financeira curta e profissional.")
        st.write(res.text)

# O restante das funcionalidades aparecerá assim que a conexão estabilizar
