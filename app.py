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

st.set_page_config(page_title="Orçamento Mensal Welton", layout="wide")

# --- CABEÇALHO ESTILO EXCEL ---
st.title("📊 Orçamento Pessoal Mensal")
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

# --- BARRA LATERAL PARA ENTRADA ---
with st.sidebar:
    st.header("➕ Novo Lançamento")
    tipo = st.selectbox("Tipo", ["Gasto", "Receita"])
    cat = st.selectbox("Categoria (Grupo)", [
        "Moradia", "Entretenimento", "Transporte", 
        "Alimentação", "Saúde", "Educação", "Seguro", "Investimentos", "Renda"
    ])
    desc = st.text_input("Descrição (Ex: Aluguel, Cinema)")
    col_p, col_r = st.columns(2)
    val_p = col_p.number_input("Estimado (R$)", min_value=0.0)
    val_r = col_r.number_input("Real (R$)", min_value=0.0)
    
    if st.button("Gravar na Planilha"):
        if desc:
            salvar_transacao(desc, val_p, val_r, cat, tipo)
            st.success("Gravado!")
            st.rerun()

# --- BUSCA DE DADOS ---
docs = db.collection('orcamento_welton').order_by('data', direction=firestore.Query.DESCENDING).stream()
dados = [d.to_dict() for d in docs]

if dados:
    df = pd.DataFrame(dados)
    
    # Cálculos Totais (Igual ao Topo da sua Planilha)
    renda_total = df[df['tipo'] == "Receita"]['real'].sum()
    gasto_p_total = df[df['tipo'] == "Gasto"]['planejado'].sum()
    gasto_r_total = df[df['tipo'] == "Gasto"]['real'].sum()
    
    saldo_previsto = renda_total - gasto_p_total
    saldo_real = renda_total - gasto_r_total
    diferenca_total = saldo_real - saldo_previsto

    # --- RESUMO FINANCEIRO (DASHBOARD) ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo Previsto", f"R$ {saldo_previsto:,.2f}")
    c2.metric("Saldo Real", f"R$ {saldo_real:,.2f}")
    c3.metric("Diferença Total", f"R$ {diferenca_total:,.2f}", delta=f"{diferenca_total:,.2f}")

    st.markdown("---")

    # --- LAYOUT DE TABELAS POR GRUPO (IGUAL AO EXCEL) ---
    categorias = ["Moradia", "Entretenimento", "Transporte", "Alimentação", "Saúde", "Educação", "Investimentos"]
    
    # Criamos colunas para colocar as tabelas lado a lado
    cols = st.columns(2)
    
    for i, categoria in enumerate(categorias):
        target_col = cols[i % 2] # Alterna entre coluna 1 e 2
        
        with target_col:
            st.subheader(f"📍 {categoria}")
            df_cat = df[df['categoria'] == categoria].copy()
            
            if not df_cat.empty:
                df_cat['Diferença'] = df_cat['planejado'] - df_cat['real']
                st.dataframe(
                    df_cat[['descricao', 'planejado', 'real', 'Diferença']], 
                    hide_index=True, 
                    use_container_width=True
                )
                
                # Subtotal por categoria
                sub_p = df_cat['planejado'].sum()
                sub_r = df_cat['real'].sum()
                st.caption(f"**Subtotal {categoria}:** Planejado R$ {sub_p:.2f} | Real R$ {sub_r:.2f}")
            else:
                st.write("*Nenhum lançamento*")
            st.write("") # Espaçamento

    # --- CONSULTORIA IA ---
    st.markdown("---")
    if st.button("🤖 Analisar como Contador"):
        resumo = df[df['tipo'] == "Gasto"].groupby('categoria')[['planejado', 'real']].sum().to_string()
        prompt = f"Analise meu orçamento estilo planilha: {resumo}. Renda: {renda_total}. Dê 3 dicas para o saldo real subir."
        with st.spinner('Lendo tabelas...'):
            try:
                res = model.generate_content(prompt)
                st.info(res.text)
            except:
                st.error("Erro na IA. Tente de novo.")
else:
    st.info("Sua planilha está vazia! Adicione o primeiro item na lateral.")
