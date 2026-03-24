import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import io

# 1. SETUP DE DESIGN
st.set_page_config(page_title="AfiliadoDash PRO", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    div[data-testid="metric-container"] {
        background-color: #161b22; border: 1px solid #30363d;
        padding: 20px; border-radius: 12px;
    }
    h1, h2, h3 { color: white !important; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
</style>
""", unsafe_allow_html=True)

hoje_pc = date.today()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    st.divider()
    arquivo_vendas = st.file_uploader("Subir CSV de Vendas", type=['csv'])
    arquivo_cliques = st.file_uploader("Subir CSV de Cliques", type=['csv'])
    st.divider()
    data_sel = st.date_input("📅 Filtro de Período", value=[hoje_pc, hoje_pc], max_value=hoje_pc)

# --- FUNÇÃO DE LEITURA BLINDADA (RESOLVE O PROBLEMA DE NÃO LER) ---
def ler_csv_shopee(file):
    if file is None:
        return pd.DataFrame()
    try:
        # Tenta ler com separador vírgula (padrão global)
        df = pd.read_csv(file, encoding='utf-8')
    except:
        try:
            # Se der erro, tenta ler com ponto e vírgula (padrão Excel Brasil)
            file.seek(0)
            df = pd.read_csv(file, sep=';', encoding='latin-1')
        except Exception as e:
            st.error(f"Erro técnico ao processar: {e}")
            return pd.DataFrame()
    return df

# --- PROCESSAMENTO ---
start_d, end_d = (data_sel[0], data_sel[1]) if len(data_sel) == 2 else (hoje_pc, hoje_pc)

df_v_filtrado = pd.DataFrame()
cliques_t = 0

# Processar Vendas
if arquivo_vendas:
    df_v = ler_csv_shopee(arquivo_vendas)
    if not df_v.empty:
        # Garante que a coluna de data exista
        col_data_v = 'Horário do pedido'
        if col_data_v in df_v.columns:
            df_v['Data_Simples'] = pd.to_datetime(df_v[col_data_v]).dt.date
            df_v_filtrado = df_v[(df_v['Data_Simples'] >= start_d) & (df_v['Data_Simples'] <= end_d)].copy()
        else:
            st.warning("Coluna 'Horário do pedido' não encontrada no arquivo de vendas.")

# Processar Cliques
if arquivo_cliques:
    df_c = ler_csv_shopee(arquivo_cliques)
    if not df_c.empty:
        col_data_c = 'Tempo dos Cliques'
        if col_data_c in df_c.columns:
            df_c['Data_Simples'] = pd.to_datetime(df_c[col_data_c]).dt.date
            df_c_filtrado = df_c[(df_c['Data_Simples'] >= start_d) & (df_c['Data_Simples'] <= end_d)]
            cliques_t = len(df_c_filtrado)
        else:
            st.warning("Coluna 'Tempo dos Cliques' não encontrada no arquivo de cliques.")

# --- CÁLCULOS ---
vendas_b = df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado']['Preço(R$)'].sum() if not df_v_filtrado.empty else 0.0
pedidos_t = len(df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado']) if not df_v_filtrado.empty else 0
comissao_t = df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado']['Comissão líquida do afiliado(R$)'].sum() if not df_v_filtrado.empty else 0.0
ticket = vendas_b / pedidos_t if pedidos_t > 0 else 0
conv = (pedidos_t / cliques_t * 100) if cliques_t > 0 else 0

# --- TELA ---
st.title("Dashboard de Visão Geral")

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Vendas Totais", f"R$ {vendas_b:.2f}")
m2.metric("Pedidos", pedidos_t)
m3.metric("Comissão Líquida", f"R$ {comissao_t:.2f}")
m4.metric("Ticket Médio", f"R$ {ticket:.2f}")
m5.metric("Cliques Totais", cliques_t)
m6.metric("Conversão", f"{conv:.2f}%")

st.divider()

if not df_v_filtrado.empty:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📊 Análise por SubID")
        tab = df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado'].groupby('Sub_id1').agg({'ID do pedido':'count', 'Comissão líquida do afiliado(R$)':'sum'}).reset_index()
        st.dataframe(tab, use_container_width=True)
    with c2:
        st.subheader("🎯 Por Canal")
        fig = px.pie(df_v_filtrado, values='Comissão líquida do afiliado(R$)', names='Canal', hole=0.6, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📈 Evolução da Comissão")
    evolucao = df_v_filtrado.groupby('Data_Simples')['Comissão líquida do afiliado(R$)'].sum().reset_index()
    fig_a = px.area(evolucao, x='Data_Simples', y='Comissão líquida do afiliado(R$)', template="plotly_dark", color_discrete_sequence=['#00c853'], markers=True)
    fig_a.update_traces(line_shape='spline')
    st.plotly_chart(fig_a, use_container_width=True)
else:
    st.info("Aguardando upload e seleção de data válida para exibir os dados.")
