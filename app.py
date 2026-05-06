import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Controle Financeiro Total - Welton", layout="wide", page_icon="🏦")

# 1. CONEXÃO COM O BANCO DE DADOS
if not firebase_admin._apps:
    cred = credentials.Certificate('chave.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. CONFIGURAÇÃO DA IA
genai.configure(api_key="AIzaSyCPaXbZeFitBZLIjtZMpwheHAdHMq7UYlc")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- FUNÇÕES DE AJUDA ---
def salvar_dados(colecao, dados):
    db.collection(colecao).document().set(dados)

def excluir_dados(colecao, doc_id):
    db.collection(colecao).document(doc_id).delete()
    st.rerun()

# --- INTERFACE LATERAL (ENTRADAS MANUAIS DETALHADAS) ---
with st.sidebar:
    st.header("🎛️ Painel de Lançamentos")
    
    aba_input = st.tabs(["💰 Renda/Alimentação", "💳 Cartões", "📄 Boletos/Contas"])
    
    with aba_input[0]:
        st.subheader("Entradas e Reservas")
        salario = st.number_input("Salário Líquido Mensal", min_value=0.0)
        reserva_food = st.number_input("Reserva para Alimentação/Foods", min_value=0.0)
        if st.button("Definir Renda e Foods"):
            db.collection('configuracoes').document('financeiro').set({
                'salario': salario,
                'reserva_food': reserva_food
            })
            st.success("Valores atualizados!")

    with aba_input[1]:
        st.subheader("Faturas de Cartão")
        c_nome = st.text_input("Nome do Cartão (ex: Nubank)")
        c_limite = st.number_input("Limite Total do Cartão", min_value=0.0)
        c_fatura = st.number_input("Valor da Fatura Atual", min_value=0.0)
        c_parcelas = st.number_input("Parcelas restantes (0 se não houver)", min_value=0)
        if st.button("Registrar Cartão"):
            salvar_dados('cartoes', {
                'nome': c_nome.upper(), 
                'limite': c_limite, 
                'fatura': c_fatura,
                'parcelas_faltam': c_parcelas,
                'data': datetime.now()
            })
            st.rerun()

    with aba_input[2]:
        st.subheader("Boletos e Empréstimos")
        b_cat = st.selectbox("Tipo de Conta", ["Luz", "Internet", "Faculdade", "Seguro de Vida", "Empréstimo", "Outros"])
        b_valor = st.number_input("Valor Mensal", min_value=0.0)
        b_parcelas = st.number_input("Quantas parcelas faltam?", min_value=0)
        b_venc = st.date_input("Data de Vencimento")
        if st.button("Registrar Conta"):
            salvar_dados('boletos', {
                'categoria': b_cat, 
                'valor': b_valor, 
                'parcelas_faltam': b_parcelas,
                'vencimento': str(b_venc)
            })
            st.rerun()

# --- RECUPERAÇÃO DE DADOS ---
res_config = db.collection('configuracoes').document('financeiro').get()
config_dict = res_config.to_dict() if res_config.exists else {'salario': 0.0, 'reserva_food': 0.0}

df_cartoes = pd.DataFrame([dict(d.to_dict(), id=d.id) for d in db.collection('cartoes').stream()])
df_boletos = pd.DataFrame([dict(d.to_dict(), id=d.id) for d in db.collection('boletos').stream()])

# --- CÁLCULOS TOTAIS ---
total_faturas = df_cartoes['fatura'].sum() if not df_cartoes.empty else 0.0
total_boletos = df_boletos['valor'].sum() if not df_boletos.empty else 0.0
gastos_totais = total_faturas + total_boletos + config_dict['reserva_food']
poupanca_mes = config_dict['salario'] - gastos_totais

# --- DASHBOARD PRINCIPAL ---
st.title("📑 Controle Financeiro 360º - Welton")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Salário Líquido", f"R$ {config_dict['salario']:,.2f}")
c2.metric("Gastos Fixos + Foods", f"R$ {total_boletos + config_dict['reserva_food']:,.2f}")
c3.metric("Faturas de Cartões", f"R$ {total_faturas:,.2f}")
# Capacidade de Poupança
st_cor = "normal" if poupanca_mes > 0 else "inverse"
c4.metric("CAPACIDADE DE GUARDAR", f"R$ {poupanca_mes:,.2f}", delta=f"{poupanca_mes:,.2f}", delta_color=st_cor)

st.markdown("---")

# --- LISTAGENS E PARCELAMENTOS ---
col_cartao, col_boleto = st.columns(2)

with col_cartao:
    st.subheader("💳 Faturas e Limites")
    if not df_cartoes.empty:
        for i, row in df_cartoes.iterrows():
            uso = (row['fatura'] / row['limite']) * 100 if row['limite'] > 0 else 0
            with st.expander(f"CARTÃO {row['nome']} - Fatura R$ {row['fatura']:.2f}"):
                st.write(f"**Disponível:** R$ {row['limite'] - row['fatura']:.2f}")
                st.write(f"**Parcelas Restantes:** {row['parcelas_faltam']}")
                st.progress(min(uso/100, 1.0))
                if st.button("Apagar", key=f"del_c_{row['id']}"): excluir_dados('cartoes', row['id'])
    else: st.write("Sem faturas registradas.")

with col_boleto:
    st.subheader("📄 Boletos e Parcelamentos")
    if not df_boletos.empty:
        for i, row in df_boletos.iterrows():
            with st.expander(f"{row['categoria']} - R$ {row['valor']:.2f}"):
                st.write(f"**Vencimento:** {row['vencimento']}")
                st.write(f"**Parcelas Faltando:** {row['parcelas_faltam']}")
                if st.button("Apagar", key=f"del_b_{row['id']}"): excluir_dados('boletos', row['id'])
    else: st.write("Sem boletos registrados.")

# --- ANÁLISE IA ---
st.markdown("---")
if st.button("🤖 Gerar Análise de Controle Total"):
    prompt = f"Renda {config_dict['salario']}. Boletos {total_boletos}. Cartões {total_faturas}. Reserva Food {config_dict['reserva_food']}. Poupando {poupanca_mes}. Analise minha saúde financeira."
    res = model.generate_content(prompt)
    st.info(res.text)
