import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import json
import google.generativeai as genai
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Welton VIP Bank", layout="wide", page_icon="🏦")

# --- CONEXÃO BANCO DE DADOS (COM PROTEÇÃO DE CACHE) ---
@st.cache_resource
def iniciar_banco():
    if not firebase_admin._apps:
        try:
            key_dict = json.loads(st.secrets["textkey"])
            cred = credentials.Certificate(key_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as e:
            return None
    return firebase_admin.get_app()

app = iniciar_banco()
if app:
    db = firestore.client()
else:
    st.error("Erro nos Secrets. Verifique a chave 'textkey'.")
    st.stop()

# --- CONFIGURAÇÃO DA IA ---
genai.configure(api_key="AIzaSyCSCgcZYaU8wvCSeZgSlTPgIwJjcjOUjNo")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- FUNÇÕES DE CARREGAMENTO ---
def puxar_dados(nome_colecao):
    try:
        docs = db.collection(nome_colecao).stream()
        return pd.DataFrame([dict(d.to_dict(), id=d.id) for d in docs])
    except:
        return pd.DataFrame()

def salvar_dados(colecao, objeto):
    db.collection(colecao).add(objeto)
    st.success("Registrado com sucesso!")
    st.rerun()

# --- MENU LATERAL ---
st.sidebar.title("🏦 Welton VIP")
aba = st.sidebar.radio("Escolha uma área:", ["📊 Dashboard", "💳 Cartões", "📄 Boletos", "📈 Investimentos"])

# --- PÁGINA: DASHBOARD ---
if aba == "📊 Dashboard":
    st.header("📊 Resumo Financeiro Profissional")
    df_r = puxar_dados('rendas')
    df_b = puxar_dados('boletos_vip')
    df_c = puxar_dados('cartoes_vip')
    
    total_r = df_r['valor'].sum() if not df_r.empty else 0.0
    total_b = df_b['valor'].sum() if not df_b.empty else 0.0
    total_c = df_c['fatura'].sum() if not df_c.empty else 0.0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Minha Renda", f"R$ {total_r:,.2f}")
    c2.metric("Total Contas/Cartões", f"R$ {total_b + total_c:,.2f}")
    c3.metric("Saldo Livre", f"R$ {total_r - (total_b + total_c):,.2f}")

    st.divider()
    if st.button("🤖 Consultar Gerente IA"):
        with st.spinner("Analisando..."):
            res = model.generate_content(f"Renda {total_r}, Gastos {total_b+total_c}. Dê um conselho curto.")
            st.info(res.text)

# --- PÁGINA: CARTÕES ---
elif aba == "💳 Cartões":
    st.header("💳 Gestão de Cartões de Crédito")
    with st.expander("➕ Novo Cartão"):
        nome = st.text_input("Nome do Cartão")
        limite = st.number_input("Limite Total", min_value=0.0)
        fatura = st.number_input("Fatura Atual", min_value=0.0)
        if st.button("Salvar Cartão"):
            salvar_dados('cartoes_vip', {'nome': nome.upper(), 'limite': limite, 'fatura': fatura})

    df = puxar_dados('cartoes_vip')
    if not df.empty:
        st.dataframe(df[['nome', 'limite', 'fatura']], use_container_width=True)

# --- PÁGINA: BOLETOS ---
elif aba == "📄 Boletos":
    st.header("📄 Contas Fixas e Boletos")
    with st.expander("➕ Nova Conta"):
        nome_b = st.text_input("Descrição")
        valor_b = st.number_input("Valor", min_value=0.0)
        if st.button("Salvar Boleto"):
            salvar_dados('boletos_vip', {'nome': nome_b.upper(), 'valor': valor_b})
            
    df = puxar_dados('boletos_vip')
    if not df.empty:
        st.table(df[['nome', 'valor']])

# --- PÁGINA: INVESTIMENTOS ---
elif aba == "📈 Investimentos":
    st.header("📈 Meus Investimentos")
    with st.expander("➕ Registrar Aplicação"):
        onde = st.text_input("Onde? (CDB, Ações, etc)")
        valor_i = st.number_input("Valor Investido", min_value=0.0)
        if st.button("Salvar Investimento"):
            salvar_dados('investimentos', {'nome': onde.upper(), 'valor': valor_i})
            
    df = puxar_dados('investimentos')
    if not df.empty:
        st.dataframe(df[['nome', 'valor']], use_container_width=True)
