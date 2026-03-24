import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime # Puxa a data do sistema

# 1. SETUP DE DESIGN
st.set_page_config(page_title="AfiliadoDash PRO", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    div[data-testid="metric-container"] {
        background-color: #161b22; border: 1px solid #30363d;
        padding: 20px; border-radius: 12px;
    }
    h1, h2, h3 { color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- PEGAR DATA ATUAL DO PC ---
hoje_pc = date.today()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff4b4b;'>🟠 AfiliadoDash</h1>", unsafe_allow_html=True)
    arquivo = st.file_uploader("Subir CSV Shopee", type=['csv'])
    
    st.divider()
    
    # FILTRO COM TRAVA: O calendário só vai até "hoje_pc" (max_value)
    st.header("📅 Filtro de Período")
    data_selecionada = st.date_input(
        "Selecione o intervalo", 
        value=[hoje_pc, hoje_pc], # Começa marcado em HOJE
        max_value=hoje_pc,        # BLOQUEIO: Não deixa clicar em datas futuras
        help="Datas futuras estão bloqueadas automaticamente."
    )
    
    st.divider()
    st.caption(f"Data do Sistema: {hoje_pc.strftime('%d/%m/%Y')}")

# --- LÓGICA DE DADOS ---
if arquivo:
    df = pd.read_csv(arquivo)
    
    # Converter datas
    df['Data_Full'] = pd.to_datetime(df['Horário do pedido'])
    df['Data_Simples'] = df['Data_Full'].dt.date
    
    # --- TRAVA DE SEGURANÇA 2 (NO CÓDIGO) ---
    # Remove qualquer linha que por erro venha com data maior que hoje
    df = df[df['Data_Simples'] <= hoje_pc]
    
    # Aplicar o filtro do calendário
    if len(data_selecionada) == 2:
        start_date, end_date = data_selecionada
        df = df[(df['Data_Simples'] >= start_date) & (df['Data_Simples'] <= end_date)]
    elif len(data_selecionada) == 1:
        df = df[df['Data_Simples'] == data_selecionada[0]]

    # Filtro de Válidos
    df_validos = df[df['Status do Pedido'].isin(['Pendente', 'Concluído'])].copy()
    
    # Métricas
    vendas_brutas = df_validos['Preço(R$)'].sum()
    pedidos_total = len(df_validos)
    comissao_total = df_validos['Comissão líquida do afiliado(R$)'].sum()
    ticket_medio = vendas_brutas / pedidos_total if pedidos_total > 0 else 0

    # --- INTERFACE ---
    st.title("Dashboard de Visão Geral")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vendas Totais", f"R$ {vendas_brutas:.2f}")
    m2.metric("Pedidos", pedidos_total)
    m3.metric("Comissão Líquida", f"R$ {comissao_total:.2f}")
    m4.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")

    st.divider()

    # GRÁFICO DE MONTANHA (ÁREA)
    st.markdown("<h3 style='text-align: center;'>EVOLUÇÃO DA COMISSÃO</h3>", unsafe_allow_html=True)
    
    if not df_validos.empty:
        evolucao = df_validos.groupby('Data_Simples')['Comissão líquida do afiliado(R$)'].sum().reset_index()
        evolucao.columns = ['Data', 'Comissão']
        
        fig_area = px.area(evolucao, x='Data', y='Comissão', 
                          template="plotly_dark", color_discrete_sequence=['#00c853'])
        fig_area.update_traces(line_shape='spline')
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.warning("Sem dados para o período selecionado (ou todas as datas são futuras).")

else:
    st.warning("Aguardando upload do CSV...")
