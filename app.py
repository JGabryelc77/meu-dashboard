"""
┌──────────────────────────────────────────────────────────────────┐
│  SHOPEE AFFILIATES DASHBOARD — API v2 (GraphQL)                 │
│  Stack: Python · Streamlit · Requests                           │
│  Endpoint: open-api.affiliate.shopee.com.br/graphql             │
│  Campos: purchaseTime · conversionStatus                        │
│          netCommission · estimatedTotalCommission                │
│  NÃO solicita: purchaseAmount · customParameters                │
└──────────────────────────────────────────────────────────────────┘
"""

import streamlit as st
import requests
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone, date
import pandas as pd

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAGE CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(
    page_title="Shopee Affiliates",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
BLACKLIST = ("cancel", "reject", "invalid")
BR_TZ = timezone(timedelta(hours=-3))
MAX_PAGES = 50          # trava de segurança na paginação
PAGE_SIZE = 100

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DARK-MODE CSS  (fundo #000, cards #111, estilo Vercel/Apple)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── reset geral ── */
*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background-color: #000000 !important;
    color: #e5e5e5;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

#MainMenu, footer, header { visibility: hidden; }

[data-testid="stSidebar"] {
    background-color: #080808;
    border-right: 1px solid #1a1a1a;
}

.block-container {
    padding: 2rem 2.5rem 3rem 2.5rem;
    max-width: 1280px;
}

/* ── cards de métrica ── */
.m-card {
    background: #111111;
    border: 1px solid #222222;
    border-radius: 14px;
    padding: 28px 24px;
    transition: border-color .25s ease, box-shadow .25s ease;
}
.m-card:hover {
    border-color: #333333;
    box-shadow: 0 0 0 1px #222222;
}
.m-label {
    font-size: 12px;
    font-weight: 600;
    color: #666666;
    text-transform: uppercase;
    letter-spacing: .8px;
    margin-bottom: 10px;
}
.m-value {
    font-size: 34px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.15;
    letter-spacing: -.5px;
}
.m-sub {
    font-size: 11.5px;
    color: #4a4a4a;
    margin-top: 10px;
    line-height: 1.4;
}
.green  { color: #00d47b !important; }
.yellow { color: #f5a623 !important; }
.muted  { color: #333333 !important; }

/* ── cabeçalho ── */
.hdr    { font-size: 30px; font-weight: 800; color: #fff; letter-spacing: -.6px; }
.hdr-sub{ font-size: 14px; color: #555; margin-bottom: 28px; }

/* ── divisor ── */
.sep { border: none; border-top: 1px solid #1a1a1a; margin: 28px 0; }

/* ── botões / inputs ── */
.stButton > button {
    background: #111 !important;
    color: #fff !important;
    border: 1px solid #333 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all .2s ease !important;
}
.stButton > button:hover {
    background: #1a1a1a !important;
    border-color: #555 !important;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
.stDateInput > div > div > input,
.stTextInput > div > div > input {
    background-color: #111 !important;
    color: #eee !important;
    border-color: #333 !important;
    border-radius: 8px !important;
}

/* ── dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #222;
    border-radius: 12px;
    overflow: hidden;
}

/* ── scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }

/* ── estado vazio ── */
.empty-state {
    text-align: center;
    padding: 100px 20px;
    color: #333;
}
.empty-state .icon { font-size: 52px; margin-bottom: 16px; }
.empty-state .title { font-size: 18px; font-weight: 600; color: #555; margin-bottom: 6px; }
.empty-state .desc  { font-size: 13px; color: #3a3a3a; }
</style>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNÇÕES UTILITÁRIAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def to_unix(d: date, end_of_day: bool = False) -> int:
    """Converte uma date para Unix Timestamp no fuso BR (UTC-3)."""
    h, m, s = (23, 59, 59) if end_of_day else (0, 0, 0)
    return int(datetime(d.year, d.month, d.day, h, m, s, tzinfo=BR_TZ).timestamp())


def brl(valor: float) -> str:
    """Formata float para R$ no padrão brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _safe_float(v) -> float:
    """Converte qualquer valor para float com fallback 0."""
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API — AUTENTICAÇÃO + REQUEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_query(start_ts: int, end_ts: int, limit: int = PAGE_SIZE,
                 scroll_id: str = "") -> str:
    """
    Monta a query GraphQL COMPACTA.
    Solicita APENAS os 4 campos permitidos:
      purchaseTime · conversionStatus · netCommission · estimatedTotalCommission
    NÃO inclui purchaseAmount nem customParameters.
    """
    return (
        "{"
        f'orderListV2(startTime:{start_ts},'
        f'endTime:{end_ts},'
        f'limit:{limit},'
        f'scrollId:"{scroll_id}")'
        "{nodes{"
        "purchaseTime "
        "conversionStatus "
        "netCommission "
        "estimatedTotalCommission"
        "}"
        "scrollId "
        "more}"
        "}"
    )


def _sign_and_call(app_id: str, secret: str, query: str) -> dict:
    """
    1) Monta o payload JSON sem espaços.
    2) Gera timestamp UNIX (epoch seconds).
    3) Signature = SHA256( AppID + Timestamp + PayloadJSON + Secret )
    4) Header: SHA256 Credential={AppID}, Timestamp={ts}, Signature={sig}
    5) POST → endpoint GraphQL.
    """
    payload_dict = {"query": query}
    payload_json = json.dumps(payload_dict, separators=(",", ":"), ensure_ascii=False)

    ts = str(int(time.time()))
    raw = f"{app_id}{ts}{payload_json}{secret}"
    sig = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    headers = {
        "Authorization": (
            f"SHA256 Credential={app_id}, "
            f"Timestamp={ts}, "
            f"Signature={sig}"
        ),
        "Content-Type": "application/json",
    }

    resp = requests.post(
        ENDPOINT,
        headers=headers,
        data=payload_json.encode("utf-8"),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_orders(app_id: str, secret: str,
                 start_ts: int, end_ts: int) -> tuple[list, str | None]:
    """
    Busca TODOS os pedidos paginados.
    Retorna (lista_de_nodes, mensagem_de_erro_ou_None).
    """
    all_nodes: list[dict] = []
    scroll_id = ""
    has_more = True
    page = 0

    while has_more and page < MAX_PAGES:
        q = _build_query(start_ts, end_ts, scroll_id=scroll_id)

        try:
            result = _sign_and_call(app_id, secret, q)
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text[:500] if exc.response else ""
            return all_nodes, f"HTTP {exc.response.status_code}: {body}"
        except requests.exceptions.RequestException as exc:
            return all_nodes, f"Erro de conexão: {exc}"

        # Erros GraphQL
        if "errors" in result:
            msg = result["errors"][0].get("message", str(result["errors"]))
            return all_nodes, f"GraphQL: {msg}"

        # Parsing resiliente (tenta nomes alternativos)
        data = result.get("data", {})
        root = (
            data.get("orderListV2")
            or data.get("orderList")
            or data.get("getOrderList")
            or {}
        )
        nodes = root.get("nodes") or root.get("orders") or []
        all_nodes.extend(nodes)

        scroll_id = root.get("scrollId") or root.get("cursor") or ""
        has_more = root.get("more", root.get("hasMore", root.get("hasNextPage", False)))
        page += 1

    return all_nodes, None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROCESSAMENTO DE DADOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _is_blacklisted(status: str) -> bool:
    s = (status or "").lower()
    return any(bl in s for bl in BLACKLIST)


def _effective_commission(order: dict) -> tuple[float, str]:
    """
    Retorna (valor_comissão, tipo).
    - netCommission > 0 → usa esse valor  (Concluído)
    - caso contrário    → estimatedTotalCommission (Pendente)
    """
    net = _safe_float(order.get("netCommission"))
    if net > 0:
        return net, "Concluído"
    est = _safe_float(order.get("estimatedTotalCommission"))
    return est, "Pendente"


def process(raw: list[dict]) -> tuple[list[dict], int]:
    """
    Aplica filtro de lista-negra e calcula comissão efetiva.
    Retorna (pedidos_válidos, total_bruto).
    """
    total_raw = len(raw)
    valid = []
    for o in raw:
        if _is_blacklisted(o.get("conversionStatus", "")):
            continue
        comm, ctype = _effective_commission(o)
        valid.append({
            "ts": o.get("purchaseTime", 0),
            "status": o.get("conversionStatus", "—"),
            "commission": comm,
            "type": ctype,
        })
    return valid, total_raw


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UI — CARD DE MÉTRICA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def card(label: str, value: str, sub: str = "", css: str = ""):
    vc = f"m-value {css}" if css else "m-value"
    sub_html = f'<div class="m-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="m-card">'
        f'<div class="m-label">{label}</div>'
        f'<div class="{vc}">{value}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIDEBAR — CREDENCIAIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Tenta carregar de st.secrets primeiro (Streamlit Cloud)
try:
    _def_id = st.secrets["SHOPEE_APP_ID"]
    _def_sk = st.secrets["SHOPEE_SECRET"]
except Exception:
    _def_id, _def_sk = "", ""

with st.sidebar:
    st.markdown("### ⚙️ Credenciais")
    st.caption("Insira App ID e Secret da Shopee Open Platform.")
    app_id = st.text_input("App ID", value=_def_id, type="password")
    secret = st.text_input("Secret Key", value=_def_sk, type="password")
    st.markdown("<hr class='sep'>", unsafe_allow_html=True)
    st.caption(
        "ℹ️ Campos **purchaseAmount** e **customParameters** "
        "NÃO são solicitados na query (restrição de acesso)."
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEADER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="hdr">🛍️ Shopee Affiliates</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hdr-sub">Dashboard de Comissões · API v2 GraphQL · Brasil</div>',
    unsafe_allow_html=True,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALENDÁRIO + ATALHOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
today = datetime.now(BR_TZ).date()
yesterday = today - timedelta(days=1)
day_before = today - timedelta(days=2)
thirty_ago = today - timedelta(days=30)

c_preset, c_start, c_end, c_btn = st.columns([2.2, 1.8, 1.8, 1])

with c_preset:
    preset = st.selectbox(
        "Período rápido",
        ["Ontem", "Anteontem", "Últimos 30 dias", "Personalizado"],
        label_visibility="collapsed",
    )

if preset == "Ontem":
    d_start, d_end = yesterday, yesterday
elif preset == "Anteontem":
    d_start, d_end = day_before, day_before
elif preset == "Últimos 30 dias":
    d_start, d_end = thirty_ago, yesterday
else:
    d_start, d_end = yesterday, today

with c_start:
    start_date = st.date_input(
        "De", value=d_start, max_value=today, label_visibility="collapsed"
    )
with c_end:
    end_date = st.date_input(
        "Até", value=d_end, max_value=today, label_visibility="collapsed"
    )
with c_btn:
    go = st.button("▶ Consultar", use_container_width=True, type="primary")

st.markdown("<hr class='sep'>", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ESTADO INICIAL  (antes de clicar)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if not go:
    st.markdown(
        '<div class="empty-state">'
        '<div class="icon">📊</div>'
        '<div class="title">Selecione um período e clique em Consultar</div>'
        '<div class="desc">Configure suas credenciais no menu lateral (☰)</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VALIDAÇÕES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if not app_id or not secret:
    st.error("⚠️ Preencha App ID e Secret Key na barra lateral.")
    st.stop()

if start_date > end_date:
    st.error("⚠️ Data inicial maior que data final.")
    st.stop()

start_ts = to_unix(start_date, end_of_day=False)
end_ts   = to_unix(end_date,   end_of_day=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHAMADA À API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.spinner("Consultando Shopee…"):
    raw_orders, error = fetch_orders(app_id, secret, start_ts, end_ts)

if error:
    st.error(f"❌ {error}")
    with st.expander("🔍 Informações de debug"):
        st.code(f"Endpoint: {ENDPOINT}", language="text")
        st.code(f"startTime (unix): {start_ts}", language="text")
        st.code(f"endTime   (unix): {end_ts}", language="text")
        st.code(
            f"Query de exemplo:\n{_build_query(start_ts, end_ts)}",
            language="graphql",
        )
    st.stop()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROCESSAMENTO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
valid_orders, total_raw = process(raw_orders)
total_valid  = len(valid_orders)
total_comm   = sum(o["commission"] for o in valid_orders)
conv_rate    = (total_valid / total_raw * 100) if total_raw > 0 else 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MÉTRICAS PRINCIPAIS  (4 cards)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
k1, k2, k3, k4 = st.columns(4, gap="medium")

with k1:
    card(
        "Vendas Totais",
        "—",
        "Indisponível via API (purchaseAmount restrito)",
        css="muted",
    )

with k2:
    card(
        "Pedidos Válidos",
        f"{total_valid}",
        f"de {total_raw} retornados · {total_raw - total_valid} removidos pelo filtro",
    )

with k3:
    card(
        "Comissão Líquida",
        brl(total_comm),
        "net + estimated (pedidos válidos)",
        css="green",
    )

with k4:
    card(
        "Taxa de Conversão",
        f"{conv_rate:.1f}%",
        "Pedidos válidos ÷ total retornado",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BREAKDOWN: CONCLUÍDO vs PENDENTE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if valid_orders:
    st.markdown("<hr class='sep'>", unsafe_allow_html=True)

    comm_done    = sum(o["commission"] for o in valid_orders if o["type"] == "Concluído")
    comm_pending = sum(o["commission"] for o in valid_orders if o["type"] == "Pendente")
    qty_done     = sum(1 for o in valid_orders if o["type"] == "Concluído")
    qty_pending  = sum(1 for o in valid_orders if o["type"] == "Pendente")

    b1, b2 = st.columns(2, gap="medium")
    with b1:
        card(
            "✅ Comissão Concluída",
            brl(comm_done),
            f"{qty_done} pedido(s) · netCommission > 0",
            css="green",
        )
    with b2:
        card(
            "⏳ Comissão Pendente",
            brl(comm_pending),
            f"{qty_pending} pedido(s) · via estimatedTotalCommission",
            css="yellow",
        )

    # ── TABELA DE PEDIDOS ──
    st.markdown("<hr class='sep'>", unsafe_allow_html=True)
    st.markdown("#### 📋 Detalhamento")

    def _fmt_ts(ts):
        if ts and ts > 0:
            try:
                return datetime.fromtimestamp(int(ts), tz=BR_TZ).strftime("%d/%m/%Y %H:%M")
            except Exception:
                return "—"
        return "—"

    df = pd.DataFrame(valid_orders)
    df["Data / Hora"]   = df["ts"].apply(_fmt_ts)
    df["Status"]        = df["status"]
    df["Tipo"]          = df["type"]
    df["Comissão (R$)"] = df["commission"].apply(lambda v: brl(v))

    display = (
        df[["Data / Hora", "Status", "Tipo", "Comissão (R$)"]]
        .sort_values("Data / Hora", ascending=False)
        .reset_index(drop=True)
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=min(520, 36 * len(display) + 40),
    )

else:
    st.markdown("<hr class='sep'>", unsafe_allow_html=True)
    st.info(
        "Nenhum pedido válido no período "
        f"**{start_date.strftime('%d/%m/%Y')}** — "
        f"**{end_date.strftime('%d/%m/%Y')}**."
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RODAPÉ (debug rápido colapsado)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.expander("🔧 Debug / Parâmetros enviados"):
    st.json({
        "endpoint": ENDPOINT,
        "startTime_unix": start_ts,
        "endTime_unix": end_ts,
        "startDate_br": start_date.strftime("%d/%m/%Y"),
        "endDate_br": end_date.strftime("%d/%m/%Y"),
        "total_raw": total_raw,
        "total_valid": total_valid,
        "blacklist_filter": list(BLACKLIST),
        "query_example": _build_query(start_ts, end_ts),
    })
