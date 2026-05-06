import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão Financeira VIP", layout="wide", page_icon="🏦")

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

# --- INTERFACE LATERAL (ENTRADAS MANUAIS) ---
with st.sidebar:
    st.header("🎛️ Painel de Lançamentos")
    
    aba_input = st.tabs(["💰 Renda", "💳 Cartões", "📄 Boletos"])
    
    with aba_input[0]:
        salario = st.number_input("Salário Líquido Mensal", min_value=0.0, format="%.2f")
        if st.button("Definir Salário"):
            # Atualiza o salário (usando um ID fixo para apenas um salário por mês)
            db.collection('configuracoes').document('salario_atual').set({'valor': salario})
            st.success("Salário atualizado!")

    with aba_input[1]:
        st.subheader("Novo Gasto no Cartão")
        c_nome = st.text_input("Nome do Cartão (ex: Nubank)")
        c_limite = st.number_input("Limite Total do Cartão", min_value=0.0)
        c_gasto = st.number_input("Valor da Compra Atual", min_value=0.0)
        if st.button("Registrar no Cartão"):
            salvar_dados('cartoes', {
                'nome': c_nome.upper(), 
                'limite': c_limite, 
                'gasto': c_gasto, 
                'data': datetime.now()
            })
            st.rerun()

    with aba_input[2]:
        st.subheader("Novo Boleto")
        b_nome = st.text_input("Descrição do Boleto")
        b_valor = st.number_input("Valor do Boleto", min_value=0.0)
        b_venc = st.date_input("Data de Vencimento")
        if st.button("Registrar Boleto"):
            salvar_dados('boletos', {
                'nome': b_nome.upper(), 
                'valor': b_valor, 
                'vencimento': str(b_venc)
            })
            st.rerun()

# --- RECUPERAÇÃO DE DADOS ---
# Salário
res_salario = db.collection('configuracoes').document('salario_atual').get()
salario_val = res_salario.to_dict()['valor'] if res_salario.exists else 0.0

# Cartões
cartoes_docs = db.collection('cartoes').stream()
df_cartoes = pd.DataFrame([dict(d.to_dict(), id=d.id) for d in cartoes_docs])

# Boletos
boletos_docs = db.collection('boletos').stream()
df_boletos = pd.DataFrame([dict(d.to_dict(), id=d.id) for d in boletos_docs])

# --- DASHBOARD PRINCIPAL ---
st.title("🏦 Dashboard Financeiro Profissional")

total_boletos = df_boletos['valor'].sum() if not df_boletos.empty else 0.0
total_gastos_cartao = df_cartoes['gasto'].sum() if not df_cartoes.empty else 0.0
orcamento_disponivel = salario_val - total_boletos

col1, col2, col3, col4 = st.columns(4)
col1.metric("Salário Líquido", f"R$ {salario_val:,.2f}")
col2.metric("Total em Boletos", f"R$ {total_boletos:,.2f}")
col3.metric("Gastos em Cartões", f"R$ {total_gastos_cartao:,.2f}")
col4.metric("Orçamento Livre", f"R$ {orcamento_disponivel:,.2f}", 
            delta="Dinheiro na mão" if orcamento_disponivel > 0 else "Alerta!")

st.markdown("---")

# --- GRÁFICOS E ANÁLISES ---
col_graf, col_ia = st.columns([1, 1])

with col_graf:
    st.subheader("📊 Distribuição Sugerida (Rosca)")
    # Dados para o gráfico de rosca baseado na sua sugestão
    dados_rosca = pd.DataFrame({
        "Categoria": ["Essenciais (Boletos)", "Variáveis (Cartões)", "Reserva"],
        "Valor": [total_boletos, total_gastos_cartao, (salario_val * 0.1)]
    })
    st.write("Visualização de gastos atuais em relação à meta (60/30/10)")
    st.bar_chart(dados_rosca.set_index("Categoria"))

with col_ia:
    st.subheader("🤖 Consultoria IA Extraordinária")
    if st.button("Gerar Análise Profissional"):
        prompt = f"""
        Welton tem renda de R$ {salario_val}. 
        Gastos em Boletos: R$ {total_boletos}. 
        Gastos em Cartões: R$ {total_gastos_cartao}.
        Dê um feedback profissional sobre a regra 60/30/10 e como ele pode melhorar o orçamento.
        """
        try:
            res = model.generate_content(prompt)
            st.info(res.text)
        except:
            st.error("IA temporariamente offline. Tente em 10 segundos.")

st.markdown("---")

# --- LISTAGENS DETALHADAS ---
st.subheader("📝 Detalhamento de Contas")
aba_tab1, aba_tab2 = st.tabs(["💳 Cartões de Crédito", "📄 Boletos/Contas"])

with aba_tab1:
    if not df_cartoes.empty:
        for i, row in df_cartoes.iterrows():
            disponivel = row['limite'] - row['gasto']
            porcentagem = (row['gasto'] / row['limite']) * 100 if row['limite'] > 0 else 0
            
            with st.expander(f"CARTÃO: {row['nome']} | Gasto: R$ {row['gasto']:.2f}"):
                c_a, c_b, c_c = st.columns(3)
                c_a.write(f"**Limite Total:** R$ {row['limite']:.2f}")
                c_b.write(f"**Limite Disponível:** R$ {disponivel:.2f}")
                c_c.write(f"**Uso:** {porcentagem:.1f}%")
                st.progress(min(porcentagem/100, 1.0))
                if st.button(f"Excluir Registro {row['id'][:4]}", key=f"del_c_{row['id']}"):
                    excluir_dados('cartoes', row['id'])
    else:
        st.write("Nenhum cartão cadastrado.")

with aba_tab2:
    if not df_boletos.empty:
        # Tabela profissional para boletos
        df_exibir = df_boletos[['nome', 'valor', 'vencimento', 'id']].copy()
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)
        
        # Opção de exclusão individual
        sel_boleto = st.selectbox("Selecione um boleto para remover se necessário:", df_boletos['nome'].unique())
        id_para_deletar = df_boletos[df_boletos['nome'] == sel_boleto]['id'].values[0]
        if st.button("🗑️ Apagar Boleto Selecionado"):
            excluir_dados('boletos', id_para_deletar)
    else:
        st.write("Nenhum boleto pendente.")
