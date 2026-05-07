import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
import json

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Welton Bank - Gestão Total", layout="wide", page_icon="🏦")

# 1. CONEXÃO COM O BANCO DE DADOS (AGORA USANDO SECRETS BLINDADOS)
if not firebase_admin._apps:
    key_dict = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. CONFIGURAÇÃO DA IA COM A CHAVE NOVA
genai.configure(api_key="AIzaSyCSCgcZYaU8wvCSeZgSlTPgIwJjcjOUjNo")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- FUNÇÕES DE BANCO DE DADOS ---
def salvar_dados(colecao, dados):
    db.collection(colecao).document().set(dados)

def excluir_dados(colecao, doc_id):
    db.collection(colecao).document(doc_id).delete()
    st.rerun()

def carregar_dados(colecao):
    docs = db.collection(colecao).stream()
    return pd.DataFrame([dict(d.to_dict(), id=d.id) for d in docs])

# --- CARREGAMENTO GLOBAL DE DADOS ---
df_renda = carregar_dados('rendas')
df_gastos = carregar_dados('gastos_diarios')
df_cartoes = carregar_dados('cartoes_vip')
df_boletos = carregar_dados('boletos_vip')
df_invest = carregar_dados('investimentos')
df_metas = carregar_dados('metas')

# --- CÁLCULOS GERAIS PARA O DASHBOARD ---
total_renda = df_renda['valor'].sum() if not df_renda.empty else 0.0
total_gastos_var = df_gastos['valor'].sum() if not df_gastos.empty else 0.0
total_faturas = df_cartoes['fatura'].sum() if not df_cartoes.empty else 0.0
total_boletos = df_boletos['valor'].sum() if not df_boletos.empty else 0.0

total_investido = df_invest['acumulado'].sum() if not df_invest.empty else 0.0
gastos_fixos = total_boletos
gastos_variaveis = total_faturas + total_gastos_var

custo_total_mes = gastos_fixos + gastos_variaveis
saldo_livre = total_renda - custo_total_mes

hoje = datetime.today().date()

# --- MENU LATERAL (NAVEGAÇÃO TIPO APP BANCÁRIO) ---
st.sidebar.title("🏦 Welton Bank")
menu = st.sidebar.radio("Navegação Principal", [
    "📊 Visão Geral", 
    "💸 Entradas e Despesas", 
    "💳 Meus Cartões", 
    "📄 Boletos e Fixas", 
    "📈 Investimentos e Metas"
])

st.sidebar.markdown("---")
st.sidebar.write(f"**Hoje:** {hoje.strftime('%d/%m/%Y')}")

# ==========================================
# MÓDULO 1: VISÃO GERAL (DASHBOARD)
# ==========================================
if menu == "📊 Visão Geral":
    st.title("📊 Resumo Financeiro do Mês")
    
    # 1. KPIs Principais
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entradas (Salário+)", f"R$ {total_renda:,.2f}")
    c2.metric("Custo Total (Fixos+Var)", f"R$ {custo_total_mes:,.2f}")
    c3.metric("Total Investido", f"R$ {total_investido:,.2f}")
    c4.metric("Disponível para Gastar", f"R$ {saldo_livre:,.2f}", 
              delta="Seguro" if saldo_livre > 0 else "Estourado", delta_color="normal" if saldo_livre > 0 else "inverse")
    
    st.markdown("---")
    
    col_alertas, col_grafico = st.columns([1, 2])
    
    with col_alertas:
        st.subheader("⚠️ Alertas de Vencimento")
        tem_alerta = False
        
        # Alertas de Boletos (Próximos 7 dias)
        if not df_boletos.empty:
            for _, b in df_boletos.iterrows():
                try:
                    venc_date = datetime.strptime(b['vencimento'], "%Y-%m-%d").date()
                    dias_pro_venc = (venc_date - hoje).days
                    if 0 <= dias_pro_venc <= 7:
                        st.warning(f"📄 **{b['nome']}** vence em {dias_pro_venc} dias! (R$ {b['valor']:.2f})")
                        tem_alerta = True
                    elif dias_pro_venc < 0:
                        st.error(f"❌ **{b['nome']}** está ATRASADO! (R$ {b['valor']:.2f})")
                        tem_alerta = True
                except: pass
                
        # Alertas de Cartões
        if not df_cartoes.empty:
            for _, c in df_cartoes.iterrows():
                try:
                    venc_date = datetime.strptime(c['vencimento'], "%Y-%m-%d").date()
                    dias_pro_venc = (venc_date - hoje).days
                    if 0 <= dias_pro_venc <= 7:
                        st.warning(f"💳 Fatura **{c['nome']}** vence em {dias_pro_venc} dias! (R$ {c['fatura']:.2f})")
                        tem_alerta = True
                except: pass
                
        if not tem_alerta:
            st.success("Tudo em dia! Nenhum vencimento próximo.")

    with col_grafico:
        st.subheader("📈 Distribuição de Gastos do Mês")
        if custo_total_mes > 0:
            dados_grafico = pd.DataFrame({
                "Categoria": ["Gastos Fixos (Boletos)", "Gastos Variáveis (Cartões+Dia)"],
                "Valor": [gastos_fixos, gastos_variaveis]
            })
            st.bar_chart(dados_grafico.set_index("Categoria"), color="#1E90FF")
        else:
            st.write("Sem gastos registrados para gerar o gráfico.")

    st.markdown("---")
    st.subheader("🤖 Consultoria Financeira com IA")
    if st.button("Gerar Análise de Fluxo de Caixa"):
        prompt = f"Renda: {total_renda}. Fixos: {gastos_fixos}. Variáveis: {gastos_variaveis}. Investido: {total_investido}. Sobra: {saldo_livre}. Aja como um conselheiro de banco. Me dê 3 dicas práticas baseadas nestes números para eu cortar gastos variáveis e investir mais."
        with st.spinner("O gerente IA está analisando sua conta..."):
            try:
                res = model.generate_content(prompt)
                st.info(res.text)
            except:
                st.error("Erro ao conectar com a IA. Tente em instantes.")

