import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# 1. CONFIGURAÇÃO DE DESIGN (MODO DARK E LAYOUT)
st.set_page_config(page_title="Afiliado Dash Pro", layout="wide", initial_sidebar_state="expanded")

# CSS para deixar os cards bonitos igual ao seu print
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #ffffff; }
    [data-testid="stMetricLabel"] { font-size: 16px; color: #a1a1a1; }
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { background-color: #ff4b4b; color: white; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3141/3141133.png", width=80)
    st.title("Menu")
    st.divider()
    st.header("📁 Importar Relatórios")
    arquivo_vendas = st.file_uploader("CSV de Vendas Shopee", type=['csv'])
    arquivo_cliques = st.file_uploader("CSV de Cliques Shopee", type=['csv'])
    st.divider()
    st.info("BM Americana Detectada: US$")

# --- PROCESSAMENTO DOS DADOS ---
vendas_val = 0.0
pedidos_val = 0
cliques_val = 0

if arquivo_vendas:
    df_v = pd.read_csv(arquivo_vendas)
    pedidos_val = len(df_v)
    vendas_val = 150.75 # Simulando valor por enquanto

if arquivo_cliques:
    df_c = pd.read_csv(arquivo_cliques)
    cliques_val = len(df_c)

# --- CABEÇALHO ---
st.title("🚀 Dashboard de Operação")
st.write(f"Análise de dados para vídeos dark | {date.today().strftime('%d/%m/%Y')}")

# --- LINHA 1: CARDS DE MÉTRICAS ---
col1, col2, col3, col4 = st.columns(4)

investimento_manual = st.number_input("💸 Gasto Meta Ads (US$)", min_value=0.0, value=0.0, help="Insira o valor gasto hoje na sua BM")

# Pegar cotação fixa de R$ 5.00 para facilitar o cálculo visual
cotacao = 5.0
gasto_brl = investimento_manual * cotacao
lucro = vendas_val - gasto_brl

with col1:
    st.metric("Investimento Total", f"US$ {investimento_manual:.2f}", f"R$ {gasto_brl:.2f} (estimado)")
with col2:
    st.metric("Vendas Shopee", f"R$ {vendas_val:.2f}", f"{pedidos_val} pedidos")
with col3:
    st.metric("Lucro Líquido", f"R$ {lucro:.2f}", delta=f"{lucro:.2f}")
with col4:
    roas = vendas_val / gasto_brl if gasto_brl > 0 else 0
    st.metric("ROAS", f"{roas:.2f}x")

st.divider()

# --- LINHA 2: GRÁFICO E TABELA (Engenharia Reversa do seu print) ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("📈 Evolução de Cliques")
    # Criando um gráfico de exemplo para preencher o espaço
    dados_grafico = pd.DataFrame({'Dia': ['Seg', 'Ter', 'Qua', 'Qui', 'Sex'], 'Cliques': [100, 250, 400, 800, cliques_val]})
    fig = px.line(dados_grafico, x='Dia', y='Cliques', template="plotly_dark", color_discrete_sequence=['#ff4b4b'])
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("🛍️ Status da Shopee")
    # Tabela simples de status
    status_dados = pd.DataFrame({
        'Status': ['Concluído', 'Pendente', 'Cancelado'],
        'Qtd': [pedidos_val, 0, 0],
        'Valor': [f"R$ {vendas_val}", "R$ 0,00", "R$ 0,00"]
    })
    st.table(status_dados)

st.success("Configuração local concluída. Quando a API liberar, os gráficos serão automáticos!")
