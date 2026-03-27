import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import time
import requests
import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# --- 1. SETUP DA PÁGINA ---
st.set_page_config(page_title="Nexus Analytics | Shopee", layout="wide", initial_sidebar_state="expanded")

# --- CSS COMPLETAMENTE NOVO (ESTILO VERCEL / MINIMALISTA HIGH-TECH) ---
st.markdown("""
<style>
    /* Reset e Fundos */
    .stApp, .main { background-color: #000000 !important; }
    h1, h2, h3, h4 { color: #ededed !important; font-family: 'Inter', sans-serif; font-weight: 600; letter-spacing: -0.05em; }
    
    /* Esconder elementos nativos */
    header, #MainMenu { visibility: hidden; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0a0a0a !important; border-right: 1px solid #333333; }
    [data-testid="stSidebar"] * { color: #a1a1aa !important; }
    hr { border-color: #333333 !important; }
    
    /* Input Fields Native Streamlit */
    .stSelectbox > div > div { background-color: #111111; color: #ededed; border: 1px solid #333333; }
    .stDateInput > div > div { background-color: #111111; color: #ededed; border: 1px solid #333333; }
    
    /* Cards de Métricas (Novo Layout) */
    .nexus-card {
        background-color: #111111;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 20px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
        display: flex; flex-direction: column; justify-content: center;
    }
    .nexus-card:hover { border-color: #0070f3; box-shadow: 0 0 15px rgba(0, 112, 243, 0.1); }
    .card-label { color: #888888; font-size: 12px; text-transform: uppercase; font-weight: 600; letter-spacing: 1px; margin-bottom: 8px; }
    .card-value { color: #ededed; font-size: 32px; font-weight: 700; line-height: 1.2; margin-bottom: 4px; }
    .card-diff { color: #0070f3; font-size: 13px; font-weight: 500; }
    
    /* Layout de Gráficos e Tabelas */
    .nexus-container {
        background-color: #111111;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 20px;
        margin-top: 24px;
    }
    .section-title { font-size: 14px; color: #ededed; font-weight: 600; text-transform: uppercase; margin-bottom: 16px; border-bottom: 1px solid #333333; padding-bottom: 8px; }
    
    /* Lista de Sub IDs */
    .subid-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #222222; }
    .subid-row:last-child { border-bottom: none; }
    .subid-name { color: #a1a1aa; font-size: 14px; }
    .subid-val { color: #ededed; font-size: 14px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

hoje_pc = date.today()

# --- 2. FUNÇÃO API SHOPEE ---
def buscar_vendas_shopee_api(data_ini, data_fim, url_api):
    if not url_api or url_api == "":
        return {"error": "Aviso do Sistema", "detalhe": "URL da API não configurada na barra lateral!"}
    try:
        app_id = st.secrets.get("SHOPEE_APP_ID")
        secret = st.secrets.get("SHOPEE_SECRET")
        if not app_id or not secret:
            return {"error": "Aviso do Sistema", "detalhe": "Credenciais não configuradas nos Secrets!"}
            
        timestamp = int(time.time())
        start_ts = int(time.mktime(data_ini.timetuple()))
        end_ts = int(time.mktime((data_fim + timedelta(days=1)).timetuple())) - 1
        
        graphql_query = f"""
        {{
          conversionReport(purchaseTimeStart: {start_ts}, purchaseTimeEnd: {end_ts}) {{
            nodes {{ purchaseTime conversionStatus netCommission estimatedTotalCommission }}
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
        try: return r.json()
        except: return {"error": "Erro de Leitura", "status": r.status_code, "texto": r.text}
    except Exception as e:
        return {"error": "Falha no Python", "detalhe": str(e)}

# --- 3. LEITURA DE CSV ---
def ler_csv_shopee(file):
    if file is None: return pd.DataFrame()
    try: df = pd.read_csv(file, encoding='utf-8')
    except:
        file.seek(0)
        df = pd.read_csv(file, sep=';', encoding='latin-1')
    return df

# --- 4. CONFIGURAÇÕES (SIDEBAR) ---
with st.sidebar:
    st.markdown("<h3 style='color: #ededed;'>⚙️ Configurações</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 13px; color: #888;'>Painel de controle de dados</p>", unsafe_allow_html=True)
    st.divider()
    
    modo = st.radio("Fonte de Dados", ["API Automática", "CSV Local"])
    
    st.divider()
    arquivo_v = None
    if modo == "CSV Local":
        arquivo_v = st.file_uploader("📥 CSV Vendas", type=['csv'])
    arquivo_c = st.file_uploader("🖱️ CSV Cliques", type=['csv'])
        
    api_endpoint = st.secrets.get("SHOPEE_GRAPHQL_ENDPOINT", "https://open-api.affiliate.shopee.com.br/graphql")
    with st.expander("API Endpoint", expanded=False):
        st.text_input("URL", value=api_endpoint, disabled=True)

# --- 5. CABEÇALHO PRINCIPAL E FILTROS ---
col_title, col_filter1, col_filter2 = st.columns([2, 1, 1])

with col_title:
    st.markdown("<h1>NEXUS <span style='color: #0070f3;'>ANALYTICS</span></h1>", unsafe_allow_html=True)

with col_filter1:
    opcao_data = st.selectbox(
        "Período Rápido",
        ["Últimos 30 dias", "Ontem", "Anteontem", "Personalizado"]
    )

with col_filter2:
    if opcao_data == "Ontem":
        start_d, end_d = hoje_pc - timedelta(days=1), hoje_pc - timedelta(days=1)
        st.date_input("Data exata", value=[start_d, end_d], disabled=True)
    elif opcao_data == "Anteontem":
        start_d, end_d = hoje_pc - timedelta(days=2), hoje_pc - timedelta(days=2)
        st.date_input("Data exata", value=[start_d, end_d], disabled=True)
    elif opcao_data == "Últimos 30 dias":
        start_d, end_d = hoje_pc - relativedelta(days=30), hoje_pc
        st.date_input("Data exata", value=[start_d, end_d], disabled=True)
    else: 
        data_sel = st.date_input("Escolha o intervalo", value=[hoje_pc - timedelta(days=3), hoje_pc], max_value=hoje_pc)
        if len(data_sel) == 2:
            start_d, end_d = data_sel[0], data_sel[1]
        else:
             start_d, end_d = (hoje_pc, hoje_pc)

st.write("") # Espaçamento

# --- 6. PROCESSAMENTO DE DADOS (FILTRO RESTRITO) ---
vendas_b, pedidos_t, comissao_t, cliques_t = 0.0, 0, 0.0, 0
df_v_filtrado = pd.DataFrame()

if modo == "API Automática":
    with st.spinner("Sincronizando banco de dados..."):
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
                        'subId1': "Oculto pela API",
                        'order_price': 0.0 # API oculta essa info do endpoint
                    })
                df_v_filtrado = pd.DataFrame(flat_nodes)
                
                # FILTRO ESTRITO API: Somente status positivos
                if 'conversionStatus' in df_v_filtrado.columns:
                    status_validos = ['Pending', 'Completed', 'Valid', 'Settled']
                    df_v_filtrado = df_v_filtrado[df_v_filtrado['conversionStatus'].isin(status_validos)]
                
                vendas_b = df_v_filtrado['order_price'].sum()
                pedidos_t = len(df_v_filtrado)
                comissao_t = df_v_filtrado['commission'].sum()
        else:
            st.error("Erro na comunicação com o servidor.")
            st.json(dados) 
else: 
    if arquivo_v:
        df_v = ler_csv_shopee(arquivo_v)
        if 'Horário do pedido' in df_v.columns:
            df_v['Data_Simples'] = pd.to_datetime(df_v['Horário do pedido']).dt.date
            df_v_filtrado = df_v[(df_v['Data_Simples'] >= start_d) & (df_v['Data_Simples'] <= end_d)]
            
            # FILTRO ESTRITO CSV: Remove qualquer variação de Cancelado ou Inválido.
            if 'Status do Pedido' in df_v_filtrado.columns:
                filtro_invalido = df_v_filtrado['Status do Pedido'].str.contains('Cancelado|Cancelada|Inválido|Invalido|Rejeitado', case=False, na=False)
                df_v_filtrado = df_v_filtrado[~filtro_invalido]
            
            # Garantir que a coluna de preço seja lida como número
            col_preco = 'Preço(R$)' if 'Preço(R$)' in df_v_filtrado.columns else None
            col_comissao = 'Comissão líquida do afiliado(R$)' if 'Comissão líquida do afiliado(R$)' in df_v_filtrado.columns else None
            
            if col_preco and col_comissao:
                vendas_b = pd.to_numeric(df_v_filtrado[col_preco], errors='coerce').sum()
                pedidos_t = len(df_v_filtrado)
                comissao_t = pd.to_numeric(df_v_filtrado[col_comissao], errors='coerce').sum()

if arquivo_c:
    df_c = ler_csv_shopee(arquivo_c)
    colunas_data_c = [c for c in df_c.columns if 'Data' in c or 'Date' in c or 'Tempo' in c or 'Horário' in c]
    if colunas_data_c:
        df_c['Data_Simples'] = pd.to_datetime(df_c[colunas_data_c[0]]).dt.date
        df_c_filtrado = df_c[(df_c['Data_Simples'] >= start_d) & (df_c['Data_Simples'] <= end_d)]
        col_cliques = [c for c in df_c.columns if 'Clique' in c or 'Clicks' in c or 'Qtd' in c]
        cliques_t = pd.to_numeric(df_c_filtrado[col_cliques[0]], errors='coerce').sum() if col_cliques else len(df_c_filtrado)

ticket = vendas_b / pedidos_t if pedidos_t > 0 else 0
conv = (pedidos_t / cliques_t * 100) if cliques_t > 0 else 0

# --- 7. TELA PRINCIPAL (MÉTRICAS) ---
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
    <div class="nexus-card">
        <div class="card-label">Vendas Totais</div>
        <div class="card-value">R$ {vendas_b:.2f}</div>
        <div class="card-diff" style="color: #888;">{'(Via API não retorna)' if modo == 'API Automática' else 'Valor bruto filtrado'}</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="nexus-card">
        <div class="card-label">Pedidos Aprovados</div>
        <div class="card-value">{pedidos_t}</div>
        <div class="card-diff">+0.0% vs anterior</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="nexus-card">
        <div class="card-label">Comissão Líquida</div>
        <div class="card-value">R$ {comissao_t:.2f}</div>
        <div class="card-diff">+0.0% vs anterior</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="nexus-card">
        <div class="card-label">Taxa de Conversão</div>
        <div class="card-value">{conv:.2f}%</div>
        <div class="card-diff" style="color: #a1a1aa;">{cliques_t} cliques registrados</div>
    </div>
    """, unsafe_allow_html=True)

# --- 8. GRÁFICO E TABELAS ---
if not df_v_filtrado.empty:
    
    col_chart, col_data = st.columns([7, 3])
    
    with col_chart:
        st.markdown("<div class='nexus-container'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Receita por Dia</div>", unsafe_allow_html=True)
        
        col_data_evolucao = 'purchaseTime' if 'purchaseTime' in df_v_filtrado.columns else 'Data_Simples'
        col_comissao = 'commission' if 'commission' in df_v_filtrado.columns else 'Comissão líquida do afiliado(R$)'
        
        if pd.api.types.is_numeric_dtype(df_v_filtrado[col_data_evolucao]):
            df_v_filtrado['Data_Real'] = pd.to_datetime(df_v_filtrado[col_data_evolucao], unit='s').dt.date
        else:
            df_v_filtrado['Data_Real'] = df_v_filtrado[col_data_evolucao]
            
        # Força os valores de comissão para numérico para evitar erros no gráfico
        df_v_filtrado[col_comissao] = pd.to_numeric(df_v_filtrado[col_comissao], errors='coerce').fillna(0)
            
        evolucao = df_v_filtrado.groupby('Data_Real')[col_comissao].sum().reset_index()
        evolucao.columns = ['Data', 'Comissão']
        
        fig = px.area(evolucao, x='Data', y='Comissão', template="plotly_dark", color_discrete_sequence=['#0070f3'])
        fig.update_traces(line=dict(width=2), fillcolor='rgba(0, 112, 243, 0.1)')
        fig.update_layout(
            yaxis_title="", xaxis_title="", height=300, 
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(showgrid=True, gridcolor='#222222', zeroline=False),
            xaxis=dict(showgrid=False, zeroline=False)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_data:
        st.markdown("<div class='nexus-container' style='height: 100%;'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Top Performance</div>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class="subid-row">
                <span class="subid-name">Total Consolidado</span>
                <span class="subid-val">R$ {comissao_t:.2f}</span>
            </div>
            <div class="subid-row">
                <span class="subid-name">Ticket Médio</span>
                <span class="subid-val">R$ {ticket:.2f}</span>
            </div>
            <div class="subid-row">
                <span class="subid-name">Pedidos Aprovados</span>
                <span class="subid-val">{pedidos_t} un.</span>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("Aguardando carregamento de dados...")