# ==========================================
# MÓDULO 2: ENTRADAS E DESPESAS DIÁRIAS
# ==========================================
elif menu == "💸 Entradas e Despesas":
    st.title("💸 Controle de Fluxo Rápido")
    
    col_in, col_out = st.columns(2)
    
    with col_in:
        st.subheader("Receitas (Salário/Extras)")
        r_nome = st.text_input("Fonte da Renda")
        r_val = st.number_input("Valor Recebido (R$)", min_value=0.0)
        if st.button("Registrar Renda"):
            salvar_dados('rendas', {'nome': r_nome, 'valor': r_val, 'data': str(hoje)})
            st.success("Renda adicionada!")
            st.rerun()
            
        if not df_renda.empty:
            st.dataframe(df_renda[['nome', 'valor', 'data']], hide_index=True)
            sel_r = st.selectbox("Apagar Renda", df_renda['id'])
            if st.button("🗑️ Excluir Renda Selecionada"): excluir_dados('rendas', sel_r)

    with col_out:
        st.subheader("Despesas Variáveis (Pix/Dinheiro)")
        g_cat = st.selectbox("Categoria", ["Alimentação (Foods)", "Transporte/Combustível", "Saúde", "Lazer", "Casa", "Outros"])
        g_nome = st.text_input("Descrição do Gasto")
        g_val = st.number_input("Valor Gasto (R$)", min_value=0.0)
        if st.button("Registrar Despesa"):
            salvar_dados('gastos_diarios', {'categoria': g_cat, 'nome': g_nome, 'valor': g_val, 'data': str(hoje)})
            st.success("Gasto adicionado!")
            st.rerun()

        if not df_gastos.empty:
            st.dataframe(df_gastos[['categoria', 'nome', 'valor']], hide_index=True)
            sel_g = st.selectbox("Apagar Despesa", df_gastos['id'])
            if st.button("🗑️ Excluir Despesa Selecionada"): excluir_dados('gastos_diarios', sel_g)

# ==========================================
# MÓDULO 3: CARTÕES DE CRÉDITO
# ==========================================
elif menu == "💳 Meus Cartões":
    st.title("💳 Gestão de Cartões de Crédito")
    
    with st.expander("➕ Adicionar / Atualizar Cartão", expanded=False):
        c_nome = st.text_input("Nome do Cartão (ex: Nubank, Itaú)")
        c_limite = st.number_input("Limite Total", min_value=0.0)
        c_fatura = st.number_input("Valor Atual da Fatura", min_value=0.0)
        c_venc = st.date_input("Vencimento da Fatura")
        if st.button("Salvar Cartão"):
            salvar_dados('cartoes_vip', {'nome': c_nome.upper(), 'limite': c_limite, 'fatura': c_fatura, 'vencimento': str(c_venc)})
            st.success("Cartão salvo!")
            st.rerun()

    if not df_cartoes.empty:
        for _, row in df_cartoes.iterrows():
            limite_disp = row['limite'] - row['fatura']
            porcentagem = (row['fatura'] / row['limite']) * 100 if row['limite'] > 0 else 0
            
            st.markdown(f"### {row['nome']}")
            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"**Vencimento:** {row['vencimento']}")
            col2.write(f"**Fatura:** R$ {row['fatura']:.2f}")
            col3.write(f"**Limite Disp.:** R$ {limite_disp:.2f}")
            col4.write(f"**Uso:** {porcentagem:.1f}%")
            
            st.progress(min(porcentagem/100, 1.0))
            if st.button("🗑️ Excluir Cartão", key=row['id']): excluir_dados('cartoes_vip', row['id'])
            st.divider()

