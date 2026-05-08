import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import json
import google.generativeai as genai
from datetime import datetime

# --- 1. CONFIGURAÇÃO PROFISSIONAL DA PÁGINA ---
st.set_page_config(
    page_title="Welton VIP Bank", 
    layout="wide", 
    page_icon="🏦",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXÃO SEGURA COM O FIREBASE (ANTI-TRAVAMENTO) ---
@st.cache_resource
def iniciar_banco():
    if not firebase_admin._apps:
        try:
            # Lê a chave do campo 'textkey' nos Secrets do Streamlit
            key_dict = json.loads(st.secrets["textkey"])
            cred = credentials.Certificate(key_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro na conexão: {e}")
            return None
    return firebase_admin.get_app()

# Inicializa o app
app_firebase = iniciar_banco()

if app_firebase:
    db = firestore.client()
else:
    st.warning("⚠️ Sistema aguardando configuração dos Secrets no Streamlit Cloud.")
    st.stop()

# --- 3. CONFIGURAÇÃO DA INTELIGÊNCIA ARTIFICIAL (GEMINI) ---
# Usando a sua chave de API que já estava funcional
genai.configure(api_key="AIzaSyCSCgcZYaU8wvCSeZgSlTPgIwJjcjOUjNo")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 4. FUNÇÕES DE SUPORTE (BUSCA E SALVAMENTO) ---
def puxar_dados(nome_colecao):
    try:
        docs = db.collection(nome_colecao).stream()
        lista = [dict(d.to_dict(), id=d.id) for d in docs]
        return pd.DataFrame(lista)
    except:
        return pd.DataFrame()

# --- 5. INTERFACE LATERAL ---
st.sidebar.title("🏦 Welton VIP Bank")
st.sidebar.markdown("---")
aba = st.sidebar.radio(
    "Navegação Principal", 
    ["📊 Dashboard", "💳 Cartões", "📄 Boletos", "📈 Investimentos", "💰 Rendas"]
)

# --- PÁGINA: DASHBOARD ---
if aba == "📊 Dashboard":
    st.header("📊 Painel Financeiro Geral")
    
    # Carrega todos os dados para o resumo
    df_r = puxar_dados('rendas')
    df_b = puxar_dados('boletos_vip')
    df_c = puxar_dados('cartoes_vip')
    
    total_r = df_r['valor'].sum() if not df_r.empty else 0.0
    total_b = df_b['valor'].sum() if not df_b.empty else 0.0
    total_c = df_c['fatura'].sum() if not df_c.empty else 0.0
    
    gastos_totais = total_b + total_c
    saldo_final = total_r - gastos_totais

    # Exibição de Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Minha Renda Total", f"R$ {total_r:,.2f}")
    col2.metric("Total de Gastos", f"R$ {gastos_totais:,.2f}", delta_color="inverse")
    col3.metric("Saldo Livre", f"R$ {saldo_final:,.2f}", delta="Disponível")

    st.markdown("---")
    
    # Consultoria com IA
    st.subheader("🤖 Consultoria do Gerente IA")
    if st.button("Analisar minha saúde financeira"):
        with st.spinner("O Gemini está analisando seus números..."):
            prompt = f"Minha renda é {total_r} e meus gastos são {gastos_totais}. Dê um conselho financeiro curto e motivador."
            try:
                response = model.generate_content(prompt)
                st.info(response.text)
            except:
                st.error("IA temporariamente indisponível.")

# --- PÁGINA: CARTÕES ---
elif aba == "💳 Cartões":
    st.header("💳 Gestão de Cartões de Crédito")
    
    with st.form("novo_cartao", clear_on_submit=True):
        col_a, col_b, col_c = st.columns(3)
        nome_c = col_a.text_input("Nome do Cartão")
        limite_c = col_b.number_input("Limite Total", min_value=0.0)
        fatura_c = col_c.number_input("Fatura Atual", min_value=0.0)
        btn_c = st.form_submit_button("Salvar Cartão")
        
        if btn_c and nome_c:
            db.collection('cartoes_vip').add({
                'nome': nome_c.upper(),
                'limite': limite_c,
                'fatura': fatura_c,
                'data_registro': datetime.now().strftime("%d/%m/%Y")
            })
            st.success(f"Cartão {nome_c} salvo!")
            st.rerun()

    st.subheader("Meus Cartões")
    df_cartoes = puxar_dados('cartoes_vip')
    if not df_cartoes.empty:
        st.dataframe(df_cartoes[['nome', 'limite', 'fatura']], use_container_width=True, hide_index=True)

# --- PÁGINA: BOLETOS ---
elif aba == "📄 Boletos":
    st.header("📄 Contas Fixas e Boletos")
    
    with st.form("novo_boleto", clear_on_submit=True):
        col_x, col_y = st.columns(2)
        desc_b = col_x.text_input("Descrição do Boleto (ex: Luz, Aluguel)")
        valor_b = col_y.number_input("Valor R$", min_value=0.0)
        btn_b = st.form_submit_button("Registrar Conta")
        
        if btn_b and desc_b:
            db.collection('boletos_vip').add({
                'nome': desc_b.upper(),
                'valor': valor_b,
                'pago': False,
                'data': datetime.now().strftime("%d/%m/%Y")
            })
            st.success("Boleto registrado!")
            st.rerun()

    st.subheader("Lista de Boletos")
    df_boletos = puxar_dados('boletos_vip')
    if not df_boletos.empty:
        st.table(df_boletos[['nome', 'valor']])

# --- PÁGINA: INVESTIMENTOS ---
elif aba == "📈 Investimentos":
    st.header("📈 Carteira de Investimentos")
    with st.form("novo_invest", clear_on_submit=True):
        tipo = st.text_input("Onde investiu? (CDB, Ações, NuBank)")
        v_inv = st.number_input("Valor Aplicado", min_value=0.0)
        if st.form_submit_button("Salvar Investimento"):
            db.collection('investimentos').add({
                'nome': tipo.upper(),
                'valor': v_inv
            })
            st.rerun()

    df_inv = puxar_dados('investimentos')
    if not df_inv.empty:
        st.dataframe(df_inv[['nome', 'valor']], use_container_width=True)

# --- PÁGINA: RENDAS ---
elif aba == "💰 Rendas":
    st.header("💰 Minhas Fontes de Renda")
    with st.form("nova_renda", clear_on_submit=True):
        origem = st.text_input("Origem (Salário, Extra, etc)")
        v_renda = st.number_input("Valor Recebido", min_value=0.0)
        if st.form_submit_button("Salvar Renda"):
            db.collection('rendas').add({
                'origem': origem.upper(),
                'valor': v_renda
            })
            st.rerun()
            
    df_rendas = puxar_dados('rendas')
    if not df_rendas.empty:
        st.table(df_rendas[['origem', 'valor']])
