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

# 2. CONFIGURAÇÃO DA IA (GEMINI 1.5 FLASH)
genai.configure(api_key="AIzaSyCPaXbZeFitBZLIjtZMpwheHAdHMq7UYlc")
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Orçamento Estilo Welton", layout="wide", page_icon="📊")

# --- ESTILIZAÇÃO TIPO PLANILHA ---
st.title("📑 Orçamento Pessoal Mensal")
st.markdown("---")

# 3. FUNÇÃO PARA SALVAR
def salvar_transacao(desc, valor_p, valor_r, cat, tipo):
    db.collection('orcamento_welton').document().set({
        'data': datetime.now(),
        'descricao': desc,
        'planejado': valor_p,
        'real': valor_r,
        'categoria': cat,
        'tipo': tipo
    })

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("➕ Novo Lançamento")
    tipo = st.selectbox("Tipo", ["Gasto", "Receita"])
    cat = st.selectbox("Categoria", [
        "Casa (Aluguel/Luz)", "Transporte", "Alimentação", 
        "Lazer/Entretenimento", "Saúde", "Educação", "Salário", "Investimentos"
    ])
    desc = st.text_input("Descrição (Ex: Aluguel, Supermercado)")
    
    col_p, col_r = st.columns(2)
    val_p = col_p.number_input("Planejado (R$)", min_value=0.0)
    val_r = col_r.number_input("Real (R$)", min_value=0.0)
    
    if st.button("📊 Registrar no Orçamento"):
        if desc:
            salvar_transacao(desc, val_p, val_r, cat, tipo)
            st.success("Registrado!")
        else:
            st.error("Coloque uma descrição!")

# --- PROCESSAMENTO DOS DADOS ---
docs = db.collection('orcamento_welton').order_by('data', direction=firestore.Query.DESCENDING).stream()
dados = [d.to_dict() for d in docs]

if dados:
    df = pd.DataFrame(dados)
    
    # Cálculos Totais (Estilo Planilha Welton)
    total_planejado = df[df['tipo'] == "Gasto"]['planejado'].sum()
    total_real = df[df['tipo'] == "Gasto"]['real'].sum()
    diferenca = total_planejado - total_real
    renda_real = df[df['tipo'] == "Receita"]['real'].sum()

    # --- DASHBOARD SUPERIOR ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Renda Real", f"R$ {renda_real:,.2f}")
    c2.metric("Gastos Planejados", f"R$ {total_planejado:,.2f}")
    c3.metric("Gastos Reais", f"R$ {total_real:,.2f}")
    # Delta positivo em gastos é bom (gastou menos que o planejado)
    c4.metric("Diferença (Economia)", f"R$ {diferenca:,.2f}", delta=f"{diferenca:,.2f}")

    st.markdown("### 📋 Detalhamento por Categoria")
    
    # Tabela formatada
    df_exibicao = df.copy()
    df_exibicao['Diferença'] = df_exibicao['planejado'] - df_exibicao['real']
    st.dataframe(df_exibicao[['categoria', 'descricao', 'planejado', 'real', 'Diferença']], use_container_width=True)

    # --- CONSULTORIA DA IA ---
    st.markdown("---")
    st.subheader("💡 Análise do Consultor IA")
    if st.button("🤖 Gerar Relatório de Performance"):
        resumo = df.groupby('categoria')[['planejado', 'real']].sum().to_string()
        prompt = f"""
        Baseado no meu orçamento mensal:
        {resumo}
        Minha renda real foi de R$ {renda_real}.
        Aja como um contador. Analise em quais categorias eu estourou o limite planejado e 
        me dê um plano de ação para sobrar mais dinheiro no próximo mês.
        """
        with st.spinner('Analisando planilhas...'):
            res = model.generate_content(prompt)
            st.info(res.text)
else:
    st.info("Sua planilha está vazia. Comece registrando seus gastos planejados e reais na lateral!")
