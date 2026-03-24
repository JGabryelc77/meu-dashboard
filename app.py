import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import hmac
import time
import requests
import json
from datetime import date, datetime, timedelta

# 1. SETUP DE DESIGN PREMIUM
st.set_page_config(page_title="AfiliadoDash | API Live", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    div[data-testid="metric-container"] {
        background-color: #161b22; border: 1px solid #30363d;
        padding: 20px; border-radius: 12px;
    }
    h1, h2, h3 { color: white !important; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO MESTRE DA API SHOPEE ---
def buscar_vendas_shopee_api(data_ini, data_fim):
    app_id = st.secrets["SHOPEE_APP_ID"]
    secret = st.secrets["SHOPEE_SECRET"]
    timestamp = int(time.time())
    
    # Gerando a Assinatura (Signature) exigida pela Shopee
    base_string = f"{app_id}{timestamp}{secret}"
    signature = hashlib.sha256(base_string.encode()).hexdigest()
    
    url = "https://open.shopee.com.br/api/v2/affiliate/get_order_list"
    
    payload = {
        "start_time": int(time.mktime(data_ini.timetuple())),
        "end_time": int(time.mktime(data_fim.timetuple())),
        "limit": 100
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 {signature}",
        "Timestamp": str(timestamp),
        "AppID": app_id
    }
    
    try:
        # Nota: Caso sua conta ainda esteja em Sandbox, a URL pode precisar de ajuste
        r = requests.post(url, json=payload, headers=headers)
        return r.json()
    except:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    st.divider()
    
    # Modo de Operação
    modo = st.radio("Fonte de Dados", ["API Automática", "Upload de CSV (Backup)"])
    
    arquivo_v = None
    if modo == "Upload de CSV (Backup)":
        arquivo_v = st.file_uploader("Subir Vendas CSV")
        
    st.divider()
    hoje = date.today()
    data_sel = st.date_input("📅 Filtro de Período", value=[hoje - timedelta(days=7), hoje], max_value=hoje)

# --- INICIALIZAÇÃO DE MÉTRICAS ---
vendas_b, pedidos_t, comissao_t = 0.0, 0, 0.0
df_v = pd.DataFrame()

# --- LÓGICA DE PROCESSAMENTO ---
start_d, end_d = (data_sel[0], data_sel[1]) if len(data_sel) == 2 else (hoje, hoje)

if modo == "API Automática":
    with st.spinner('Conectando à API da Shopee...'):
        dados_api = buscar_vendas_shopee_api(start_d, end_d)
        if dados_api and 'data' in dados_api:
            df_v = pd.DataFrame(dados_api['data']['order_list'])
            # Mapeamento de colunas da API para o Dashboard
            if not df_v.empty:
                comissao_t = df_v['commission'].sum()
                pedidos_t = len(df_v)
                vendas_b = df_v['order_price'].sum()
        else:
            st.error("Erro na API: Verifique se sua chave está em modo 'Live' na Shopee.")

elif modo == "Upload de CSV (Backup)" and arquivo_v:
    df_v = pd.read_csv(arquivo_v)
    df_v['Data_Simples'] = pd.to_datetime(df_v['Horário do pedido']).dt.date
    df_v = df_v[(df_v['Data_Simples'] >= start_d) & (df_v['Data_Simples'] <= end_d)]
    df_validos = df_v[df_v['Status do Pedido'] != 'Cancelado']
    vendas_b = df_validos['Preço(R$)'].sum()
    pedidos_t = len(df_validos)
    comissao_t = df_validos['Comissão líquida do afiliado(R$)'].sum()

# --- TELA PRINCIPAL (ESTRUTURA IDENTICA) ---
st.title("Dashboard de Visão Geral")

# LINHA 1: CARDS
m1, m2, m3, m4 = st.columns(4)
m1.metric("Vendas Totais", f"R$ {vendas_b:.2f}")
m2.metric("Pedidos", pedidos_t)
m3.metric("Comissão Líquida", f"R$ {comissao_t:.2f}")
m4.metric("Ticket Médio", f"R$ {vendas_b/pedidos_t if pedidos_t > 0 else 0:.2f}")

st.divider()

if not df_v.empty:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📊 Análise por SubID")
        # Ajusta nome da coluna dependendo se é API ou CSV
        col_sub = 'Sub_id1' if 'Sub_id1' in df_v.columns else 'sub_id'
        tab = df_v.groupby(col_sub).agg({'ID do pedido':'count', 'Preço(R$)':'sum'}).reset_index() if 'Sub_id1' in df_v.columns else df_v
        st.dataframe(tab, use_container_width=True)
    
    with c2:
        st.subheader("🎯 Por Canal")
        col_canal = 'Canal' if 'Canal' in df_v.columns else 'source'
        if col_canal in df_v.columns:
            fig = px.pie(df_v, names=col_canal, hole=0.6, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Evolução da Comissão")
    # Gráfico de Montanha
    fig_a = px.area(df_v, y=df_v.columns[0], template="plotly_dark", color_discrete_sequence=['#00c853'])
    fig_a.update_traces(line_shape='spline')
    st.plotly_chart(fig_a, use_container_width=True)
else:
    st.info("Aguardando dados da API ou do CSV para preencher a estrutura.")
