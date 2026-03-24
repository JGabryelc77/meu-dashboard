import streamlit as st
import pandas as pd
import plotly.express as px

# 1. ESTILO E CONFIGURAÇÃO
st.set_page_config(page_title="AfiliadoDash | Dashboard", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    div[data-testid="metric-container"] {
        background-color: #161b22; border: 1px solid #30363d;
        padding: 20px; border-radius: 10px;
    }
    h3 { color: white; font-size: 18px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (BARRA LATERAL) ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    arquivo = st.file_uploader("Subir CSV Shopee", type=['csv'])
    st.divider()
    
    # NOVO: Filtro de Data
    st.header("📅 Filtro de Período")
    data_selecionada = st.date_input("Selecione o intervalo", value=[])
    
    st.divider()
    st.info("Painel de Visão Geral")

# --- LÓGICA DE DADOS ---
if arquivo:
    df = pd.read_csv(arquivo)
    
    # Converter a coluna de tempo para formato de data real do Python
    df['Data_Full'] = pd.to_datetime(df['Horário do pedido'])
    df['Data_Simples'] = df['Data_Full'].dt.date
    
    # Aplicar o filtro de data se o usuário selecionou algo
    if len(data_selecionada) == 2:
        start_date, end_date = data_selecionada
        df = df[(df['Data_Simples'] >= start_date) & (df['Data_Simples'] <= end_date)]
    elif len(data_selecionada) == 1:
        df = df[df['Data_Simples'] == data_selecionada[0]]

    # Filtro de pedidos válidos
    df_validos = df[df['Status do Pedido'].isin(['Pendente', 'Concluído'])].copy()
    
    # Cálculos das métricas
    vendas_brutas = df_validos['Preço(R$)'].sum()
    pedidos_total = len(df_validos)
    comissao_total = df_validos['Comissão líquida do afiliado(R$)'].sum()
    ticket_medio = vendas_brutas / pedidos_total if pedidos_total > 0 else 0

    # --- RENDERIZAÇÃO DO DASHBOARD ---
    st.markdown(f"### Dashboard | Período Selecionado")
    
    # LINHA 1: METRICAS
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Vendas Totais", f"R$ {vendas_brutas:.2f}")
    m2.metric("Pedidos", pedidos_total)
    m3.metric("Comissão Líquida", f"R$ {comissao_total:.2f}")
    m4.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
    m5.metric("Comissão a Validar", "R$ 0,00")

    st.divider()

    # LINHA 2: GRÁFICOS DE SUBID
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### TOP SUBID 1")
        top1 = df_validos.groupby('Sub_id1')['Comissão líquida do afiliado(R$)'].sum().reset_index().sort_values('Comissão líquida do afiliado(R$)', ascending=True).tail(5)
        fig1 = px.bar(top1, x='Comissão líquida do afiliado(R$)', y='Sub_id1', orientation='h', template="plotly_dark", color_discrete_sequence=['#00c853'])
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.markdown("### TOP SUBID 2")
        top2 = df_validos.groupby('Sub_id2')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        fig2 = px.bar(top2, x='Comissão líquida do afiliado(R$)', y='Sub_id2', orientation='h', template="plotly_dark", color_discrete_sequence=['#ff6d00'])
        st.plotly_chart(fig2, use_container_width=True)

    with c3:
        st.markdown("### POR CANAL")
        canal_data = df_validos.groupby('Canal')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        fig_rosca = px.pie(canal_data, values='Comissão líquida do afiliado(R$)', names='Canal', hole=0.6, template="plotly_dark")
        st.plotly_chart(fig_rosca, use_container_width=True)

    # LINHA 3: EVOLUÇÃO TEMPORAL
    st.divider()
    st.markdown("<h3 style='text-align: center;'>EVOLUÇÃO DA COMISSÃO NO PERÍODO</h3>", unsafe_allow_html=True)
    
    # Agrupar por dia para mostrar a evolução real
    evolucao = df_validos.groupby('Data_Simples')['Comissão líquida do afiliado(R$)'].sum().reset_index()
    fig_line = px.line(evolucao, x='Data_Simples', y='Comissão líquida do afiliado(R$)', markers=True, template="plotly_dark", color_discrete_sequence=['#00c853'])
    st.plotly_chart(fig_line, use_container_width=True)

else:
    st.warning("Aguardando upload do arquivo CSV...")
