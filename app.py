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
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #333 !important; font-family: 'Inter', sans-serif; }
    .stCaption { color: #6c757d !important; }
    [data-testid="stSidebar"] { background-color: #fff; border-right: 1px solid #dee2e6; }
    [data-testid="stSidebar"] .stMarkdown { color: #333 !important; }
    
    /* Cards de Métricas */
    .metric-card {
        background-color: #fff; border: 1px solid #dee2e6;
        padding: 24px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 24px;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .metric-title { color: #6c757d; font-size: 14px; margin-bottom: 8px; }
    .metric-value { color: #333; font-size: 32px; font-weight: 700; margin-bottom: 4px; }
    .metric-sub { color: #28a745; font-size: 14px; font-weight: 500; } /* Cor verde para aumento */
    .metric-sub-red { color: #dc3545; font-size: 14px; font-weight: 500; } /* Cor vermelha para queda */
    
    /* Cartões de TOP SubID */
    .top-subid-card {
        background-color: #fff; border: 1px solid #dee2e6;
        padding: 24px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 24px;
    }
    .top-subid-item {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 12px;
    }
    .top-subid-label { font-size: 14px; color: #6c757d; }
    .top-subid-value { font-size: 14px; color: #333; font-weight: 600; }
    .top-subid-bar {
        height: 8px; border-radius: 4px;
        background-color: #ff4b4b; /* Cor de exemplo */
    }
</style>
""", unsafe_allow_html=True)

# TRAVA DE DATA (PC DO USUÁRIO)
hoje_pc = date.today()

# --- 2. FUNÇÃO API SHOPEE (PADRÃO GRAPHQL BRASIL) ---
def buscar_vendas_shopee_api(data_ini, data_fim, url_api):
    if not url_api or url_api == "":
        st.sidebar.error("Você esqueceu de configurar a URL da API nos Secrets!")
        return {"error": "Aviso do Sistema", "detalhe": "URL da API não configurada na barra lateral!"}
        
    try:
        # Puxa as chaves cadastradas no Secrets do Streamlit
        # **Atenção: Eu não coloco credenciais diretamente no código por segurança.**
        # Substitua pelas suas variáveis se não usar os Secrets.
        app_id = st.secrets.get("SHOPEE_APP_ID")
        secret = st.secrets.get("SHOPEE_SECRET")
        
        if not app_id or not secret:
            st.sidebar.error("As credenciais SHOPEE_APP_ID e SHOPEE_SECRET não foram encontradas nos Secrets!")
            return {"error": "Aviso do Sistema", "detalhe": "Credenciais SHOPEE_APP_ID e SHOPEE_SECRET não configuradas nos Secrets!"}
            
        timestamp = int(time.time())
        
        # Converte datas para Timestamp Unix (exigência do conversionReport)
        start_ts = int(time.mktime(data_ini.timetuple()))
        end_ts = int(time.mktime((data_fim + timedelta(days=1)).timetuple())) - 1
        
        # A query ajustada com os campos exatos que funcionaram
        graphql_query = f"""
        {{
          conversionReport(purchaseTimeStart: {start_ts}, purchaseTimeEnd: {end_ts}) {{
            nodes {{
              purchaseTime
              conversionStatus
              netCommission
              estimatedTotalCommission
              customParameters {{
                subId1
              }}
              orders {{
                purchaseAmount
              }}
            }}
          }}
        }}
        """
        
        # Monta o Payload e transforma em String JSON sem espaços
        payload = {"query": graphql_query.strip()}
        payload_str = json.dumps(payload, separators=(',', ':'))
        
        # Calcula a Assinatura (Credential + Timestamp + Payload + Secret)
        base_string = f"{app_id}{timestamp}{payload_str}{secret}"
        signature = hashlib.sha256(base_string.encode('utf-8')).hexdigest()
        
        # O cabeçalho exato exigido pela documentação oficial do Brasil
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"
        }
        
        # Faz a requisição POST (O endpoint do GraphQL é sempre POST)
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
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    st.divider()
    
    # Navegação simulada
    st.markdown("Dashboard", unsafe_allow_html=True)
    st.markdown("Análise do Dia", unsafe_allow_html=True)
    st.markdown("Análise de Cliques", unsafe_allow_html=True)
    st.markdown("Meta Ads", unsafe_allow_html=True)
    st.markdown("Gerador de links", unsafe_allow_html=True)
    st.markdown("Análise de Links", unsafe_allow_html=True)
    st.markdown("Upload", unsafe_allow_html=True)
    st.markdown("Integrações", unsafe_allow_html=True)
    st.divider()
    
    # Seletor de Data conforme solicitado
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
    else: # Trechos de dias (Intervalo Livre)
        # O print image_10.png sugere um seletor de popover, no Streamlit ele é um date_input
        # Vamos manter o date_input para intervalo livre e usar o selectbox para atalhos.
        # Adicionei help na opção para o usuário saber da limitação de dias.
        data_sel = st.date_input("Escolha as datas (máx 3 dias)", value=[hoje_pc - timedelta(days=3), hoje_pc], max_value=hoje_pc, help="Para intervalos livres, escolha até 3 dias.")
        if len(data_sel) == 2:
            dias_dif = (data_sel[1] - data_sel[0]).days
            if dias_dif > 2:
                st.sidebar.warning("INTERVALO LIVRE: Escolha no máximo 3 dias.")
                start_d, end_d = hoje_pc, hoje_pc # Reseta para hoje para não dar erro
            else:
                start_d, end_d = data_sel[0], data_sel[1]
        else:
             start_d, end_d = (hoje_pc, hoje_pc)
    
    st.divider()
    modo = st.radio("📡 Fonte de Vendas", ["API Automática", "CSV (Backup)"])
    
    arquivo_v = None
    if modo == "CSV (Backup)":
        arquivo_v = st.file_uploader("📥 Subir CSV de Vendas", type=['csv'])
        
    st.markdown("---")
    arquivo_c = st.file_uploader("🖱️ Subir CSV de Cliques (P/ Conversão)", type=['csv'])
        
    st.divider()
    # Pega o Endpoint dos Secrets para não precisar colar toda vez na sidebar.
    # **Atenção: Substitua se não usar os Secrets.**
    api_endpoint = st.secrets.get("SHOPEE_GRAPHQL_ENDPOINT", "https://open-api.affiliate.shopee.com.br/graphql")
    
    with st.expander("⚙️ Configuração Avançada", expanded=False):
        st.caption("A URL do Endpoint GraphQL é:")
        st.text_input("Endpoint", value=api_endpoint, disabled=True)
        # Exemplo decorativo dos IDs do print
        st.markdown("User: JG João Gabryel Car...")
        st.markdown(f"Data do PC: {hoje_pc.strftime('%d/%m/%Y')}")

# --- 5. PROCESSAMENTO DE DADOS ---
vendas_b, pedidos_t, comissao_t, cliques_t = 0.0, 0, 0.0, 0
df_v_filtrado = pd.DataFrame()

# Lógica de Vendas
if modo == "API Automática":
    with st.spinner("Conectando aos servidores GraphQL da Shopee..."):
        dados = buscar_vendas_shopee_api(start_d, end_d, api_endpoint)
        
        # Novo caminho de leitura para o padrão GraphQL oficial
        if dados and 'data' in dados and 'conversionReport' in dados['data']:
            nodes = dados['data']['conversionReport']['nodes']
            if nodes:
                # Planificando os dados aninhados do GraphQL
                flat_nodes = []
                for n in nodes:
                    comissao = n.get('netCommission') or n.get('estimatedTotalCommission') or 0
                    
                    sub_id = "N/A"
                    if n.get('customParameters') and isinstance(n['customParameters'], dict):
                        sub_id = n['customParameters'].get('subId1', 'N/A')
                        
                    venda_bruta = 0
                    if n.get('orders') and isinstance(n['orders'], list):
                        for ord in n['orders']:
                            venda_bruta += ord.get('purchaseAmount', 0)
                            
                    flat_nodes.append({
                        'purchaseTime': n.get('purchaseTime'),
                        'conversionStatus': n.get('conversionStatus'),
                        'commission': float(comissao),
                        'subId1': sub_id,
                        'order_price': float(venda_bruta)
                    })
                    
                df_v_filtrado = pd.DataFrame(flat_nodes)
                
                # Ignorando status de cancelamento comuns (Cancelled, Rejected, Invalid)
                if 'conversionStatus' in df_v_filtrado.columns:
                    df_v_filtrado = df_v_filtrado[~df_v_filtrado['conversionStatus'].isin(['Cancelled', 'Rejected', 'Invalid'])]
                
                vendas_b = df_v_filtrado['order_price'].sum()
                pedidos_t = len(df_v_filtrado)
                comissao_t = df_v_filtrado['commission'].sum()
        else:
            st.error(f"⚠️ Resposta do Servidor (Verifique seus Secrets):")
            st.json(dados) 
            
else: # Modo CSV (Backup)
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
st.title("Dashboard")
st.caption(f"Período selecionado: {start_d.strftime('%d/%m/%Y')} até {end_d.strftime('%d/%m/%Y')}")

# --- LINHA 1: OS 5 CARDS DE MÉTRICAS (HTML/CSS CUSTOMIZADO) ---
m1, m2, m3, m4, m5 = st.columns(5)

# Card Vendas Totais
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Vendas Totais</div>
        <div class="metric-value">R$ {vendas_b:.2f}</div>
        <div class="metric-sub">↑ 100.0% Anterior: R$ {vendas_b:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# Card Pedidos
with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Pedidos</div>
        <div class="metric-value">{pedidos_t}</div>
        <div class="metric-sub">↑ 100.0% Itens vendidos: {pedidos_t}</div>
    </div>
    """, unsafe_allow_html=True)

# Card Comissão Líquida
with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Comissão Líquida</div>
        <div class="metric-value">R$ {comissao_t:.2f}</div>
        <div class="metric-sub">↑ 100.0% Anterior: R$ {comissao_t:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# Card Ticket Médio
with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Ticket Médio</div>
        <div class="metric-value">R$ {ticket:.2f}</div>
        <div class="metric-sub">↑ 100.0% Anterior: R$ {ticket:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# Card Comissão Estimada (Decorativo)
with m5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Comissão estimada a validar</div>
        <div class="metric-value">R$ 0,00</div>
        <div class="stCaption">Validadas a receber: R$ 0,00</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- LINHA 2: TABELAS TOP SUBID (HTML/CSS CUSTOMIZADO) ---
if not df_v_filtrado.empty:
    c1, c2, c3 = st.columns(3)
    
    # Processa DataFrame por SubID para a tabela
    col_sub = 'subId1' if 'subId1' in df_v_filtrado.columns else ('Sub_id1' if 'Sub_id1' in df_v_filtrado.columns else df_v_filtrado.columns[0])
    col_comissao = 'commission' if 'commission' in df_v_filtrado.columns else ('Comissão líquida do afiliado(R$)' if 'Comissão líquida do afiliado(R$)' in df_v_filtrado.columns else 'commission')
    
    with c1:
        st.subheader("TOP SUBID 1 (COMISSÃO)")
        if col_sub in df_v_filtrado.columns and col_comissao in df_v_filtrado.columns:
            # Agrupa e soma a comissão por SubID
            df_subid = df_v_filtrado.groupby(col_sub)[col_comissao].sum().reset_index().sort_values(by=col_comissao, ascending=False).head(3)
            
            for index, row in df_subid.iterrows():
                # Define a cor da barra baseada no SubID (exemplo)
                # print image_11.png só mostra uma tabela com sem sub id.
                # Vou manter apenas uma tabela para TOP SubID 1.
                cor_barra = "#28a745" if row[col_sub] == "sem sub id" else "#00c853"
                st.markdown(f"""
                <div class="top-subid-card">
                    <div class="top-subid-item">
                        <div class="top-subid-label">{row[col_sub]}</div>
                        <div class="top-subid-value">R$ {row[col_comissao]:.2f}</div>
                    </div>
                    <div class="top-subid-bar" style="background-color: {cor_barra};"></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("A API não retornou dados para este SubID.")
            
    # Contêineres vazios para TOP SubID 2 e 3 para manter o layout de 3 colunas
    with c2:
        st.subheader("TOP SUBID 2 (COMISSÃO)")
        # st.json(df_v_filtrado.iloc[0].to_dict()) # Modo Dev: mostra as colunas
        st.caption("A API não retornou dados para este SubID.")
        
    with c3:
        st.subheader("TOP SUBID 3 (COMISSÃO)")
        st.caption("A API não retornou dados para este SubID.")

    st.divider()

    # --- LINHA 3: GRÁFICO DE EVOLUÇÃO (DISPERSÃO - PONTOS VERDES) ---
    st.subheader("EVOLUÇÃO DA COMISSÃO")
    col_data_evolucao = 'purchaseTime' if 'purchaseTime' in df_v_filtrado.columns else ('Data_Simples' if 'Data_Simples' in df_v_filtrado.columns else None)
    
    if col_data_evolucao and col_data_evolucao in df_v_filtrado.columns:
        # Se a API retornar unix timestamp (números), converte para data
        if pd.api.types.is_numeric_dtype(df_v_filtrado[col_data_evolucao]):
            df_v_filtrado['Data_Real'] = pd.to_datetime(df_v_filtrado[col_data_evolucao], unit='s').dt.date
        else:
            df_v_filtrado['Data_Real'] = df_v_filtrado[col_data_evolucao]
            
        evolucao = df_v_filtrado.groupby('Data_Real')[col_comissao].sum().reset_index()
        evolucao.columns = ['Data', 'Comissão']
        
        # Cria o gráfico de dispersão com pontos verdes e suavizados, conforme image_11.png e image_9.png
        fig_a = px.scatter(evolucao, x='Data', y='Comissão', template="plotly_white", color_discrete_sequence=['#28a745'], labels={'Data':'Dia', 'Comissão':'Comissão (R$)'})
        # fig_a.update_traces(line_shape='spline') # Spline é para px.area, dispersão não tem linha.
        fig_a.update_layout(yaxis_title="Comissão (R$)", xaxis_title="Dia", height=400, margin=dict(l=40, r=40, t=10, b=10))
        st.plotly_chart(fig_a, use_container_width=True)
    else:
        st.info("Aguardando os dados da API ou do arquivo CSV para plotar o gráfico.")

else:
    st.info("Aguardando os dados da API ou do arquivo CSV.")
