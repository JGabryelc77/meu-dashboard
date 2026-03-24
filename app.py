import streamlit as st
import requests
from datetime import date

# Configuração da Página
st.set_page_config(page_title="Afiliado Dash", layout="wide")

# Função para pegar a cotação do Dólar (PTAX) no Banco Central
def pegar_cotacao_dolar():
    try:
        url = "https://economia.awesomeapi.com.br/last/USD-BRL"
        r = requests.get(url).json()
        return float(r['USDBRL']['bid'])
    except:
        return 5.00 # Valor de segurança caso a API falhe

# Função para buscar dados do Facebook
def buscar_gastos_fb():
    token = st.secrets["FB_ACCESS_TOKEN"]
    account_id = st.secrets["FB_AD_ACCOUNT_ID"]
    hoje = date.today().strftime('%Y-%m-%d')
    
    url = f"https://graph.facebook.com/v19.0/{account_id}/insights"
    params = {
        'access_token': token,
        'time_range': f"{{'since':'{hoje}','until':'{hoje}'}}",
        'fields': 'spend',
        'level': 'account'
    }
    
    try:
        r = requests.get(url, params=params).json()
        if 'data' in r and len(r['data']) > 0:
            return float(r['data'][0]['spend'])
        return 0.0
    except:
        return 0.0

# --- INTERFACE DO SITE ---
st.title("📊 Painel de Tráfego - Vídeos Dark")

if st.button('🔄 Atualizar Dados Agora'):
    with st.spinner('Buscando dados na Meta e Cotação do Dólar...'):
        gastos_usd = buscar_gastos_fb()
        cotacao = pegar_cotacao_dolar()
        gastos_brl = gastos_usd * cotacao
        
        # Simulando vendas (enquanto a Shopee não libera a API)
        vendas_brl = 0.00 # Aqui entrará o valor da Shopee
        lucro_brl = vendas_brl - gastos_brl
        
        st.subheader(f"Resumo de Hoje (Cotação US$: R$ {cotacao:.2f})")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Investimento (Meta Ads)", f"US$ {gastos_usd:.2f}", f"R$ {gastos_brl:.2f}")
        col2.metric("Vendas (Shopee)", f"R$ {vendas_brl:.2f}")
        
        # Cor do lucro (Verde se positivo, Vermelho se negativo)
        st.metric("Lucro Líquido Real", f"R$ {lucro_brl:.2f}", delta=f"{lucro_brl:.2f}", delta_color="normal")
        
        if gastos_usd > 0:
            roas = vendas_brl / gastos_brl if gastos_brl > 0 else 0
            st.write(f"**ROAS Atual:** {roas:.2f}x")

else:
    st.info("Clique no botão acima para sincronizar sua BM americana e converter para Reais.")

# Rodapé com a data da última atualização
st.caption(f"Dados atualizados em: {date.today().strftime('%d/%m/%Y')}")
