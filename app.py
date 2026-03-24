import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SETUP DE DESIGN AVANÇADO (ESTILO AFILIADODASH)
st.set_page_config(page_title="AfiliadoDash PRO", layout="wide", initial_sidebar_state="expanded")

# Injeção de CSS para forçar o design premium (modo dark, cards arredondados e sem bordas padrão)
st.markdown("""
<style>
    /* Fundo Escuro do Site */
    .main { background-color: #0b0e14; }
    
    /* Estilização dos Cards de Métrica (Cinza Escuro e Arredondado) */
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    
    /* Cores das métricas */
    div[data-testid="stMetricValue"] > div { color: #ffffff !important; font-family: 'Inter', sans-serif; }
    div[data-testid="stMetricLabel"] > label { color: #8b949e !important; }
    div[data-testid="stMetricDelta"] > div { color: #00c853 !important; }
    
    /* Títulos Brancos */
    h1, h2, h3 { color: white !important; font-family: 'Inter', sans-serif; }
    
    /* Sidebar Premium */
    [data-testid="stSidebar"] { background-color: #0e1117; border-right: 1px solid #30363d; }
    
    /* Esconder elementos padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (BARRA LATERAL) ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    st.divider()
    
    arquivo = st.file_uploader("Subir CSV Shopee", type=['csv'], help="Baixe o relatório de vendas no painel de afiliado")
    
    st.divider()
    
    # Filtro de Período (Calendário)
    st.header("📅 Filtro de Período")
    data_selecionada = st.date_input("Selecione o intervalo", value=[], help="Clique no dia de início e depois no dia de fim")
    
    st.divider()
    st.caption("v1.0.0 Pro")

# --- LÓGICA DE DADOS ---
if arquivo:
    df = pd.read_csv(arquivo)
    
    # Processamento de Datas
    df['Data_Full'] = pd.to_datetime(df['Horário do pedido'])
    df['Data_Simples'] = df['Data_Full'].dt.date
    
    # Aplicar o filtro de data (calendário)
    if len(data_selecionada) == 2:
        start_date, end_date = data_selecionada
        df = df[(df['Data_Simples'] >= start_date) & (df['Data_Simples'] <= end_date)]
    elif len(data_selecionada) == 1:
        df = df[df['Data_Simples'] == data_selecionada[0]]

    # Filtro de Pedidos Válidos
    df_validos = df[df['Status do Pedido'].isin(['Pendente', 'Concluído'])].copy()
    
    # CÁLCULOS
    vendas_brutas = df_validos['Preço(R$)'].sum()
    pedidos_total = len(df_validos)
    comissao_total = df_validos['Comissão líquida do afiliado(R$)'].sum()
    ticket_medio = vendas_brutas / pedidos_total if pedidos_total > 0 else 0

    # --- RENDERIZAÇÃO DO DASHBOARD ---
    st.title("Dashboard de Visão Geral")
    st.write(f"Análise de dados para vídeos dark")

    # LINHA 1: METRICAS PRINCIPAIS
    st.markdown("### Resumo")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vendas Totais", f"R$ {vendas_brutas:.2f}")
    m2.metric("Pedidos", pedidos_total)
    m3.metric("Comissão Líquida", f"R$ {comissao_total:.2f}")
    m4.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")

    st.divider()

    # LINHA 2: GRÁFICOS DE SUBID (BARRAS HORIZONTAIS)
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### TOP SUBID 1")
        top1 = df_validos.groupby('Sub_id1')['Comissão líquida do afiliado(R$)'].sum().reset_index().sort_values('Comissão líquida do afiliado(R$)', ascending=True).tail(5)
        fig1 = px.bar(top1, x='Comissão líquida do afiliado(R$)', y='Sub_id1', 
                      orientation='h', template="plotly_dark", 
                      color_discrete_sequence=['#00c853']) # Cor Verde
        fig1.update_layout(xaxis_visible=False, height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig1, use_container_width=True)
        
    with c2:
        st.markdown("### TOP SUBID 2")
        top2 = df_validos.groupby('Sub_id2')['Comissão líquida do afiliado(R$)'].sum().reset_index().sort_values('Comissão líquida do afiliado(R$)', ascending=True).tail(5)
        fig2 = px.bar(top2, x='Comissão líquida do afiliado(R$)', y='Sub_id2', 
                      orientation='h', template="plotly_dark", 
                      color_discrete_sequence=['#ff6d00']) # Cor Laranja
        fig2.update_layout(xaxis_visible=False, height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # LINHA 3: EVOLUÇÃO TEMPORAL (GRÁFICO DE MONTANHA / ÁREA)
    st.markdown("<h3 style='text-align: center;'>EVOLUÇÃO DA COMISSÃO NO PERÍODO</h3>", unsafe_allow_html=True)
    
    if not df_validos.empty:
        # Agrupar comissão por dia
        evolucao = df_validos.groupby('Data_Simples')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        evolucao.columns = ['Data', 'Comissão']
        
        # Criação do gráfico de ÁREA (Montanha)
        fig_area = px.area(evolucao, x='Data', y='Comissão', 
                          template="plotly_dark", 
                          color_discrete_sequence=['#00c853'], # Verde Shopee
                          markers=True) # Pontos nos dias
        
        # Ajustes visuais do gráfico
        fig_area.update_layout(
            yaxis_title="Comissão (R$)",
            xaxis_title="Dia",
            margin=dict(l=20, r=20, t=20, b=20),
            height=400
        )
        # Suavizar a linha da montanha
        fig_area.update_traces(line_shape='spline')
        
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.warning("Nenhum pedido válido encontrado no período selecionado.")

else:
    st.warning("Aguardando upload do arquivo CSV na barra lateral...")
