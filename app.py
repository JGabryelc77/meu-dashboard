import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime

# 1. SETUP DE DESIGN AVANÇADO (ESTILO AFILIADODASH)
st.set_page_config(page_title="AfiliadoDash PRO", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    div[data-testid="metric-container"] {
        background-color: #161b22; border: 1px solid #30363d;
        padding: 20px; border-radius: 12px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricValue"] > div { color: #ffffff !important; }
    div[data-testid="stMetricLabel"] > label { color: #8b949e !important; }
    h1, h2, h3 { color: white !important; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
</style>
""", unsafe_allow_html=True)

# --- PEGAR DATA ATUAL DO PC (TRAVA) ---
hoje_pc = date.today()

# --- SIDEBAR (BARRA LATERAL) ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    st.divider()
    
    # 1. DOIS UPLOADS (RESTAURADO)
    st.header("📁 Importar Relatórios")
    arquivo_vendas = st.file_uploader("CSV de Vendas Shopee", type=['csv'])
    arquivo_cliques = st.file_uploader("CSV de Cliques Shopee", type=['csv'])
    
    st.divider()
    
    # 2. FILTRO UNIFICADO COM TRAVA DE FUTURO
    st.header("📅 Filtro de Período")
    data_selecionada = st.date_input(
        "Selecione o intervalo", 
        value=[hoje_pc, hoje_pc], # Padrão: HOJE
        max_value=hoje_pc,        # BLOQUEIO: Não deixa clicar no futuro
        help="Datas futuras estão bloqueadas automaticamente."
    )
    
    st.divider()
    st.caption(f"Data do Sistema: {hoje_pc.strftime('%d/%m/%Y')}")

# --- INICIALIZAÇÃO DE VARIÁVEIS ---
df_vendas = pd.DataFrame()
df_cliques = pd.DataFrame()
start_date, end_date = None, None

# Processar intervalo de datas selecionado
if len(data_selecionada) == 2:
    start_date, end_date = data_selecionada
elif len(data_selecionada) == 1:
    start_date = data_selecionada[0]
    end_date = data_selecionada[0]

# --- LÓGICA DE DADOS (PROCESSAMENTO UNIFICADO) ---

# 1. Processar Vendas (se o arquivo for subido)
if arquivo_vendas:
    df_vendas = pd.read_csv(arquivo_vendas)
    
    # Converter e Tratar Datas (Seguro)
    df_vendas['Data_Full'] = pd.to_datetime(df_vendas['Horário do pedido'])
    df_vendas['Data_Simples'] = df_vendas['Data_Full'].dt.date
    
    # Trava de Segurança Contra Futuro no Código
    df_vendas = df_vendas[df_vendas['Data_Simples'] <= hoje_pc]
    
    # Aplicar o filtro do calendário
    if start_date and end_date:
        df_vendas = df_vendas[(df_vendas['Data_Simples'] >= start_date) & (df_vendas['Data_Simples'] <= end_date)]

# 2. Processar Cliques (se o arquivo for subido) - NOVA LÓGICA
if arquivo_cliques:
    # Nota: O CSV de cliques da Shopee costuma ter colunas diferentes. 
    # Vou assumir colunas padrão 'Date' e 'Clicks'. Se der erro, me mande o CSV de cliques.
    df_cliques = pd.read_csv(arquivo_cliques)
    
    try:
        # Converter data (Ajustar o nome da coluna 'Date' conforme seu arquivo real)
        df_cliques['Data_Full'] = pd.to_datetime(df_cliques['Date']) 
        df_cliques['Data_Simples'] = df_cliques['Data_Full'].dt.date
        
        # Trava de Segurança Contra Futuro no Código
        df_cliques = df_cliques[df_cliques['Data_Simples'] <= hoje_pc]
        
        # Aplicar o filtro do calendário (Unificado)
        if start_date and end_date:
            df_cliques = df_cliques[(df_cliques['Data_Simples'] >= start_date) & (df_cliques['Data_Simples'] <= end_date)]
    except Exception as e:
        st.sidebar.error(f"Erro ao ler CSV de Cliques. Verifique os nomes das colunas. Erro: {e}")
        df_cliques = pd.DataFrame() # Reseta se der erro

# --- CÁLCULOS FINANCEIROS (MÉTRICAS RESUMO) ---
# Inicializa métricas zeradas
vendas_brutas, pedidos_total, comissao_total, ticket_medio, total_cliques, conversao = 0.0, 0, 0.0, 0.0, 0, 0.0

if not df_vendas.empty:
    # Filtro de pedidos válidos
    df_validos = df_vendas[df_vendas['Status do Pedido'].isin(['Pendente', 'Concluído'])].copy()
    
    vendas_brutas = df_validos['Preço(R$)'].sum()
    pedidos_total = len(df_validos)
    comissao_total = df_validos['Comissão líquida do afiliado(R$)'].sum()
    ticket_medio = vendas_brutas / pedidos_total if pedidos_total > 0 else 0.0

if not df_cliques.empty:
    # Soma total de cliques no período selecionado (assumindo coluna 'Clicks')
    total_cliques = df_cliques['Clicks'].sum() if 'Clicks' in df_cliques.columns else len(df_cliques)

# Cálculo de Conversão de Cliques em Pedidos
if total_cliques > 0 and pedidos_total > 0:
    conversao = (pedidos_total / total_cliques) * 100

# --- INTERFACE PRINCIPAL (A ESTRUTURA COMPLETA) ---
st.title("Dashboard de Visão Geral")
st.write(f"Análise de dados para vídeos dark | Período: {start_date.strftime('%d/%m/%Y') if start_date else ''} até {end_date.strftime('%d/%m/%Y') if end_date else ''}")

# LINHA 1: METRICAS PRINCIPAIS (6 cards agora)
st.markdown("### Resumo do Período")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Vendas Totais", f"R$ {vendas_brutas:.2f}")
m2.metric("Pedidos", pedidos_total)
m3.metric("Comissão Líquida", f"R$ {comissao_total:.2f}")
m4.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
m5.metric("Cliques Totais", total_cliques)
m6.metric("Conversão", f"{conversao:.2f}%")

st.divider()

# LINHA 2: ANÁLISE DETALHADA (TABELA E ROSCA)
if not df_vendas.empty:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("📊 Análise Unificada (por Vídeo/SubID)")
        # Tabela detalhada por Sub_id1 (Vídeo/Produto)
        tab_unificada = df_vendas[df_vendas['Status do Pedido'] != 'Cancelado'].groupby('Sub_id1').agg({
            'ID do pedido': 'count',
            'Comissão líquida do afiliado(R$)': 'sum',
            'Preço(R$)': 'sum'
        }).reset_index()
        
        tab_unificada.columns = ['SubID', 'Pedidos', 'Comissão Líquida', 'Valor Total']
        
        st.dataframe(tab_unificada.style.format({
            'Comissão Líquida': 'R$ {:.2f}', 
            'Valor Total': 'R$ {:.2f}'
        }), use_container_width=True)

    with c2:
        st.subheader("🎯 Vendas por Canal")
        # Gráfico de Rosca "Por Canal"
        canal_data = df_vendas[df_vendas['Status do Pedido'] != 'Cancelado'].groupby('Canal')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        fig_rosca = px.pie(canal_data, values='Comissão líquida do afiliado(R$)', names='Canal', 
                           hole=0.6, template="plotly_dark", 
                           color_discrete_sequence=['#ff4b4b', '#ff6d00', '#00c853'])
        fig_rosca.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
        st.plotly_chart(fig_rosca, use_container_width=True)
else:
    st.info("Suba o arquivo de Vendas para ver a análise detalhada.")

st.divider()

# LINHA 3: EVOLUÇÃO TEMPORAL (GRÁFICO DE MONTANHA)
st.markdown("<h3 style='text-align: center;'>EVOLUÇÃO FINANCEIRA NO PERÍODO</h3>", unsafe_allow_html=True)
if not df_vendas.empty:
    # Agrupar comissão por dia
    evolucao = df_vendas[df_vendas['Status do Pedido'] != 'Cancelado'].groupby('Data_Simples')['Comissão líquida do afiliado(R$)'].sum().reset_index()
    evolucao.columns = ['Data', 'Comissão']
    
    # Criação do gráfico de ÁREA (Montanha) suavizado
    fig_area = px.area(evolucao, x='Data', y='Comissão', 
                      template="plotly_dark", 
                      color_discrete_sequence=['#00c853'], # Verde
                      markers=True) # Pontos nos dias
    fig_area.update_traces(line_shape='spline') # Suavizar a linha
    fig_area.update_layout(yaxis_title="Comissão (R$)", xaxis_title="Dia", height=400)
    
    st.plotly_chart(fig_area, use_container_width=True)
else:
    st.warning("Nenhum pedido encontrado no período selecionado.")
