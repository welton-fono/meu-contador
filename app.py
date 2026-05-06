import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# 1. CONEXÃO COM O BANCO DE DADOS (FIREBASE)
if not firebase_admin._apps:
    # O arquivo chave.json deve estar na raiz do seu repositório GitHub
    cred = credentials.Certificate('chave.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. CONFIGURAÇÃO DA IA (VERSÃO COM FINAL -LATEST PARA EVITAR ERRO 404)
genai.configure(api_key="AIzaSyCPaXbZeFitBZLIjtZMpwheHAdHMq7UYlc")
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="Orçamento Estilo Welton", layout="wide", page_icon="📊")

# --- ESTILIZAÇÃO DO CABEÇALHO ---
st.title("📑 Orçamento Pessoal Mensal")
st.info("Dica: Para um melhor resultado, registre o valor 'Planejado' e o 'Real' no mesmo lançamento.")
st.markdown("---")

# 3. FUNÇÃO PARA SALVAR TRANSAÇÃO
def salvar_transacao(desc, valor_p, valor_r, cat, tipo):
    db.collection('orcamento_welton').document().set({
        'data': datetime.now(),
        'descricao': desc.upper(),
        'planejado': valor_p,
        'real': valor_r,
        'categoria': cat,
        'tipo': tipo
    })

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("➕ Novo Lançamento")
    tipo = st.selectbox("Tipo de Movimentação", ["Gasto", "Receita"])
    cat = st.selectbox("Categoria", [
        "Casa (Aluguel/Luz)", "Transporte", "Alimentação", 
        "Lazer/Entretenimento", "Saúde", "Educação", "Salário", "Investimentos"
    ])
    desc = st.text_input("Descrição (Ex: Faculdade, Aluguel)")
    
    col_p, col_r = st.columns(2)
    val_p = col_p.number_input("Planejado (R$)", min_value=0.0, step=10.0)
    val_r = col_r.number_input("Real (R$)", min_value=0.0, step=10.0)
    
    if st.button("📊 Registrar no Orçamento"):
        if desc:
            salvar_transacao(desc, val_p, val_r, cat, tipo)
            st.success("✅ Registrado com sucesso!")
            st.rerun() # Atualiza a tela após salvar
        else:
            st.error("⚠️ Digite uma descrição!")

# --- BUSCA E PROCESSAMENTO DE DADOS ---
docs = db.collection('orcamento_welton').order_by('data', direction=firestore.Query.DESCENDING).stream()
dados = [d.to_dict() for d in docs]

if dados:
    df = pd.DataFrame(dados)
    
    # Cálculos Totais (Baseados no seu modelo Excel)
    receita_total = df[df['tipo'] == "Receita"]['real'].sum()
    custo_planejado = df[df['tipo'] == "Gasto"]['planejado'].sum()
    custo_real = df[df['tipo'] == "Gasto"]['real'].sum()
    
    # Saldo Real (Renda menos Custo Real) - Exatamente como no Excel
    saldo_final = receita_total - custo_real
    economia_prevista = custo_planejado - custo_real

    # --- DASHBOARD DE RESUMO ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Renda Mensal Real", f"R$ {receita_total:,.2f}")
    c2.metric("Custo Planejado", f"R$ {custo_planejado:,.2f}")
    c3.metric("Custo Real", f"R$ {custo_real:,.2f}")
    
    # Se saldo for positivo, fica verde. Se negativo, vermelho.
    c4.metric("Saldo Final (Real)", f"R$ {saldo_final:,.2f}", delta=f"Diferença: {economia_prevista:,.2f}")

    st.markdown("### 📋 Detalhamento por Categoria")
    
    # Preparação da Tabela comparativa
    df_tab = df.copy()
    df_tab['Diferença'] = df_tab['planejado'] - df_tab['real']
    
    # Mostra a tabela organizada por data
    st.dataframe(df_tab[['categoria', 'descricao', 'planejado', 'real', 'Diferença']], 
                 use_container_width=True, 
                 hide_index=True)

    # --- CONSULTORIA DA IA ---
    st.markdown("---")
    st.subheader("💡 Consultoria Financeira IA")
    
    if st.button("🤖 Gerar Análise de Performance"):
        # Agrupa os dados para a IA entender o cenário geral
        resumo_ia = df.groupby(['tipo', 'categoria'])[['planejado', 'real']].sum().to_string()
        
        prompt = f"""
        Olá Gemini. Analise meu orçamento mensal como meu contador pessoal.
        Meus dados atuais agrupados são:
        {resumo_ia}
        
        Minha Renda Real total é de R$ {receita_total}.
        Analise onde estou gastando mais do que planejei e me dê 3 passos práticos 
        para eu sair das dívidas e começar a investir. Seja direto e encorajador.
        """
        
        with st.spinner('A IA está revisando suas contas...'):
            try:
                # Agora usando a chamada -latest
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"Erro na conexão com a IA: {e}")
else:
    st.info("Sua planilha está pronta! Registre seus gastos na barra lateral para começar a análise.")