# ==========================================
# MÓDULO 4: BOLETOS E FIXAS
# ==========================================
elif menu == "📄 Boletos e Fixas":
    st.title("📄 Controle de Contas e Boletos")
    
    with st.expander("➕ Adicionar Novo Boleto/Conta", expanded=False):
        b_cat = st.selectbox("Categoria", ["Luz", "Internet", "Faculdade", "Seguro de Vida", "Empréstimo", "Água", "Aluguel", "Outros"])
        b_nome = st.text_input("Nome / Descrição")
        b_val = st.number_input("Valor da Parcela (R$)", min_value=0.0)
        b_faltam = st.number_input("Parcelas Restantes (0 se for conta fixa contínua)", min_value=0)
        b_venc = st.date_input("Dia de Vencimento")
        
        if st.button("Salvar Boleto"):
            salvar_dados('boletos_vip', {'categoria': b_cat, 'nome': b_nome.upper(), 'valor': b_val, 'parcelas': b_faltam, 'vencimento': str(b_venc)})
            st.success("Conta salva!")
            st.rerun()

    if not df_boletos.empty:
        st.dataframe(df_boletos[['categoria', 'nome', 'valor', 'vencimento', 'parcelas']], hide_index=True, use_container_width=True)
        sel_b = st.selectbox("Apagar Boleto", df_boletos['id'], format_func=lambda x: df_boletos.loc[df_boletos['id'] == x, 'nome'].values[0])
        if st.button("🗑️ Excluir Boleto"): excluir_dados('boletos_vip', sel_b)

# ==========================================
# MÓDULO 5: INVESTIMENTOS E METAS
# ==========================================
elif menu == "📈 Investimentos e Metas":
    st.title("📈 Construção de Patrimônio")
    
    col_inv, col_metas = st.columns(2)
    
    with col_inv:
        st.subheader("Meus Investimentos")
        i_nome = st.text_input("Onde investiu? (ex: CDB, Tesouro, Ações)")
        i_aplicado = st.number_input("Valor Aplicado (Tirado do bolso)", min_value=0.0)
        i_acumulado = st.number_input("Saldo Atual Rendendo", min_value=0.0)
        if st.button("Salvar Investimento"):
            salvar_dados('investimentos', {'nome': i_nome, 'aplicado': i_aplicado, 'acumulado': i_acumulado})
            st.rerun()
            
        if not df_invest.empty:
            df_invest['Lucro'] = df_invest['acumulado'] - df_invest['aplicado']
            st.dataframe(df_invest[['nome', 'aplicado', 'acumulado', 'Lucro']], hide_index=True)
            sel_i = st.selectbox("Apagar Investimento", df_invest['id'])
            if st.button("🗑️ Excluir Invest.", key="del_inv"): excluir_dados('investimentos', sel_i)

    with col_metas:
        st.subheader("Metas de Economia")
        m_nome = st.text_input("Objetivo (ex: Viagem, Carro Novo)")
        m_alvo = st.number_input("Valor Necessário (Meta)", min_value=0.0)
        m_atual = st.number_input("Quanto já guardou?", min_value=0.0)
        if st.button("Salvar Meta"):
            salvar_dados('metas', {'nome': m_nome, 'alvo': m_alvo, 'guardado': m_atual})
            st.rerun()
            
        if not df_metas.empty:
            for _, m in df_metas.iterrows():
                perc_meta = (m['guardado'] / m['alvo']) * 100 if m['alvo'] > 0 else 0
                st.write(f"**{m['nome']}** - R$ {m['guardado']:.2f} / R$ {m['alvo']:.2f}")
                st.progress(min(perc_meta/100, 1.0))
            sel_m = st.selectbox("Apagar Meta", df_metas['id'])
            if st.button("🗑️ Excluir Meta", key="del_met"): excluir_dados('metas', sel_m)
