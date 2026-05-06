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

# 2. CONFIGURAÇÃO DA IA (Ajustada para máxima compatibilidade)
genai.configure(api_key="AIzaSyCPaXbZeFitBZLIjtZMpwheHAdHMq7UYlc")
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Orçamento Estilo Welton", layout="wide", page_icon="📊")

st.title("📑 Orçamento Pessoal Mensal")
st.markdown("---")

# 3. FUNÇÃO PARA SALVAR
def salvar_transacao(desc, valor_p, valor_r, cat, tipo):
    db.collection('orcamento_welton').document().set({
        'data': datetime.now(),
        'descricao': desc.upper(),
        'planejado': float(valor_p),
        'real': float(valor_r),
        'categoria': cat,
        'tipo': tipo
    })

# --- SIDEBAR ---
with st.sidebar:
    st.header("➕ Novo Lançamento")
    tipo = st.selectbox("Tipo", ["Gasto", "Receita"])
    cat = st.selectbox("Categoria", [
        "Casa (Aluguel/Luz)", "Transporte", "Alimentação", 
        "Lazer/Entretenimento", "Saúde", "Educação", "Salário", "Investimentos"
    ])
    desc = st.text_input("Descrição")
    
    col_p, col_r = st.columns(2)
    val_p = col_p.number_input("Planejado (R$)", min_value=0.0)
    val_r = col_r.number_input("Real (R$)", min_value=0.0)
    
    if st.button("📊 Registrar"):
        if desc:
            salvar_transacao(desc, val_p, val_r, cat, tipo)
            st.success("Registrado!")
            st.rerun()

# --- PROCESSAMENTO DOS DADOS ---
docs = db.collection('orcamento_welton').order_by('data', direction=firestore.Query.DESCENDING).stream()
dados = [d.to_dict() for d in docs]

if dados:
    df = pd.DataFrame(dados)
    
    # Totais
    receita_total = df[df['tipo'] == "Receita"]['real'].sum()
    gasto_p = df[df['tipo'] == "Gasto"]['planejado'].sum()
    gasto_r = df[df['tipo'] == "Gasto"]['real'].sum()
    saldo = receita_total - gasto_r

    # Dashboard
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Renda Real", f"R$ {receita_total:,.2f}")
    c2.metric("Planejado", f"R$ {gasto_p:,.2f}")
    c3.metric("Gasto Real", f"R$ {gasto_r:,.2f}")
    c4.metric("Saldo Final", f"R$ {saldo:,.2f}")

    st.subheader("📋 Detalhes")
    df['Diferença'] = df['planejado'] - df['real']
    st.dataframe(df[['categoria', 'descricao', 'planejado', 'real', 'Diferença']], use_container_width=True, hide_index=True)

    # --- IA ---
    st.markdown("---")
    st.subheader("💡 Consultoria Financeira")
    if st.button("🤖 Pedir Conselho à IA"):
        resumo = df[df['tipo'] == "Gasto"].groupby('categoria')[['planejado', 'real']].sum().to_string()
        prompt = f"Como um contador, analise meu orçamento: {resumo}. Minha renda é {receita_total}. Me dê 3 dicas práticas."
        
        with st.spinner('Analisando...'):
            try:
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error("O serviço de IA está reiniciando. Tente novamente em 15 segundos.")
else:
    st.info("Cadastre algo para começar!")
