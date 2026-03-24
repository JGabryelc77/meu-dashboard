import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SETUP DE DESIGN PROFISSIONAL
st.set_page_config(page_title="AfiliadoDash PRO", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    /* Estilização dos Cards com Ícones e Cores */
    .stMetric {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    h2, h3 { color: white !important; font-family: 'Inter', sans-serif; }
    p { color: #8b949e !important; }
    
    /* Tabela Estilo Dark */
    .styled-table { border-collapse: collapse; width: 100%; color: white; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (MENU LATERAL) ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    st.divider()
    st.button("🏠 Análise do Dia", use_container_width=True)
    st.button("📈 Análise de Cliques", use_container_width=True)
    st.button("🎯 Meta Ads", use_container_width=True)
    st.divider()
    st.header("Upload de Dados")
    arquivo = st.file_uploader("Subir CSV Shopee", type=['csv'])
    st.divider()
    invest_usd = st.number_input("Investimento (US$)", min_value=0.0, value=0.0)
    cotacao = st.number_input("Cotação Dólar (R$)", value=5.15)

# --- LÓGICA DE DADOS ---
comissao_total = 0.0
pedidos_total = 0
vendas_brutas = 0.0
df = pd.DataFrame()

if arquivo:
    df = pd.read_csv(arquivo)
    df_validos = df[df['Status do Pedido'] != 'Cancelado']
    comissao_total = df_validos['Comissão líquida do afiliado(R$)'].sum()
    pedidos_total = len(df_validos)
    vendas_brutas = df_validos['Preço(R$)'].sum()

invest_brl = invest_usd * cotacao
lucro = comissao_total - invest_brl
roas = comissao_total / invest_brl if invest_brl > 0 else 0.0
ticket = vendas_brutas / pedidos_total if pedidos_total > 0 else 0.0

# --- TELA PRINCIPAL (ESTRUTURA IGUAL AO PRINT) ---
st.title("Análise do Dia")
st.write("Detalhe das vendas e comissões do período.")

# GRID DE CARDS 1
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendas Totais", f"R$ {vendas_brutas:.2f}", help="Soma dos preços dos produtos")
c2.metric("Pedidos", pedidos_total, "Total de vendas")
c3.metric("Comissão Líquida", f"R$ {comissao_total:.2f}", "Seu lucro bruto")
c4.metric("Ticket Médio", f"R$ {ticket:.2f}")

# GRID DE CARDS 2
c5, c6, c7, c8 = st.columns(4)
c5.metric("Investimento", f"US$ {invest_usd:.2f}", f"R$ {invest_brl:.2f}")
c6.metric("Lucro Total", f"R$ {lucro:.2f}", delta=f"R$ {lucro:.2f}")
c7.metric("ROAS", f"{roas:.2f}x")
c8.metric("CPMV", "R$ 0,00")

st.markdown("---")

# ANÁLISE UNIFICADA (TABELA DETALHADA)
st.subheader("Análise unificada")
if not df.empty:
    # Criando a tabela igual ao print
    tab_unificada = df_validos.groupby('Sub_id1').agg({
        'ID do pedido': 'count',
        'Comissão líquida do afiliado(R$)': 'sum',
        'Preço(R$)': 'sum'
    }).reset_index()
    
    tab_unificada.columns = ['SubID', 'Pedidos', 'Comissão Líquida', 'Valor Total']
    
    # Adicionando Lucro (como você não tem gasto por SubID no CSV, simulamos Lucro = Comissão)
    tab_unificada['Lucro'] = tab_unificada['Comissão Líquida']
    
    st.dataframe(tab_unificada.style.format({
        'Comissão Líquida': 'R$ {:.2f}', 
        'Valor Total': 'R$ {:.2f}', 
        'Lucro': 'R$ {:.2f}'
    }), use_container_width=True)
else:
    st.info("Suba o arquivo para ver a tabela unificada.")

st.markdown("---")

# EVOLUÇÃO DE VENDAS (GRÁFICO MELHORADO)
st.subheader("Evolução de Vendas")
if not df.empty:
    df['Horário do pedido'] = pd.to_datetime(df['Horário do pedido'])
    # Agrupando por hora ou dia para o gráfico não ficar uma linha reta
    vendas_tempo = df_validos.copy()
    vendas_tempo['Hora'] = pd.to_datetime(vendas_tempo['Horário do pedido']).dt.strftime('%H:00')
    graf_data = vendas_tempo.groupby('Hora')['Comissão líquida do afiliado(R$)'].sum().reset_index()
    
    fig = px.area(graf_data, x='Hora', y='Comissão líquida do afiliado(R$)', 
                 template="plotly_dark", line_shape="spline",
                 color_discrete_sequence=['#ff4b4b'])
    
    fig.update_layout(yaxis_title="Comissão (R$)", xaxis_title="Hora do Pedido")
    st.plotly_chart(fig, use_container_width=True)
