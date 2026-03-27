import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import time
import requests
import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# --- 1. SETUP DE DESIGN PREMIUM CLEAR ---
st.set_page_config(page_title="AfiliadoDash PRO | API GraphQL", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOMIZADO PARA LAYOUT PREMIUM ---
st.markdown("""
<style>
    /* Estilos Gerais */
    .main { background-color: #f0f2f5; }
    h1, h2, h3 { color: #1e1e1e !important; font-family: 'Inter', sans-serif; font-weight: 700; }
    .stCaption { color: #6c757d !important; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e5e5e5; }
    [data-testid="stSidebar"] .stMarkdown { color: #333 !important; font-weight: 500; }
    
    /* Cards de Métricas */
    .metric-card {
        background-color: #ffffff; border: none;
        padding: 24px; border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 24px;
        display: flex; flex-direction: column; justify-content: space-between;
        border-top: 3px solid transparent;
    }
    .metric-card:hover { border-top: 3px solid #ff4b4b; transition: 0.2s; }
    .metric-title { color: #6c757d; font-size: 13px; margin-bottom: 8px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}
    .metric-value { color: #1e1e1e; font-size: 28px; font-weight: 800; margin-bottom: 8px; }
    .metric-sub { color: #28a745; font-size: 12px; font-weight: 600; background: #e6f4ea; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content; margin-bottom: 4px;} 
    .metric-sub-text { color: #6c757d; font-size: 12px;}
    
    /* Cartões de TOP SubID */
    .top-subid-card {
        background-color: #ffffff; border: none;
        padding: 24px; border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .top-subid-item {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 12px;
    }
    .top-subid-label { font-size: 14px; color: #6c757d; font-weight: 500;}
    .top-subid-value { font-size: 14px; color: #1e1e1e; font-weight: 700; }
    .top-subid-bar {
        height: 8px; border-radius: 4px;
        background-color: #28a745; 
    }
</style>
""", unsafe_allow_html=True)

hoje_pc = date.today()

# --- 2. FUNÇÃO API SHOPEE (QUERY REVERTIDA PARA A VERSÃO BLINDADA) ---
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
        
        # Query blindada exigida pela Shopee (Sem purchaseAmount e customParameters)
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

# --- 4. SIDEBAR E CONFIGURAÇÃO ---
with st.sidebar:
    st.markdown("<h2 style='color: #ff4b4b; text-align: center;'>🟠 AfiliadoDash</h2>", unsafe_allow_html=True)
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
        ["Últimos 30 dias", "Ontem", "Anteontem", "Trechos de dias"],
        help="O plano permite consultar até 3 dias para intervalos livres."
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
        arquivo_v = st.file_uploader("📥 Subir CSV de Vendas", type=['csv'])
        
    arquivo_c = st.file_uploader("🖱️ Subir CSV de Cliques (P/ Conversão)", type=['csv'])
        
    api_endpoint = st.secrets.get("SHOPEE_GRAPHQL_ENDPOINT", "https://open-api.affiliate.shopee.com.br/graphql")
    
    with st.expander("⚙️ Configuração Avançada", expanded=False):
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
                        'subId1': "Sem Sub ID (API)",
                        'order_price': 0.0 # API não retorna
                    })
                    
                df_v_filtrado = pd.DataFrame(flat_nodes)
                
                if 'conversionStatus' in df_v_filtrado.columns:
                    df_v_filtrado = df_v_filtrado[~df_v_filtrado['conversionStatus'].isin(['Cancelled', 'Rejected', 'Invalid'])]
                
                vendas_b = df_v_filtrado['order_price'].sum()
                pedidos_t = len(df_v_filtrado)
                comissao_t = df_v_filtrado['commission'].sum()
        else:
            st.error(f"⚠️ Resposta do Servidor:")
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
st.markdown("<h1>Dashboard <span style='font-size: 14px; background-color: #ff4b4b; color: white; padding: 4px 12px; border-radius: 20px; vertical-align: middle; margin-left: 10px;'>Primeiros Passos ▶</span></h1>", unsafe_allow_html=True)

