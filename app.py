import streamlit as st

# Configura a página para ocupar a tela toda
st.set_page_config(page_title="Afiliado Dash", layout="wide")

st.title("📊 Painel de Tráfego - Vídeos Dark")
st.write("O motor do site está ligado e funcionando perfeitamente na nuvem!")

# Criando a primeira linha de Cards (Igual ao AfiliadoDash que mapeamos)
st.subheader("Resumo de Hoje")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Investimento (Meta Ads)", "US$ 0,00")
col2.metric("Vendas (Shopee)", "R$ 0,00")
col3.metric("Lucro Líquido", "R$ 0,00")
col4.metric("ROAS", "0.00x")
