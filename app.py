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
            # Puxa a chave do cofre 'textkey' que vamos configurar no Streamlit
            key_dict = json.loads(st.secrets["textkey"])
            cred = credentials.Certificate(key_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro na chave do Banco de Dados: {e}")
            return None
    return firebase_admin.get_app()

app = iniciar_banco()

if app:
    db = firestore.client()
else:
    st.warning("⚠️ Aguardando configuração correta dos Secrets...")
    st.stop()

# --- CONFIGURAÇÃO DA INTELIGÊNCIA ARTIFICIAL ---
genai.configure(api_key="AIzaSyCSCgcZYaU8wvCSeZgSlTPgIwJjcjOUjNo")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- FUNÇÕES DE CARREGAMENTO DE DADOS ---
def puxar_dados(nome_colecao):
    try:
        docs = db.collection(nome_colecao).stream()
        lista_dados = [dict(d.to_dict(), id=d.id) for d in docs]
        return pd.DataFrame(lista_dados)
    except:
        return pd.DataFrame()

# --- MENU LATERAL DE NAVEGAÇÃO ---
st.sidebar.title("🏦 Welton VIP")
aba = st.sidebar.radio("Escolha uma área:", ["📊 Dashboard", "💳 Cartões", "📄 Boletos", "📈 Investimentos"])

# --- PÁGINA: DASHBOARD ---
if aba == "📊 Dashboard":
    st.header("📊 Painel Financeiro Profissional")
    
    # Puxar dados de forma segura
    df_r = puxar_dados('rendas')
    df_b = puxar_dados('boletos_vip')
    
    col1, col2, col3 = st.columns(3)
    
    total_receita = df_r['valor'].sum() if not df_r.empty else 0.0
    total_boletos = df_b['valor'].sum() if not df_b.empty else 0.0
    saldo = total_receita - total_boletos
    
    col1.metric("Minha Renda", f"R$ {total_receita:,.2f}")
    col2.metric("Total em Boletos", f"R$ {total_boletos:,.2f}")
    col3.metric("Saldo Disponível", f"R$ {saldo:,.2f}", delta="Saúde Financeira")

    st.markdown("---")
    if st.button("🤖 Pedir Consultoria ao Gerente IA"):
        with st.spinner("Analisando seus números..."):
            prompt = f"Tenho R$ {total_receita} de renda e R$ {total_boletos} de contas fixas. Me dê uma dica de investimento ou economia curta e profissional."
            try:
                res = model.generate_content(prompt)
                st.info(res.text)
            except:
                st.write("IA ocupada. Tente novamente em 10 segundos.")

# --- PÁGINA: BOLETOS ---
elif aba == "📄 Boletos":
    st.header("📄 Gestão de Contas e Boletos")
    
    with st.expander("➕ Cadastrar Nova Conta (Luz, Internet, etc.)", expanded=True):
        nome_conta = st.text_input("Descrição da Conta")
        valor_conta = st.number_input("Valor da Parcela (R$)", min_value=0.0, step=10.0)
        vencimento = st.date_input("Data de Vencimento")
        
        if st.button("Salvar Conta no Banco"):
            if nome_conta:
                db.collection('boletos_vip').add({
                    'nome': nome_conta.upper(),
                    'valor': valor_conta,
                    'vencimento': str(vencimento)
                })
                st.success(f"Conta '{nome_conta}' salva com sucesso!")
                st.rerun()
            else:
                st.error("Por favor, preencha o nome da conta.")

    st.subheader("📋 Contas Cadastradas")
    df_lista = puxar_dados('boletos_vip')
    if not df_lista.empty:
        st.dataframe(df_lista[['nome', 'valor', 'vencimento']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma conta cadastrada ainda.")
