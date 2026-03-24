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

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    arquivo = st.file_uploader("Subir CSV Shopee", type=['csv'])
    st.divider()
    st.info("Painel de Visão Geral")

# --- LÓGICA DE DADOS ---
if arquivo:
    df = pd.read_csv(arquivo)
    
    # Criando a coluna de data de forma segura
    df['Data_Convertida'] = pd.to_datetime(df['Horário do pedido']).dt.strftime('%d/%m/%Y')
    
    # Filtro de válidos
    df_validos = df[df['Status do Pedido'].isin(['Pendente', 'Concluído'])].copy()
    
    vendas_brutas = df_validos['Preço(R$)'].sum()
    pedidos_total = len(df_validos)
    comissao_total = df_validos['Comissão líquida do afiliado(R$)'].sum()
    ticket_medio = vendas_brutas / pedidos_total if pedidos_total > 0 else 0

    # --- LINHA 1: METRICAS PRINCIPAIS ---
    st.markdown("### Dashboard")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Vendas Totais", f"R$ {vendas_brutas:.2f}")
    m2.metric("Pedidos", pedidos_total)
    m3.metric("Comissão Líquida", f"R$ {comissao_total:.2f}")
    m4.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
    m5.metric("Comissão a Validar", "R$ 0,00")

    st.divider()

    # --- LINHA 2: TOP SUBIDS ---
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### TOP SUBID 1 (COMISSÃO)")
        top1 = df_validos.groupby('Sub_id1')['Comissão líquida do afiliado(R$)'].sum().reset_index().sort_values('Comissão líquida do afiliado(R$)', ascending=True).tail(5)
        fig1 = px.bar(top1, x='Comissão líquida do afiliado(R$)', y='Sub_id1', orientation='h', 
                      template="plotly_dark", color_discrete_sequence=['#00c853'])
        fig1.update_layout(xaxis_visible=False, height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.markdown("### TOP SUBID 2 (COMISSÃO)")
        top2 = df_validos.groupby('Sub_id2')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        fig2 = px.bar(top2, x='Comissão líquida do afiliado(R$)', y='Sub_id2', orientation='h',
                      template="plotly_dark", color_discrete_sequence=['#ff6d00'])
        fig2.update_layout(xaxis_visible=False, height=300)
        st.plotly_chart(fig2, use_container_width=True)

    with c3:
        st.markdown("### TOP SUBID 3 (COMISSÃO)")
        st.write("Sem dados de SubID 3")

    st.divider()

    # --- LINHA 3: CANAL E STATUS ---
    c4, c5 = st.columns(2)

    with c4:
        st.markdown("### POR CANAL")
        canal_data = df_validos.groupby('Canal')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        fig_rosca = px.pie(canal_data, values='Comissão líquida do afiliado(R$)', names='Canal', 
                           hole=0.6, template="plotly_dark", 
                           color_discrete_sequence=['#2979ff', '#ff6d00', '#00c853'])
        st.plotly_chart(fig_rosca, use_container_width=True)

    with c5:
        st.markdown("### COMISSÃO POR STATUS")
        status_data = df.groupby('Status do Pedido')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        fig_status = px.bar(status_data, x='Comissão líquida do afiliado(R$)', y='Status do Pedido', orientation='h',
                            template="plotly_dark", color_discrete_sequence=['#ffd600'])
        st.plotly_chart(fig_status, use_container_width=True)

    # --- LINHA 4: EVOLUÇÃO (AQUI ESTAVA O ERRO) ---
    st.divider()
    st.markdown("<h3 style='text-align: center;'>EVOLUÇÃO DA COMISSÃO</h3>", unsafe_allow_html=True)
    
    # CORREÇÃO: Usando a coluna 'Data_Convertida' que criamos lá no topo
    evolucao = df_validos.groupby('Data_Convertida')['Comissão líquida do afiliado(R$)'].sum().reset_index()
    
    fig_line = px.line(evolucao, x='Data_Convertida', y='Comissão líquida do afiliado(R$)', 
                       markers=True, template="plotly_dark", color_discrete_sequence=['#00c853'])
    st.plotly_chart(fig_line, use_container_width=True)

else:
    st.warning("Por favor, suba o arquivo CSV na barra lateral para carregar o Dashboard.")
