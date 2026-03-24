import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# 1. SETUP DE DESIGN PREMIUM (IGUAL AO AFILIADODASH)
st.set_page_config(page_title="AfiliadoDash PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    div[data-testid="metric-container"] {
        background-color: #161b22; border: 1px solid #30363d;
        padding: 20px; border-radius: 12px;
    }
    div[data-testid="stMetricValue"] > div { color: #ffffff !important; font-size: 24px !important; }
    div[data-testid="stMetricLabel"] > label { color: #8b949e !important; }
    h1, h2, h3 { color: white !important; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
</style>
""", unsafe_allow_html=True)

hoje_pc = date.today()

# --- BARRA LATERAL (MENU E FILTROS) ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    st.divider()
    st.header("📁 Importar Relatórios")
    arquivo_vendas = st.file_uploader("Subir CSV de Vendas", type=['csv'])
    arquivo_cliques = st.file_uploader("Subir CSV de Cliques", type=['csv'])
    st.divider()
    
    # FILTRO DE DATA UNIFICADO (COM TRAVA DE FUTURO)
    st.header("📅 Filtro de Período")
    data_sel = st.date_input("Intervalo", value=[hoje_pc, hoje_pc], max_value=hoje_pc)

# --- TRATAMENTO DE DATAS ---
start_d, end_d = (data_sel[0], data_sel[1]) if len(data_sel) == 2 else (hoje_pc, hoje_pc)

# --- PROCESSAMENTO DOS DADOS ---
vendas_b, pedidos_t, comissao_t, cliques_t = 0.0, 0, 0.0, 0
df_v_filtrado = pd.DataFrame()
df_c_filtrado = pd.DataFrame()

# 1. Lógica de Vendas
if arquivo_vendas:
    df_v = pd.read_csv(arquivo_vendas)
    df_v['Data_Simples'] = pd.to_datetime(df_v['Horário do pedido']).dt.date
    df_v_filtrado = df_v[(df_v['Data_Simples'] >= start_d) & (df_v['Data_Simples'] <= end_d)]
    df_validos = df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado']
    vendas_b = df_validos['Preço(R$)'].sum()
    pedidos_t = len(df_validos)
    comissao_t = df_validos['Comissão líquida do afiliado(R$)'].sum()

# 2. Lógica de Cliques (Baseada no seu cabeçalho real)
if arquivo_cliques:
    df_c = pd.read_csv(arquivo_cliques)
    # Usando o nome da coluna que você mandou: "Tempo dos Cliques"
    df_c['Data_Simples'] = pd.to_datetime(df_c['Tempo dos Cliques']).dt.date
    df_c_filtrado = df_c[(df_c['Data_Simples'] >= start_d) & (df_c['Data_Simples'] <= end_d)]
    cliques_t = len(df_c_filtrado)

# Cálculos extras
ticket = vendas_b / pedidos_t if pedidos_t > 0 else 0
conv = (pedidos_t / cliques_t * 100) if cliques_t > 0 else 0

# --- TELA PRINCIPAL ---
st.title("Dashboard de Visão Geral")
st.caption(f"Período selecionado: {start_d.strftime('%d/%m/%Y')} até {end_d.strftime('%d/%m/%Y')}")

# LINHA 1: OS 6 CARDS (ESTRUTURA COMPLETA)
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Vendas Totais", f"R$ {vendas_b:.2f}")
m2.metric("Pedidos", pedidos_t)
m3.metric("Comissão Líquida", f"R$ {comissao_t:.2f}")
m4.metric("Ticket Médio", f"R$ {ticket:.2f}")
m5.metric("Cliques Totais", cliques_t)
m6.metric("Conversão", f"{conv:.2f}%")

st.divider()

# LINHA 2: TABELA E ROSCA
col_esq, col_dir = st.columns([2, 1])

with col_esq:
    st.subheader("📊 Análise Unificada (SubIDs)")
    if not df_v_filtrado.empty:
        # Agrupamento por SubID
        tab = df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado'].groupby('Sub_id1').agg({
            'ID do pedido': 'count',
            'Comissão líquida do afiliado(R$)': 'sum'
        }).reset_index()
        tab.columns = ['SubID', 'Pedidos', 'Comissão']
        st.dataframe(tab.style.format({'Comissão': 'R$ {:.2f}'}), use_container_width=True)
    else:
        st.info("Suba o arquivo de Vendas para ver a análise por vídeo.")

with col_dir:
    st.subheader("🎯 Por Canal")
    if not df_v_filtrado.empty:
        fig_rosca = px.pie(df_v_filtrado, values='Comissão líquida do afiliado(R$)', names='Canal', 
                           hole=0.6, template="plotly_dark", 
                           color_discrete_sequence=['#ff4b4b', '#2979ff', '#00c853'])
        fig_rosca.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250)
        st.plotly_chart(fig_rosca, use_container_width=True)

st.divider()

# LINHA 3: EVOLUÇÃO (GRÁFICO DE MONTANHA)
st.subheader("📈 EVOLUÇÃO DA COMISSÃO")
if not df_v_filtrado.empty:
    evolucao = df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado'].groupby('Data_Simples')['Comissão líquida do afiliado(R$)'].sum().reset_index()
    fig_area = px.area(evolucao, x='Data_Simples', y='Comissão líquida do afiliado(R$)', 
                      template="plotly_dark", color_discrete_sequence=['#00c853'], markers=True)
    fig_area.update_traces(line_shape='spline')
    fig_area.update_layout(yaxis_title="Comissão (R$)", xaxis_title="Dia")
    st.plotly_chart(fig_area, use_container_width=True)
