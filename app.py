import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import time
import requests
import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# --- 1. SETUP DE DESIGN PREMIUM DARK ---
st.set_page_config(page_title="AfiliadoDash PRO | API Live", layout="wide", initial_sidebar_state="expanded")

# --- CSS COMPLETAMENTE REFEITO (ULTRA DARK MODERN) ---
st.markdown("""
<style>
    /* Fundos e Textos Gerais */
    .stApp { background-color: #09090b !important; }
    .main { background-color: #09090b !important; }
    h1, h2, h3, h4 { color: #fafafa !important; font-family: 'Inter', sans-serif; font-weight: 700; letter-spacing: -0.5px; }
    
    /* Esconder elementos nativos do Streamlit para visual mais limpo */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0f0f13 !important; border-right: 1px solid #27272a; }
    [data-testid="stSidebar"] .stMarkdown { color: #a1a1aa !important; font-weight: 500; font-size: 14px; }
    hr { border-color: #27272a !important; }
    
    /* Cards de Métricas Principais */
    .dash-card {
        background: linear-gradient(145deg, #121214, #0e0e11);
        border: 1px solid #27272a;
        padding: 24px; 
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        transition: transform 0.2s ease, border-color 0.2s ease;
        display: flex; flex-direction: column; justify-content: space-between;
        height: 100%;
    }
    .dash-card:hover {
        border-color: #ef4444;
        transform: translateY(-3px);
    }
    .card-title { color: #a1a1aa; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;}
    .card-value { color: #ffffff; font-size: 32px; font-weight: 800; margin-bottom: 16px; line-height: 1; }
    .card-footer { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #71717a; font-weight: 500;}
    .badge-up { background: rgba(34, 197, 94, 0.15); color: #4ade80; padding: 4px 8px; border-radius: 6px; font-weight: 700; }
    
    /* Seção do Gráfico */
    .chart-container {
        background-color: #121214;
        border: 1px solid #27272a;
        border-radius: 16px;
        padding: 24px;
        margin-top: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    
    /* Cards de TOP SubID */
    .subid-card {
        background-color: #121214; 
        border: 1px solid #27272a;
        padding: 24px; 
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        margin-top: 24px;
    }
    .subid-header { font-size: 12px; color: #a1a1aa; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }
    .subid-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .subid-name { color: #e4e4e7; font-size: 14px; font-weight: 600; }
    .subid-val { color: #fafafa; font-size: 16px; font-weight: 800; }
    .progress-bg { background-color: #27272a; border-radius: 8px; height: 6px; width: 100%; overflow: hidden; }
    .progress-bar { height: 100%; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

hoje_pc = date.today()

# --- 2. FUNÇÃO API SHOPEE (BLINDADA) ---
def buscar_vendas_shopee_api(data_ini, data_fim, url_api):
    if not url_api or url_api == "":
        return {"error": "Aviso do Sistema", "detalhe": "URL da API não configurada na barra lateral!"}
        
    try:
        app_id = st.secrets.get("SHOPEE_APP_ID")
        secret = st.secrets.get("SHOPEE_SECRET")
        
        if not app_id or not secret:
            return {"error": "Aviso do Sistema", "detalhe": "Credenciais SHOPEE_APP_ID e SHOPEE_SECRET não configuradas nos Secrets!"}
            
        timestamp = int(time.time())
        start_ts = int(time.mktime(data_ini.timetuple()))
        end_ts = int(time.mktime((data_fim + timedelta(days=1)).timetuple())) - 1
        
        graphql_query = f"""
        {{
          conversionReport(purchaseTimeStart: {start_ts}, purchaseTimeEnd: {end_ts}) {{
            nodes {{
              purchaseTime
              conversionStatus
              netCommission
              estimatedTotalCommission
            }}
          }}
        }}
        """
        
        payload = {"query": graphql_query.strip()}
        payload_str = json.dumps(payload, separators=(',', ':'))
        
        base_string = f"{app_id}{timestamp}{payload_str}{secret}"
        signature = hashlib.sha256(base_string.encode('utf-8')).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"
        }
        
        r = requests.post(url_api, data=payload_str, headers=headers, timeout=20)
            
        try:
            return r.json()
        except:
            return {"error": "Erro de Leitura", "status": r.status_code, "texto": r.text}
            
    except Exception as e:
        return {"error": "Falha no Python", "detalhe": str(e)}

# --- 3. FUNÇÃO LEITURA DE CSV ---
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
    st.markdown("<h2 style='color: #ef4444; text-align: center; margin-bottom: 0;'>🟠 AfiliadoDash</h2>", unsafe_allow_html=True)
    st.divider()
    
    st.markdown("🔸 **Dashboard**")
    st.markdown("📅 Análise do Dia")
    st.markdown("🖱️ Análise de Cliques")
    st.markdown("📢 Meta Ads")
    st.markdown("🔗 Gerador de links")
    st.markdown("📊 Análise de Links")
    st.markdown("📤 Upload")
    st.markdown("⚙️ Integrações")
    
    st.divider()
    
    opcao_data = st.selectbox(
        "📅 Filtro de Período",
        ["Últimos 30 dias", "Ontem", "Anteontem", "Trechos de dias"]
    )
    
    if opcao_data == "Ontem":
        start_d, end_d = hoje_pc - timedelta(days=1), hoje_pc - timedelta(days=1)
    elif opcao_data == "Anteontem":
        start_d, end_d = hoje_pc - timedelta(days=2), hoje_pc - timedelta(days=2)
    elif opcao_data == "Últimos 30 dias":
        start_d, end_d = hoje_pc - relativedelta(days=30), hoje_pc
    else: 
        data_sel = st.date_input("Escolha as datas", value=[hoje_pc - timedelta(days=3), hoje_pc], max_value=hoje_pc)
        if len(data_sel) == 2:
            start_d, end_d = data_sel[0], data_sel[1]
        else:
             start_d, end_d = (hoje_pc, hoje_pc)
    
    st.divider()
    modo = st.radio("📡 Fonte de Vendas", ["API Automática", "CSV (Backup)"])
    
    arquivo_v = None
    if modo == "CSV (Backup)":
        arquivo_v = st.file_uploader("📥 CSV Vendas", type=['csv'])
        
    arquivo_c = st.file_uploader("🖱️ CSV Cliques", type=['csv'])
        
    api_endpoint = st.secrets.get("SHOPEE_GRAPHQL_ENDPOINT", "https://open-api.affiliate.shopee.com.br/graphql")
    
    with st.expander("⚙️ Dev Tools", expanded=False):
        st.text_input("Endpoint", value=api_endpoint, disabled=True)

# --- 5. PROCESSAMENTO DE DADOS ---
vendas_b, pedidos_t, comissao_t, cliques_t = 0.0, 0, 0.0, 0
df_v_filtrado = pd.DataFrame()

if modo == "API Automática":
    with st.spinner("Sincronizando..."):
        dados = buscar_vendas_shopee_api(start_d, end_d, api_endpoint)
        
        if dados and 'data' in dados and 'conversionReport' in dados['data']:
            nodes = dados['data']['conversionReport']['nodes']
            if nodes:
                flat_nodes = []
                for n in nodes:
                    comissao = n.get('netCommission') or n.get('estimatedTotalCommission') or 0
                    flat_nodes.append({
                        'purchaseTime': n.get('purchaseTime'),
                        'conversionStatus': n.get('conversionStatus'),
                        'commission': float(comissao),
                        'subId1': "Sem Sub ID",
                        'order_price': 0.0 
                    })
                    
                df_v_filtrado = pd.DataFrame(flat_nodes)
                
                if 'conversionStatus' in df_v_filtrado.columns:
                    df_v_filtrado = df_v_filtrado[~df_v_filtrado['conversionStatus'].isin(['Cancelled', 'Rejected', 'Invalid'])]
                
                vendas_b = df_v_filtrado['order_price'].sum()
                pedidos_t = len(df_v_filtrado)
                comissao_t = df_v_filtrado['commission'].sum()
        else:
            st.error("Falha ao comunicar com a Shopee.")
            st.json(dados) 
            
else: 
    if arquivo_v:
        df_v = ler_csv_shopee(arquivo_v)
        if 'Horário do pedido' in df_v.columns:
            df_v['Data_Simples'] = pd.to_datetime(df_v['Horário do pedido']).dt.date
            df_v_filtrado = df_v[(df_v['Data_Simples'] >= start_d) & (df_v['Data_Simples'] <= end_d)]
            validos = df_v_filtrado[df_v_filtrado['Status do Pedido'] != 'Cancelado']
            vendas_b = validos['Preço(R$)'].sum()
            pedidos_t = len(validos)
            comissao_t = validos['Comissão líquida do afiliado(R$)'].sum()

if arquivo_c:
    df_c = ler_csv_shopee(arquivo_c)
    colunas_data_c = [c for c in df_c.columns if 'Data' in c or 'Date' in c or 'Tempo' in c or 'Horário' in c]
    if colunas_data_c:
        df_c['Data_Simples'] = pd.to_datetime(df_c[colunas_data_c[0]]).dt.date
        df_c_filtrado = df_c[(df_c['Data_Simples'] >= start_d) & (df_c['Data_Simples'] <= end_d)]
        col_cliques = [c for c in df_c.columns if 'Clique' in c or 'Clicks' in c or 'Qtd' in c]
        cliques_t = df_c_filtrado[col_cliques[0]].sum() if col_cliques else len(df_c_filtrado)

ticket = vendas_b / pedidos_t if pedidos_t > 0 else 0
conv = (pedidos_t / cliques_t * 100) if cliques_t > 0 else 0

# --- 6. TELA PRINCIPAL ---

# Título Limpo
st.markdown("<h1 style='margin-bottom: 24px;'>Dashboard</h1>", unsafe_allow_html=True)

# LINHA 1: CARDS DE MÉTRICAS ULTRA DARK
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.markdown(f"""
    <div class="dash-card">
        <div class="card-title">Vendas Totais</div>
        <div class="card-value">R$ {vendas_b:.2f}</div>
        <div class="card-footer">
            <span class="badge-up">↑ 0.0%</span> Anterior: R$ 0.00
        </div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="dash-card">
        <div class="card-title">Pedidos Feitos</div>
        <div class="card-value">{pedidos_t}</div>
        <div class="card-footer">
            <span class="badge-up">↑ 0.0%</span> Itens: {pedidos_t}
        </div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="dash-card">
        <div class="card-title">Comissão Líquida</div>
        <div class="card-value" style="color: #4ade80;">R$ {comissao_t:.2f}</div>
        <div class="card-footer">
            <span class="badge-up">↑ 0.0%</span> Anterior: R$ 0.00
        </div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="dash-card">
        <div class="card-title">Ticket Médio</div>
        <div class="card-value">R$ {ticket:.2f}</div>
        <div class="card-footer">
            <span class="badge-up">↑ 0.0%</span> Anterior: R$ 0.00
        </div>
    </div>
    """, unsafe_allow_html=True)

with m5:
    st.markdown(f"""
    <div class="dash-card">
        <div class="card-title">Comissão a Validar</div>
        <div class="card-value">R$ {comissao_t:.2f}</div>
        <div class="card-footer">
            <span style="color: #4ade80;">✔ Validadas: R$ 0.00</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# LINHA 2: GRÁFICO E TABELAS
if not df_v_filtrado.empty:
    
    # --- ÁREA DO GRÁFICO ---
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.markdown("<div class='subid-header'>EVOLUÇÃO DA COMISSÃO</div>", unsafe_allow_html=True)
    
    col_data_evolucao = 'purchaseTime' if 'purchaseTime' in df_v_filtrado.columns else 'Data_Simples'
    col_comissao = 'commission' if 'commission' in df_v_filtrado.columns else 'Comissão líquida do afiliado(R$)'
    
    if pd.api.types.is_numeric_dtype(df_v_filtrado[col_data_evolucao]):
        df_v_filtrado['Data_Real'] = pd.to_datetime(df_v_filtrado[col_data_evolucao], unit='s').dt.date
    else:
        df_v_filtrado['Data_Real'] = df_v_filtrado[col_data_evolucao]
        
    evolucao = df_v_filtrado.groupby('Data_Real')[col_comissao].sum().reset_index()
    evolucao.columns = ['Data', 'Comissão']
    
    fig_a = px.line(evolucao, x='Data', y='Comissão', template="plotly_dark", markers=True, color_discrete_sequence=['#4ade80'])
    fig_a.update_traces(marker=dict(size=8, line=dict(width=2, color='#121214')), line=dict(width=3))
    fig_a.update_layout(
        yaxis_title="", xaxis_title="", height=360, 
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(showgrid=True, griddash='dash', gridcolor='#27272a', zeroline=False),
        xaxis=dict(showgrid=False, zeroline=False)
    )
    st.plotly_chart(fig_a, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- ÁREA DOS SUB IDs ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="subid-card">
            <div class="subid-header">TOP SUBID 1</div>
            <div class="subid-row">
                <span class="subid-name">Sem Sub ID</span>
                <span class="subid-val">R$ {comissao_t:.2f}</span>
            </div>
            <div class="progress-bg"><div class="progress-bar" style="width: 100%; background-color: #a855f7;"></div></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="subid-card">
            <div class="subid-header">TOP SUBID 2</div>
            <div class="subid-row">
                <span class="subid-name">-</span>
                <span class="subid-val">R$ 0.00</span>
            </div>
            <div class="progress-bg"><div class="progress-bar" style="width: 0%; background-color: #f97316;"></div></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="subid-card">
            <div class="subid-header">TOP SUBID 3</div>
            <div class="subid-row">
                <span class="subid-name">-</span>
                <span class="subid-val">R$ 0.00</span>
            </div>
            <div class="progress-bg"><div class="progress-bar" style="width: 0%; background-color: #3b82f6;"></div></div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Aguardando os dados da API ou do arquivo CSV.")
