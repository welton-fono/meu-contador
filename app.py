import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# 1. CONEXÃO COM O BANCO DE DADOS (FIREBASE)
if not firebase_admin._apps:
    # O arquivo chave.json deve estar no seu GitHub também!
    cred = credentials.Certificate('chave.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. CONFIGURAÇÃO DA INTELIGÊNCIA ARTIFICIAL (GEMINI)
genai.configure(api_key="AIzaSyCPaXbZeFitBZLIjtZMpwheHAdHMq7UYlc")
model = genai.GenerativeModel('gemini-pro')

st.set_page_config(page_title="Contador IA", layout="wide", page_icon="💰")
st.title("🤖 Meu Assistente Financeiro Inteligente")

# 3. FUNÇÃO PARA SALVAR NO BANCO
def salvar_gasto(descricao, valor, categoria, tipo):
    doc_ref = db.collection('transacoes').document()
    doc_ref.set({
        'data': datetime.now(),
        'descricao': descricao,
        'valor': valor,
        'categoria': categoria,
        'tipo': tipo
    })

# --- INTERFACE LATERAL (ENTRADA DE DADOS) ---
with st.sidebar:
    st.header("📋 Novo Lançamento")
    desc = st.text_input("O que você pagou ou recebeu?")
    valor = st.number_input("Valor (R$)", min_value=0.0, step=0.50)
    tipo = st.selectbox("Tipo", ["Gasto", "Receita"])
    cat = st.selectbox("Categoria", ["Dívida", "Alimentação", "Lazer", "Investimento", "Salário", "Saúde", "Outros"])
    
    if st.button("Registrar no Banco de Dados"):
        if desc and valor > 0:
            v_final = -valor if tipo == "Gasto" else valor
            salvar_gasto(desc, v_final, cat, tipo)
            st.success("✅ Registrado com sucesso!")
        else:
            st.warning("Preencha a descrição e o valor!")

# --- PAINEL PRINCIPAL (ANÁLISE E HISTÓRICO) ---
docs = db.collection('transacoes').order_by('data', direction=firestore.Query.DESCENDING).stream()
lista_dados = [d.to_dict() for d in docs]

if lista_dados:
    df = pd.DataFrame(lista_dados)
    
    # Resumo Rápido
    saldo_atual = df['valor'].sum()
    st.metric("Saldo Geral em Conta", f"R$ {saldo_atual:,.2f}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Histórico de Movimentações")
        # Formata a data para ficar mais bonita na tabela
        df['data_formatada'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y %H:%M')
        st.dataframe(df[['data_formatada', 'descricao', 'valor', 'categoria']], use_container_width=True)
    
    with col2:
        st.subheader("💡 Consultoria da IA")
        st.write("Clique abaixo para que a IA analise seu perfil de gastos atual.")
        
        if st.button("🤖 Analisar minhas finanças"):
            # Cria um resumo para a IA entender
            resumo_categorias = df.groupby('categoria')['valor'].sum().to_string()
            
            prompt_ia = f"""
            Aja como um contador e consultor financeiro expert. 
            Meus lançamentos atuais são (valores negativos são gastos, positivos são ganhos):
            {resumo_categorias}
            
            Com base nisso, me dê 3 conselhos curtos e diretos para eu economizar mais, 
            quitar minhas dívidas e começar a investir. Seja motivador!
            """
            
            with st.spinner('A IA está analisando seus números...'):
                try:
                    response = model.generate_content(prompt_ia)
                    st.info(response.text)
                except Exception as e:
                    st.error(f"Erro ao falar com a IA: {e}")
else:
    st.info("👋 Bem-vindo! Comece registrando um gasto ou receita na barra lateral para ativar as análises.")
