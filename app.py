import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import time
import requests
import json
from datetime import date, timedelta

# --- 1. SETUP DE DESIGN PREMIUM ---
st.set_page_config(page_title="AfiliadoDash PRO | API Live", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    div[data-testid="metric-container"] {
        background-color: #161b22; border: 1px solid #30363d;
        padding: 20px; border-radius: 12px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricValue"] > div { color: #ffffff !important; font-size: 26px !important; }
    div[data-testid="stMetricLabel"] > label { color: #8b949e !important; }
    h1, h2, h3 { color: white !important; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0e1117; border-right: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

hoje_pc = date.today()

# --- 2. FUNÇÃO API SHOPEE (COM ASSINATURA CORRIGIDA) ---
def buscar_vendas_shopee_api(data_ini, data_fim):
    try:
        # Puxa as chaves cadastradas no Secrets do Streamlit
        app_id = st.secrets["SHOPEE_APP_ID"]
        secret = st.secrets["SHOPEE_SECRET"]
        timestamp = int(time.time())
        
        url = "https://open.shopee.com.br/api/v2/affiliate/get_order_list"
        
        # 1. Monta o pedido de datas
        payload = {
            "start_time": int(time.mktime(data_ini.timetuple())),
            "end_time": int(time.mktime(data_fim.timetuple())),
            "limit": 100
        }
        
        # 2. Converte o pedido para string sem espaços (Exigência Shopee)
        payload_str = json.dumps(payload, separators=(',', ':'))
        
        # 3. Gera a assinatura misturando AppID + Timestamp + Payload + Secret
        base_string = f"{app_id}{timestamp}{payload_str}{secret}"
        signature = hashlib.sha256(base_string.encode('utf-8')).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"SHA256 {signature}",
            "Timestamp": str(timestamp),
            "AppID": app_id
        }
        
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        return r.json()
        
    except Exception as e:
        return {"error": "Falha no Python", "detalhe": str(e)}

# --- 3. FUNÇÃO LEITURA DE CSV (BACKUP E CLIQUES) ---
def ler_csv_shopee(file):
    if file is None: return pd.DataFrame()
    try:
        df = pd.read_csv(file, encoding='utf-8')
    except:
        file.seek(0)
        df = pd.read_csv(file, sep=';', encoding='latin-1')
    return df

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    st.divider()
    
    modo = st.radio("📡 Fonte de Vendas", ["API Automática", "CSV (Backup)"])
    
    arquivo_v = None
    if modo == "CSV (Backup)":
        arquivo_v = st.file_uploader("📥 Subir CSV de Vendas", type=['csv'])
        
    st.markdown("---")
    arquivo_c = st.file_uploader("🖱️ Subir CSV de Cliques (P/ Conversão)", type=['csv'])
        
    st.divider()
    data_sel = st.date_input("📅 Filtro de Período", 
                            value=[hoje_pc - timedelta(days=7), hoje_pc], 
                            max_value=hoje_pc)

# --- 5. PROCESSAMENTO DE DADOS ---
vendas_b, pedidos_t, comissao_t, cliques_t = 0.0, 0, 0.0, 0
df_v_filtrado = pd.DataFrame()
start_d, end_d = (data_sel[0], data_sel[1]) if len(data_sel) == 2 else (hoje_pc, hoje_pc)

# Lógica de Vendas
if modo == "API Automática":
    with st.spinner("Sincronizando com a Shopee..."):
        dados = buscar_vendas_shopee_api(start_d, end_d)
        
        # Modo Detetive: Se der sucesso, processa. Se der erro, mostra na tela.
        if dados and 'data' in dados and 'order_list' in dados['data']:
            df_v_filtrado = pd.DataFrame(dados['data']['order_list'])
            if not df_v_filtrado.empty:
                vendas_b = df_v_filtrado['order_price'].sum()
                pedidos_t = len(df_v_filtrado)
                comissao_t = df_v_filtrado['commission'].sum()
        else:
            st.error("⚠️ A API retornou um erro. Copie o texto abaixo e me mande:")
            st.json(dados) # Isso mostra o erro real para arrumarmos
            
else: # Modo CSV
    if arquivo_v:
        df_v = ler_csv_shopee(arquivo_v)
        if 'Horário do pedido' in df_v.columns:
            df_v['Data_Simples'] = pd.to_datetime(df_v['Horário do pedido']).dt.date
            df_v_filtrado = df_v[(df_v['Data_Simples'] >= start_d) & (df_v['Data_Simples'] <= end_d)]
            validos = df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado']
            vendas_b = validos['Preço(R$)'].sum()
            pedidos_t = len(validos)
            comissao_t = validos['Comissão líquida do afiliado(R$)'].sum()

# Lógica de Cliques (Sempre CSV)
if arquivo_c:
    df_c = ler_csv_shopee(arquivo_c)
    colunas_data_c = [c for c in df_c.columns if 'Data' in c or 'Date' in c or 'Tempo' in c or 'Horário' in c]
    if colunas_data_c:
        df_c['Data_Simples'] = pd.to_datetime(df_c[colunas_data_c[0]]).dt.date
        df_c_filtrado = df_c[(df_c['Data_Simples'] >= start_d) & (df_c['Data_Simples'] <= end_d)]
        col_cliques = [c for c in df_c.columns if 'Clique' in c or 'Clicks' in c or 'Qtd' in c]
        cliques_t = df_c_filtrado[col_cliques[0]].sum() if col_cliques else len(df_c_filtrado)

# Cálculos Finais
ticket = vendas_b / pedidos_t if pedidos_t > 0 else 0
conv = (pedidos_t / cliques_t * 100) if cliques_t > 0 else 0

# --- 6. TELA PRINCIPAL ---
st.title("Dashboard de Visão Geral")
st.caption(f"Período: {start_d.strftime('%d/%m/%Y')} até {end_d.strftime('%d/%m/%Y')}")

# LINHA 1: METRICAS
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Vendas Totais", f"R$ {vendas_b:.2f}")
m2.metric("Pedidos", pedidos_t)
m3.metric("Comissão Líquida", f"R$ {comissao_t:.2f}")
m4.metric("Ticket Médio", f"R$ {ticket:.2f}")
m5.metric("Cliques Totais", cliques_t)
m6.metric("Conversão", f"{conv:.2f}%")

st.divider()

# LINHA 2: TABELA E GRÁFICO
if not df_v_filtrado.empty:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📊 Análise Unificada (SubID)")
        col_sub = 'Sub_id1' if 'Sub_id1' in df_v_filtrado.columns else ('sub_id' if 'sub_id' in df_v_filtrado.columns else df_v_filtrado.columns[0])
        col_comissao = 'Comissão líquida do afiliado(R$)' if 'Comissão líquida do afiliado(R$)' in df_v_filtrado.columns else 'commission'
        
        tab = df_v_filtrado.groupby(col_sub).agg(
            Pedidos=(col_sub, 'count'),
            Comissao=(col_comissao, 'sum')
        ).reset_index()
        tab.columns = ['SubID', 'Pedidos', 'Comissão (R$)']
        st.dataframe(tab.style.format({'Comissão (R$)': 'R$ {:.2f}'}), use_container_width=True)
        
    with c2:
        st.subheader("🎯 Vendas por Canal")
        col_canal = 'Canal' if 'Canal' in df_v_filtrado.columns else ('source' if 'source' in df_v_filtrado.columns else None)
        if col_canal:
            fig = px.pie(df_v_filtrado, names=col_canal, values=col_comissao, hole=0.6, template="plotly_dark", color_discrete_sequence=['#ff4b4b', '#ff6d00', '#00c853'])
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Evolução da Comissão (Montanha)")
    col_data_evolucao = 'Data_Simples' if 'Data_Simples' in df_v_filtrado.columns else 'create_time'
    # Se a API retornar unix timestamp (números), converte para data
    if pd.api.types.is_numeric_dtype(df_v_filtrado[col_data_evolucao]):
        df_v_filtrado['Data_Real'] = pd.to_datetime(df_v_filtrado[col_data_evolucao], unit='s').dt.date
    else:
        df_v_filtrado['Data_Real'] = df_v_filtrado[col_data_evolucao]
        
    evolucao = df_v_filtrado.groupby('Data_Real')[col_comissao].sum().reset_index()
    evolucao.columns = ['Data', 'Comissão']
    
    fig_a = px.area(evolucao, x='Data', y='Comissão', template="plotly_dark", color_discrete_sequence=['#00c853'], markers=True)
    fig_a.update_traces(line_shape='spline')
    fig_a.update_layout(yaxis_title="Comissão (R$)", xaxis_title="Dia", height=400)
    st.plotly_chart(fig_a, use_container_width=True)
else:
    st.info("Aguardando os dados da API ou do arquivo CSV.")
