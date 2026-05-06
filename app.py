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

st.set_page_config(page_title="Gestão Financeira Welton", layout="wide")

# --- FUNÇÕES DE CONTROLE (SALVAR E APAGAR) ---
def salvar_item(colecao, dados):
    db.collection(colecao).document().set(dados)

def apagar_item(colecao, doc_id):
    db.collection(colecao).document(doc_id).delete()
    st.rerun()

st.title("📑 Meu Contador Pessoal - Welton")
st.markdown("---")

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("⚙️ Painel de Controle")
    opcao = st.selectbox("O que deseja fazer?", ["Resumo Geral", "Gerenciar Cartões", "Gerenciar Boletos", "Registrar Salário"])

    if opcao == "Registrar Salário":
        val = st.number_input("Valor do Salário Líquido", min_value=0.0)
        if st.button("Salvar Salário"):
            salvar_item('financas', {'tipo': 'receita', 'valor': val, 'desc': 'Salário', 'data': datetime.now()})
            st.success("Salário registrado!")

    elif opcao == "Gerenciar Cartões":
        st.subheader("💳 Novo Gasto no Cartão")
        nome_cartao = st.text_input("Nome do Cartão (ex: Nubank, Black)")
        item = st.text_input("O que comprou?")
        valor_c = st.number_input("Valor da Compra", min_value=0.0)
        if st.button("Registrar no Cartão"):
            salvar_item('financas', {'tipo': 'cartao', 'nome': nome_cartao.upper(), 'desc': item, 'valor': valor_c, 'data': datetime.now()})
            st.rerun()

    elif opcao == "Gerenciar Boletos":
        st.subheader("🧾 Novo Boleto/Conta")
        nome_boleto = st.text_input("Nome do Boleto (ex: Aluguel, Internet)")
        valor_b = st.number_input("Valor do Boleto", min_value=0.0)
        venc = st.date_input("Data de Vencimento")
        if st.button("Registrar Boleto"):
            salvar_item('financas', {'tipo': 'boleto', 'nome': nome_boleto.upper(), 'valor': valor_b, 'venc': str(venc)})
            st.rerun()

# --- BUSCA DE DADOS ---
docs = db.collection('financas').stream()
lista_dados = []
for d in docs:
    item = d.to_dict()
    item['id'] = d.id  # Pegamos o ID para poder apagar depois
    lista_dados.append(item)

df = pd.DataFrame(lista_dados) if lista_dados else pd.DataFrame()

if not df.empty:
    # --- CÁLCULOS ---
    salario = df[df['tipo'] == 'receita']['valor'].sum()
    total_boletos = df[df['tipo'] == 'boleto']['valor'].sum()
    total_cartao = df[df['tipo'] == 'cartao']['valor'].sum()
    sobra = salario - total_boletos - total_cartao

    # --- DASHBOARD SUPERIOR ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Salário", f"R$ {salario:,.2f}")
    c2.metric("Total Boletos", f"R$ {total_boletos:,.2f}")
    c3.metric("Total Cartões", f"R$ {total_cartao:,.2f}")
    c4.metric("Disponível", f"R$ {sobra:,.2f}", delta="Saldo Livre")

    st.markdown("---")

    # --- LISTAGEM COM OPÇÃO DE APAGAR ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💳 Gastos por Cartão")
        df_c = df[df['tipo'] == 'cartao']
        if not df_c.empty:
            for _, row in df_c.iterrows():
                with st.expander(f"🛒 {row['nome']} - R$ {row['valor']:.2f}"):
                    st.write(f"Item: {row['desc']}")
                    if st.button(f"🗑️ Apagar {row['id'][:5]}", key=row['id']+"c"):
                        apagar_item('financas', row['id'])
        else: st.write("Nenhum cartão registrado.")

    with col2:
        st.subheader("🧾 Boletos a Pagar")
        df_b = df[df['tipo'] == 'boleto']
        if not df_b.empty:
            for _, row in df_b.iterrows():
                with st.expander(f"📄 {row['nome']} - R$ {row['valor']:.2f}"):
                    st.write(f"Vencimento: {row['venc']}")
                    if st.button(f"🗑️ Apagar {row['id'][:5]}", key=row['id']+"b"):
                        apagar_item('financas', row['id'])
        else: st.write("Nenhum boleto registrado.")

    # --- CONSULTORIA IA ---
    st.markdown("---")
    if st.button("🤖 Analisar Finanças"):
        prompt = f"Welton tem R$ {salario} de renda. Boletos: {total_boletos}. Cartões: {total_cartao}. Dê um conselho curto."
        res = model.generate_content(prompt)
        st.info(res.text)

else:
    st.info("Comece registrando seu salário e gastos na barra lateral!")
