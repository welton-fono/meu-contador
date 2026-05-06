import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime

# 1. CONEXÃO COM O BANCO DE DADOS
if not firebase_admin._apps:
    # O arquivo chave.json deve estar na mesma pasta!
    cred = credentials.Certificate('chave.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Meu Contador IA", layout="wide")
st.title("🤖 Meu Assistente Financeiro")

# 2. FUNÇÃO PARA SALVAR NO FIREBASE
def salvar_gasto(descricao, valor, categoria, tipo):
    doc_ref = db.collection('transacoes').document()
    doc_ref.set({
        'data': datetime.now(),
        'descricao': descricao,
        'valor': valor,
        'categoria': categoria,
        'tipo': tipo
    })

# 3. INTERFACE DE ENTRADA
with st.sidebar:
    st.header("Novo Lançamento")
    desc = st.text_input("O que você comprou/recebeu?")
    valor = st.number_input("Valor (R$)", min_value=0.0)
    tipo = st.selectbox("Tipo", ["Gasto", "Receita"])
    cat = st.selectbox("Categoria", ["Dívida", "Alimentação", "Lazer", "Investimento", "Salário"])
    
    if st.button("Registrar no Banco de Dados"):
        valor_final = -valor if tipo == "Gasto" else valor
        salvar_gasto(desc, valor_final, cat, tipo)
        st.success("Salvo com sucesso!")

# 4. BUSCAR DADOS DO FIREBASE E MOSTRAR
st.subheader("Suas Contas em Tempo Real")
docs = db.collection('transacoes').order_by('data', direction=firestore.Query.DESCENDING).stream()
lista_dados = [d.to_dict() for d in docs]

if lista_dados:
    df = pd.DataFrame(lista_dados)
    # Mostrar Saldo Simples
    total = df['valor'].sum()
    st.metric("Saldo Geral", f"R$ {total:,.2f}")
    st.table(df[['data', 'descricao', 'valor', 'categoria']])
else:
    st.info("Nenhum dado encontrado ainda. Comece registrando algo na lateral!")
