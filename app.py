import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# 1. CONEXÃO COM O BANCO DE DADOS
if not firebase_admin._apps:
    cred = credentials.Certificate('chave.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. CONFIGURAÇÃO DA IA
genai.configure(api_key="AIzaSyCPaXbZeFitBZLIjtZMpwheHAdHMq7UYlc")
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Contador Welton - VIP", layout="wide")

# --- ESTILIZAÇÃO ---
st.title("🏦 Sistema de Gestão Financeira Welton")
st.markdown("---")

# 3. FUNÇÕES DE BANCO DE DADOS
def salvar_item(colecao, dados):
    db.collection(colecao).document().set(dados)

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("⚙️ Lançamentos")
    menu = st.radio("O que deseja registrar?", ["Salário/Receita", "Boleto/Conta Fixa", "Gasto no Cartão", "Configurar Cartão"])

    if menu == "Salário/Receita":
        val = st.number_input("Valor Líquido (R$)", min_value=0.0)
        if st.button("Registrar Salário"):
            salvar_item('financas_welton', {'tipo': 'Receita', 'valor': val, 'data': datetime.now(), 'cat': 'Salário'})
            st.success("Salário atualizado!")

    elif menu == "Boleto/Conta Fixa":
        desc = st.text_input("Descrição do Boleto")
        val = st.number_input("Valor (R$)", min_value=0.0)
        venc = st.date_input("Vencimento")
        if st.button("Salvar Boleto"):
            salvar_item('financas_welton', {'tipo': 'Boleto', 'desc': desc, 'valor': val, 'venc': str(venc), 'status': 'Pendente'})
            st.rerun()

    elif menu == "Gasto no Cartão":
        cartao = st.selectbox("Selecione o Cartão", ["Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5"])
        desc = st.text_input("O que comprou?")
        val = st.number_input("Valor da Compra (R$)", min_value=0.0)
        if st.button("Registrar Compra"):
            salvar_item('financas_welton', {'tipo': 'Gasto_Cartao', 'cartao': cartao, 'desc': desc, 'valor': val, 'data': datetime.now()})
            st.rerun()

# --- BUSCA DE DADOS ---
docs = db.collection('financas_welton').stream()
dados = [d.to_dict() for d in docs]
df = pd.DataFrame(dados) if dados else pd.DataFrame()

if not df.empty:
    # --- CÁLCULOS GERAIS ---
    receita = df[df['tipo'] == 'Receita']['valor'].sum()
    boletos = df[df['tipo'] == 'Boleto']['valor'].sum()
    gastos_cartao = df[df['tipo'] == 'Gasto_Cartao']['valor'].sum()
    
    orcamento_livre = receita - boletos - gastos_cartao

    # --- DASHBOARD PRINCIPAL ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Salário Líquido", f"R$ {receita:,.2f}")
    c2.metric("Total em Boletos", f"R$ {boletos:,.2f}", delta_color="inverse")
    c3.metric("Gastos em Cartões", f"R$ {gastos_cartao:,.2f}")
    c4.metric("ORÇAMENTO DISPONÍVEL", f"R$ {orcamento_livre:,.2f}", delta="Pode gastar" if orcamento_livre > 0 else "Estourado")

    st.markdown("---")

    # --- SEÇÃO DE CARTÕES (GRID) ---
    st.subheader("💳 Meus Cartões de Crédito")
    cols_cartoes = st.columns(5)
    for i in range(1, 6):
        nome_c = f"Cartão {i}"
        with cols_cartoes[i-1]:
            gasto_c = df[(df['tipo'] == 'Gasto_Cartao') & (df['cartao'] == nome_c)]['valor'].sum()
            st.info(f"**{nome_c}**")
            st.write(f"Gasto: R$ {gasto_c:,.2f}")
            # Simulando um limite de 2000 por cartão para exemplo
            progresso = min(gasto_c / 2000, 1.0) if gasto_c > 0 else 0.0
            st.progress(progresso)

    # --- TABELAS ESTILO EXCEL ---
    col_esq, col_dir = st.columns(2)
    
    with col_esq:
        st.subheader("📑 Boletos Pendentes")
        df_bol = df[df['tipo'] == 'Boleto']
        if not df_bol.empty:
            st.table(df_bol[['desc', 'valor', 'venc']])
            
    with col_dir:
        st.subheader("🛒 Últimas Compras (Cartão)")
        df_compras = df[df['tipo'] == 'Gasto_Cartao']
        if not df_compras.empty:
            st.dataframe(df_compras[['cartao', 'desc', 'valor']], hide_index=True)

    # --- IA ANALISTA ---
    st.markdown("---")
    if st.button("🤖 Gerar Consultoria do Mês"):
        prompt = f"""
        Sou o Welton. Minha renda é {receita}. 
        Tenho {boletos} em boletos e gastei {gastos_cartao} nos cartões.
        Sobrou {orcamento_livre}. 
        Me dê um plano real para eu não usar mais do que 30% da minha renda em cartões.
        """
        with st.spinner("Analisando seus 5 cartões..."):
            res = model.generate_content(prompt)
            st.write(res.text)

else:
    st.warning("Aguardando os primeiros lançamentos para montar seu painel.")
