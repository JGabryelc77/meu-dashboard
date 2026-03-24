import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# 1. DESIGN E CONFIGURAÇÃO
st.set_page_config(page_title="Afiliado Dash Pro", layout="wide")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 28px; }
    .main { background-color: #0e1117; }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Configurações")
    arquivo_vendas = st.file_uploader("Subir CSV de Vendas (Shopee)", type=['csv'])
    st.divider()
    investimento_usd = st.number_input("💸 Gasto Meta Ads (US$)", min_value=0.0, value=0.0)
    cotacao = st.number_input("💵 Cotação Dólar (R$)", min_value=1.0, value=5.10)

# --- PROCESSAMENTO REAL DO CSV ---
comissao_total = 0.0
qtd_pedidos = 0
df_vendas = pd.DataFrame()

if arquivo_vendas:
    try:
        # Lendo o CSV da Shopee
        df_vendas = pd.read_csv(arquivo_vendas)
        
        # Filtrando apenas pedidos que não foram cancelados
        df_validos = df_vendas[df_vendas['Status do Pedido'] != 'Cancelado']
        
        # Somando a comissão líquida real
        comissao_total = df_validos['Comissão líquida do afiliado(R$)'].sum()
        qtd_pedidos = len(df_validos)
        
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")

# --- CÁLCULOS FINANCEIROS ---
gasto_brl = investimento_usd * cotacao
lucro_real = comissao_total - gasto_brl
roas = comissao_total / gasto_brl if gasto_brl > 0 else 0.0

# --- INTERFACE PRINCIPAL ---
st.title("🚀 Dashboard de Operação Real")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Investimento", f"US$ {investimento_usd:.2f}", f"R$ {gasto_brl:.2f}")
with col2:
    st.metric("Comissão Shopee", f"R$ {comissao_total:.2f}", f"{qtd_pedidos} pedidos")
with col3:
    st.metric("Lucro Líquido", f"R$ {lucro_real:.2f}", delta=f"{lucro_real:.2f}")
with col4:
    st.metric("ROAS", f"{roas:.2f}x")

st.divider()

# --- ANÁLISE POR VÍDEO (SUB_ID1) ---
if not df_vendas.empty:
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("📊 Vendas por Vídeo (Sub_id1)")
        # Agrupando vendas por Sub_id1
        vendas_por_sub = df_vendas[df_vendas['Status do Pedido'] != 'Cancelado'].groupby('Sub_id1')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        vendas_por_sub = vendas_por_sub.sort_values(by='Comissão líquida do afiliado(R$)', ascending=False)
        
        fig = px.bar(vendas_por_sub, x='Sub_id1', y='Comissão líquida do afiliado(R$)', 
                     title="Ranking de Lucro por Vídeo", template="plotly_dark",
                     color_discrete_sequence=['#00FF00'])
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("📝 Últimos Pedidos")
        st.dataframe(df_vendas[['Horário do pedido', 'Status do Pedido', 'Sub_id1', 'Comissão líquida do afiliado(R$)']].head(10), use_container_width=True)

else:
    st.info("Aguardando upload do CSV da Shopee para analisar os vídeos...")