# --- LINHA 1: CARDS (HTML/CSS) ---
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Vendas Totais</div>
        <div class="metric-value">R$ {vendas_b:.2f}</div>
        <div>
            <span class="metric-sub">↑ 0.0%</span><br>
            <span class="metric-sub-text">Anterior: R$ 0.00</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Pedidos</div>
        <div class="metric-value">{pedidos_t}</div>
        <div>
            <span class="metric-sub">↑ 0.0%</span><br>
            <span class="metric-sub-text">Itens vendidos: {pedidos_t}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Comissão Líquida</div>
        <div class="metric-value">R$ {comissao_t:.2f}</div>
        <div>
            <span class="metric-sub">↑ 0.0%</span><br>
            <span class="metric-sub-text">Anterior: R$ 0.00</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Ticket Médio</div>
        <div class="metric-value">R$ {ticket:.2f}</div>
        <div>
            <span class="metric-sub">↑ 0.0%</span><br>
            <span class="metric-sub-text">Anterior: R$ 0.00</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Comissão a validar</div>
        <div class="metric-value">R$ {comissao_t:.2f}</div>
        <div>
            <span class="metric-sub-text" style="color: #28a745; font-weight: bold;">Validadas a receber: R$ 0.00</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- LINHA 2: GRÁFICOS E TABELAS ---
if not df_v_filtrado.empty:
    st.markdown("<div style='background: white; padding: 20px; border-radius: 12px; margin-top: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 14px; color: #1e1e1e; text-transform: uppercase;'>Evolução da Comissão</h3>", unsafe_allow_html=True)
    
    col_data_evolucao = 'purchaseTime' if 'purchaseTime' in df_v_filtrado.columns else 'Data_Simples'
    col_comissao = 'commission' if 'commission' in df_v_filtrado.columns else 'Comissão líquida do afiliado(R$)'
    
    if pd.api.types.is_numeric_dtype(df_v_filtrado[col_data_evolucao]):
        df_v_filtrado['Data_Real'] = pd.to_datetime(df_v_filtrado[col_data_evolucao], unit='s').dt.date
    else:
        df_v_filtrado['Data_Real'] = df_v_filtrado[col_data_evolucao]
        
    evolucao = df_v_filtrado.groupby('Data_Real')[col_comissao].sum().reset_index()
    evolucao.columns = ['Data', 'Comissão']
    
    # Gráfico de linhas pontilhadas como na sua imagem
    fig_a = px.line(evolucao, x='Data', y='Comissão', template="plotly_white", markers=True, color_discrete_sequence=['#28a745'])
    fig_a.update_traces(marker=dict(size=10))
    fig_a.update_layout(
        yaxis_title="", xaxis_title="", height=350, 
        margin=dict(l=0, r=0, t=20, b=0),
        yaxis=dict(showgrid=True, griddash='dash', gridcolor='#e5e5e5'),
        xaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig_a, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Cards de SubID (Mocados pois a API oculta isso)
    st.write("")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="top-subid-card">
            <div style="font-size: 12px; font-weight: bold; color: #1e1e1e; margin-bottom: 20px;">TOP SUBID 1 (COMISSÃO)</div>
            <div class="top-subid-item">
                <div class="top-subid-label">Sem Sub ID</div>
                <div class="top-subid-value">R$ {comissao_t:.2f}</div>
            </div>
            <div class="top-subid-bar" style="background-color: #a855f7;"></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="top-subid-card">
            <div style="font-size: 12px; font-weight: bold; color: #1e1e1e; margin-bottom: 20px;">TOP SUBID 2 (COMISSÃO)</div>
            <div class="top-subid-item">
                <div class="top-subid-label">-</div>
                <div class="top-subid-value">R$ 0.00</div>
            </div>
            <div class="top-subid-bar" style="background-color: #f97316;"></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="top-subid-card">
            <div style="font-size: 12px; font-weight: bold; color: #1e1e1e; margin-bottom: 20px;">TOP SUBID 3 (COMISSÃO)</div>
            <div class="top-subid-item">
                <div class="top-subid-label">-</div>
                <div class="top-subid-value">R$ 0.00</div>
            </div>
            <div class="top-subid-bar" style="background-color: #3b82f6;"></div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Aguardando os dados da API ou do arquivo CSV.")
