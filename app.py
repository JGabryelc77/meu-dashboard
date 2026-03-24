import streamlit as st
import pandas as pd
from datetime import date

# Configuração da Página
st.set_page_config(page_title="Afiliado Dash", layout="wide")

st.title("📊 Painel de Tráfego - Vídeos Dark")

# --- BARRA LATERAL (UPLOADS) ---
st.sidebar.header("📁 Importar Dados (Shopee)")
arquivo_vendas = st.sidebar.file_uploader("Importar CSV de Vendas", type=['csv'])
arquivo_cliques = st.sidebar.file_uploader("Importar CSV de Cliques", type=['csv'])

# --- LÓGICA DE PROCESSAMENTO ---
vendas_totais = 0.0
total_pedidos = 0
total_cliques = 0

if arquivo_vendas is not None:
    df_vendas = pd.read_csv(arquivo_vendas)
    # Aqui o código soma a coluna de comissão (ajustaremos o nome da coluna conforme o seu arquivo)
    # Por enquanto, vamos simular que ele achou os dados:
    vendas_totais = 150.75 # Exemplo simulado
    total_pedidos = len(df_vendas)

if arquivo_cliques is not None:
    df_cliques = pd.read_csv(arquivo_cliques)
    total_cliques = len(df_cliques)

# --- INTERFACE PRINCIPAL ---
st.subheader("Resumo de Hoje")
col1, col2, col3, col4 = st.columns(4)

# Como o Facebook deu erro no SMS, vamos deixar um campo manual temporário para investimento
investimento_manual = st.number_input("Digite seu gasto no Meta (US$)", min_value=0.0, value=0.0)

col1.metric("Investimento (Meta)", f"US$ {investimento_manual:.2f}")
col2.metric("Vendas (Shopee)", f"R$ {vendas_totais:.2f}")
col3.metric("Total Pedidos", total_pedidos)
col4.metric("Cliques Shopee", total_cliques)

st.divider()

if investimento_manual > 0 or vendas_totais > 0:
    st.success(f"Análise: Com R$ {vendas_totais:.2f} em vendas e US$ {investimento_manual:.2f} de gasto, seu dashboard está pronto!")
