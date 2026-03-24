import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN CUSTOMIZADO (CSS)
st.set_page_config(page_title="AfiliadoDash PRO", layout="wide")

st.markdown("""
<style>
    /* Fundo Escuro do Site */
    .main { background-color: #0b0e14; }
    
    /* Estilização dos Cards (Engenharia Reversa do Print) */
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    
    /* Cores das métricas */
    div[data-testid="stMetricValue"] { color: #ffffff; font-weight: bold; }
    div[data-testid="stMetricLabel"] { color: #8b949e; }
    
    /* Esconder o Menu Padrão e o Made with Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (MENU) ---
with st.sidebar:
    st.markdown("<h2 style='color: #ff4b4b;'>🟠 AfiliadoDash</h2>", unsafe_allow_html=True)
    st.divider()
    st.write("📊 **Análise do Dia**")
    st.write("📈 **Análise de Cliques**")
    st.write("🎯 **Meta Ads**")
    st.divider()
    st.header("Upload de Dados")
    arquivo = st.file_uploader("Subir CSV Shopee", type=['csv'])
    st.divider()
    invest_usd = st.number_input("Investimento (US$)", min_value=0.0, value=0.0, step=1.0)
    cotacao = st.number_input("Cotação Dólar (R$)", value=5.15)

# --- PROCESSAMENTO DO SEU CSV ---
comissao_total = 0.0
pedidos_total = 0
df = pd.DataFrame()

if arquivo:
    df = pd.read_csv(arquivo)
    # Filtrando apenas o que não foi cancelado
    df_validos = df[df['Status do Pedido'] != 'Cancelado']
    comissao_total = df_validos['Comissão líquida do afiliado(R$)'].sum()
    pedidos_total = len(df_validos)

# --- CÁLCULOS ---
invest_brl = invest_usd * cotacao
lucro = comissao_total - invest_brl
roas = comissao_total / invest_brl if invest_brl > 0 else 0.0

# --- ESTRUTURA VISUAL IGUAL AO PRINT ---
st.markdown("<h2 style='color: white;'>Análise do Dia</h2>", unsafe_allow_html=True)
st.caption("Detalhe das vendas e comissões do período.")

# Linha 1 de Cards
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendas Totais", f"R$ {comissao_total * 10:.2f}") # Valor Bruto estimado
c2.metric("Pedidos", pedidos_total)
c3.metric("Comissão Líquida", f"R$ {comissao_total:.2f}")
c4.metric("Ticket Médio", f"R$ {(comissao_total*10/pedidos_total) if pedidos_total > 0 else 0:.2f}")

# Linha 2 de Cards
c5, c6, c7, c8 = st.columns(4)
c5.metric("Investimento", f"US$ {invest_usd:.2f}", f"R$ {invest_brl:.2f}")
c6.metric("Lucro Total", f"R$ {lucro:.2f}", delta=f"R$ {lucro:.2f}")
c7.metric("ROAS", f"{roas:.2f}x")
c8.metric("CPMV", "R$ 0,00")

st.divider()

# TABELA DE SUB_IDS (A unificada que você queria)
st.markdown("<h3 style='color: white;'>Análise unificada</h3>", unsafe_allow_html=True)

if not df.empty:
    # Agrupando por Sub_id1 (Vídeo/Criativo)
    analise_sub = df[df['Status do Pedido'] != 'Cancelado'].groupby('Sub_id1').agg({
        'ID do pedido': 'count',
        'Comissão líquida do afiliado(R$)': 'sum'
    }).reset_index()
    
    analise_sub.columns = ['SubID', 'Pedidos', 'Comissão Líquida']
    
    # Exibindo a tabela formatada
    st.dataframe(analise_sub.style.format({'Comissão Líquida': 'R$ {:.2f}'}), use_container_width=True)
else:
    st.warning("Aguardando upload do CSV para gerar a análise unificada.")

# GRÁFICO DE EVOLUÇÃO (IGUAL AO PRINT)
if not df.empty:
    st.divider()
    st.subheader("Evolução de Vendas")
    df['Data'] = pd.to_datetime(df['Horário do pedido']).dt.date
    vendas_data = df.groupby('Data')['Comissão líquida do afiliado(R$)'].sum().reset_index()
    
    fig = px.line(vendas_data, x='Data', y='Comissão líquida do afiliado(R$)', 
                 template="plotly_dark", color_discrete_sequence=['#ff4b4b'])
    st.plotly_chart(fig, use_container_width=True)
