"""
Shopee Affiliates Dashboard - API v2 GraphQL
Auto-discovery do schema real da API
"""

import streamlit as st
import requests
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone, date
import pandas as pd

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(
    page_title="Shopee Affiliates",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
BLACKLIST = ("cancel", "reject", "invalid")
BR_TZ = timezone(timedelta(hours=-3))
MAX_PAGES = 50
PAGE_SIZE = 100

ROOT_CANDIDATES = [
    "orderList",
    "affiliateOrderList",
    "getOrderList",
    "orderListV2",
    "orders",
    "affiliateOrders",
]

NODE_KEYS = ("nodes", "orders", "items", "edges", "list", "data")
SCROLL_KEYS = ("scrollId", "scroll_id", "cursor", "after", "nextCursor")
MORE_KEYS = ("more", "hasMore", "hasNextPage", "has_more")

ORDER_FIELDS = (
    "purchaseTime "
    "conversionStatus "
    "netCommission "
    "estimatedTotalCommission"
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DARK MODE CSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*,*::before,*::after{box-sizing:border-box}
.stApp{
    background-color:#000000!important;
    color:#e5e5e5;
    font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background-color:#080808;border-right:1px solid #1a1a1a}
.block-container{padding:2rem 2.5rem 3rem 2.5rem;max-width:1280px}
.m-card{
    background:#111111;border:1px solid #222222;
    border-radius:14px;padding:28px 24px;
    transition:border-color .25s ease,box-shadow .25s ease;
}
.m-card:hover{border-color:#333333;box-shadow:0 0 0 1px #222222}
.m-label{
    font-size:12px;font-weight:600;color:#666666;
    text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px;
}
.m-value{font-size:34px;font-weight:800;color:#ffffff;line-height:1.15;letter-spacing:-.5px}
.m-sub{font-size:11.5px;color:#4a4a4a;margin-top:10px;line-height:1.4}
.green{color:#00d47b!important}
.yellow{color:#f5a623!important}
.blue{color:#3b82f6!important}
.muted{color:#333333!important}
.hdr{font-size:30px;font-weight:800;color:#fff;letter-spacing:-.6px}
.hdr-sub{font-size:14px;color:#555;margin-bottom:28px}
.sep{border:none;border-top:1px solid #1a1a1a;margin:28px 0}
.schema-item{
    display:inline-block;background:#1a1a1a;color:#888;
    padding:4px 10px;border-radius:6px;margin:3px;
    font-family:monospace;font-size:12px;
}
.schema-match{background:#0a2a1a!important;color:#00d47b!important;border:1px solid #0d3d23}
.stButton>button{
    background:#111!important;color:#fff!important;
    border:1px solid #333!important;border-radius:10px!important;
    font-weight:600!important;transition:all .2s ease!important;
}
.stButton>button:hover{background:#1a1a1a!important;border-color:#555!important}
div[data-baseweb="select"]>div,
div[data-baseweb="input"]>div,
.stDateInput>div>div>input,
.stTextInput>div>div>input{
    background-color:#111!important;color:#eee!important;
    border-color:#333!important;border-radius:8px!important;
}
[data-testid="stDataFrame"]{border:1px solid #222;border-radius:12px;overflow:hidden}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:#000}
::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
.empty-state{text-align:center;padding:100px 20px;color:#333}
.empty-state .icon{font-size:52px;margin-bottom:16px}
.empty-state .title{font-size:18px;font-weight:600;color:#555;margin-bottom:6px}
.empty-state .desc{font-size:13px;color:#3a3a3a}
</style>
""",
    unsafe_allow_html=True,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UTILIDADES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def to_unix(d, end_of_day=False):
    h, m, s = (23, 59, 59) if end_of_day else (0, 0, 0)
    return int(
        datetime(d.year, d.month, d.day, h, m, s, tzinfo=BR_TZ).timestamp()
    )


def brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sf(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API CORE - ASSINATURA + CHAMADA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _sign_and_call(app_id, secret, query):
    payload_dict = {"query": query}
    payload_json = json.dumps(
        payload_dict, separators=(",", ":"), ensure_ascii=False
    )
    ts = str(int(time.time()))
    raw = app_id + ts + payload_json + secret
    sig = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    headers = {
        "Authorization": (
            "SHA256 Credential=" + app_id
            + ", Timestamp=" + ts
            + ", Signature=" + sig
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTROSPECTION - DESCOBRE SCHEMA REAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def introspect_schema(app_id, secret):
    query = "{__schema{queryType{fields{name}}}}"
    try:
        result = _sign_and_call(app_id, secret, query)
    except requests.exceptions.HTTPError as exc:
        return [], "HTTP " + str(exc.response.status_code)
    except requests.exceptions.RequestException as exc:
        return [], str(exc)

    if "errors" in result:
        msg = result["errors"][0].get("message", str(result["errors"]))
        return [], msg

    fields = (
        result.get("data", {})
        .get("__schema", {})
        .get("queryType", {})
        .get("fields", [])
    )
    return [f["name"] for f in fields if isinstance(f, dict)], None


def _find_order_query(schema_fields):
    lower_map = {f.lower(): f for f in schema_fields}
    for candidate in ROOT_CANDIDATES:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    for low, original in lower_map.items():
        if "order" in low:
            return original
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BRUTE FORCE - TESTA CANDIDATOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def probe_query_name(app_id, secret, start_ts, end_ts):
    errors = []
    for name in ROOT_CANDIDATES:
        q = (
            "{" + name
            + "(startTime:" + str(start_ts)
            + ",endTime:" + str(end_ts)
            + ',limit:1,scrollId:"")'
            + "{nodes{" + ORDER_FIELDS + "}"
            + "scrollId more}}"
        )
        try:
            result = _sign_and_call(app_id, secret, q)
            if "errors" not in result:
                return name, errors
            msg = result["errors"][0].get("message", "")
            errors.append(name + ": " + msg)
        except Exception as exc:
            errors.append(name + ": " + str(exc))
    return None, errors


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DISCOVERY COMPLETO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def discover_root_field(app_id, secret, start_ts, end_ts):
    schema_fields, intro_err = introspect_schema(app_id, secret)

    if schema_fields:
        match = _find_order_query(schema_fields)
        if match:
            return match, schema_fields, "introspection"
        return None, schema_fields, "introspection (sem match)"

    name, _ = probe_query_name(app_id, secret, start_ts, end_ts)
    if name:
        return name, [], "brute-force"
    return None, [], "falhou (" + str(intro_err) + ")"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARSE RESILIENTE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _extract_from_root(root):
    nodes = []
    for k in NODE_KEYS:
        if k in root and isinstance(root[k], list):
            nodes = root[k]
            break

    scroll = ""
    for k in SCROLL_KEYS:
        if k in root and root[k] is not None:
            scroll = str(root[k])
            break

    more = False
    for k in MORE_KEYS:
        if k in root:
            more = bool(root[k])
            break

    return nodes, scroll, more


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FETCH ORDERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_orders(app_id, secret, start_ts, end_ts, root_field):
    all_nodes = []
    scroll_id = ""
    has_more = True
    page = 0

    while has_more and page < MAX_PAGES:
        q = (
            "{" + root_field
            + "(startTime:" + str(start_ts)
            + ",endTime:" + str(end_ts)
            + ",limit:" + str(PAGE_SIZE)
            + ',scrollId:"' + scroll_id + '")'
            + "{nodes{" + ORDER_FIELDS + "}"
            + "scrollId more}}"
        )

        try:
            result = _sign_and_call(app_id, secret, q)
        except requests.exceptions.HTTPError as exc:
            body = ""
            if exc.response is not None:
                body = exc.response.text[:500]
            return all_nodes, "HTTP " + str(getattr(exc.response, "status_code", "?")) + ": " + body
        except requests.exceptions.RequestException as exc:
            return all_nodes, "Conexao: " + str(exc)

        if "errors" in result:
            msg = result["errors"][0].get("message", str(result["errors"]))
            return all_nodes, "GraphQL: " + msg

        data = result.get("data", {})
        root = data.get(root_field, {})
        if not root:
            for v in data.values():
                if isinstance(v, dict):
                    root = v
                    break

        nodes, scroll_id, has_more = _extract_from_root(root)
        all_nodes.extend(nodes)
        page += 1

        if not nodes:
            break

    return all_nodes, None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROCESSAMENTO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _is_blacklisted(status):
    s = (status or "").lower()
    return any(bl in s for bl in BLACKLIST)


def _effective_commission(order):
    net = _sf(order.get("netCommission"))
    if net > 0:
        return net, "Concluido"
    return _sf(order.get("estimatedTotalCommission")), "Pendente"


def process(raw):
    total_raw = len(raw)
    valid = []
    for o in raw:
        if _is_blacklisted(o.get("conversionStatus", "")):
            continue
        comm, ctype = _effective_commission(o)
        valid.append(
            {
                "ts": o.get("purchaseTime", 0),
                "status": o.get("conversionStatus", "-"),
                "commission": comm,
                "type": ctype,
            }
        )
    return valid, total_raw


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UI CARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def card(label, value, sub="", css=""):
    vc = "m-value " + css if css else "m-value"
    sub_html = '<div class="m-sub">' + sub + "</div>" if sub else ""
    st.markdown(
        '<div class="m-card">'
        + '<div class="m-label">'
        + label
        + "</div>"
        + '<div class="'
        + vc
        + '">'
        + value
        + "</div>"
        + sub_html
        + "</div>",
        unsafe_allow_html=True,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIDEBAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
try:
    _def_id = st.secrets["SHOPEE_APP_ID"]
    _def_sk = st.secrets["SHOPEE_SECRET"]
except Exception:
    _def_id = ""
    _def_sk = ""

with st.sidebar:
    st.markdown("### Credenciais")
    app_id = st.text_input("App ID", value=_def_id, type="password")
    secret = st.text_input("Secret Key", value=_def_sk, type="password")

    st.markdown("---")
    st.markdown("### Schema Explorer")
    st.caption("Descobre os campos reais da API")

    if st.button("Explorar Schema", use_container_width=True):
        if app_id and secret:
            with st.spinner("Introspection..."):
                fields, err = introspect_schema(app_id, secret)
            if err:
                st.error("Erro: " + str(err))
            elif fields:
                st.success(str(len(fields)) + " campos encontrados:")
                order_match = _find_order_query(fields)
                for f in sorted(fields):
                    is_match = f == order_match
                    cls = "schema-match" if is_match else ""
                    prefix = ">>> " if is_match else ""
                    st.markdown(
                        '<span class="schema-item '
                        + cls
                        + '">'
                        + prefix
                        + f
                        + "</span>",
                        unsafe_allow_html=True,
                    )
                if order_match:
                    st.success("Campo de pedidos: " + order_match)
                else:
                    st.warning("Nenhum campo com 'order' encontrado.")
            else:
                st.warning("Schema vazio ou introspection desabilitada.")
        else:
            st.warning("Preencha App ID e Secret primeiro.")

    st.markdown("---")
    st.markdown("### Override Manual")
    st.caption("Se a auto-deteccao falhar, insira o nome correto:")
    manual_root = st.text_input(
        "Root Query Field",
        value="",
        placeholder="ex: orderList",
        help="Deixe vazio para auto-deteccao",
    )

    st.markdown("---")
    st.caption(
        "purchaseAmount e customParameters "
        "NAO sao solicitados (restricao de acesso)."
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEADER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown(
    '<div class="hdr">Shopee Affiliates</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hdr-sub">'
    "Dashboard de Comissoes - API v2 GraphQL - Auto-Discovery"
    "</div>",
    unsafe_allow_html=True,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALENDARIO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
today = datetime.now(BR_TZ).date()
yesterday = today - timedelta(days=1)
day_before = today - timedelta(days=2)
thirty_ago = today - timedelta(days=30)

c_preset, c_start, c_end, c_btn = st.columns([2.2, 1.8, 1.8, 1])

with c_preset:
    preset = st.selectbox(
        "Periodo",
        ["Ontem", "Anteontem", "Ultimos 30 dias", "Personalizado"],
        label_visibility="collapsed",
    )

if preset == "Ontem":
    d_start, d_end = yesterday, yesterday
elif preset == "Anteontem":
    d_start, d_end = day_before, day_before
elif preset == "Ultimos 30 dias":
    d_start, d_end = thirty_ago, yesterday
else:
    d_start, d_end = yesterday, today

with c_start:
    start_date = st.date_input(
        "De", value=d_start, max_value=today, label_visibility="collapsed"
    )
with c_end:
    end_date = st.date_input(
        "Ate", value=d_end, max_value=today, label_visibility="collapsed"
    )
with c_btn:
    go = st.button("Consultar", use_container_width=True, type="primary")

st.markdown('<hr class="sep">', unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ESTADO VAZIO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if not go:
    st.markdown(
        '<div class="empty-state">'
        '<div class="icon">.</div>'
        '<div class="title">Selecione um periodo e clique em Consultar</div>'
        '<div class="desc">'
        "O sistema detecta automaticamente o schema da API - "
        "Configure credenciais no menu lateral"
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.stop()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VALIDACOES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if not app_id or not secret:
    st.error("Preencha App ID e Secret Key na barra lateral.")
    st.stop()

if start_date > end_date:
    st.error("Data inicial maior que data final.")
    st.stop()

start_ts = to_unix(start_date, end_of_day=False)
end_ts = to_unix(end_date, end_of_day=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASSO 1: DESCOBRIR ROOT FIELD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if manual_root.strip():
    root_field = manual_root.strip()
    schema_fields = []
    method_used = "override manual"
    st.info("Usando root field manual: " + root_field)
else:
    with st.spinner("Detectando schema da API..."):
        root_field, schema_fields, method_used = discover_root_field(
            app_id, secret, start_ts, end_ts
        )

    if not root_field:
        st.error("Nao foi possivel detectar o campo de pedidos na API.")

        if schema_fields:
            st.warning(
                "Schema encontrado com "
                + str(len(schema_fields))
                + " campos:"
            )
            cols_per_row = 4
            for i in range(0, len(schema_fields), cols_per_row):
                row = schema_fields[i : i + cols_per_row]
                cols = st.columns(cols_per_row)
                for j, f in enumerate(row):
                    cols[j].code(f)
            st.info(
                "Copie o nome correto e cole no campo "
                "'Override Manual' na barra lateral."
            )
        else:
            st.warning(
                "Introspection desabilitada e nenhum candidato funcionou. "
                "Tente inserir o nome manualmente na barra lateral."
            )

        with st.expander("Debug"):
            st.json(
                {
                    "endpoint": ENDPOINT,
                    "method": method_used,
                    "candidates_tested": ROOT_CANDIDATES,
                    "schema_fields": schema_fields,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                }
            )
        st.stop()

    st.success(
        "Campo detectado: "
        + root_field
        + " (via "
        + method_used
        + ")"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASSO 2: BUSCAR PEDIDOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.spinner("Buscando pedidos via " + root_field + "..."):
    raw_orders, error = fetch_orders(
        app_id, secret, start_ts, end_ts, root_field
    )

if error:
    st.error(error)
    with st.expander("Debug"):
        sample_q = (
            "{" + root_field
            + "(startTime:" + str(start_ts)
            + ",endTime:" + str(end_ts)
            + ',limit:1,scrollId:"")'
            + "{nodes{" + ORDER_FIELDS + "}"
            + "scrollId more}}"
        )
        st.code("Endpoint: " + ENDPOINT)
        st.code("Root field: " + root_field)
        st.code("Query:\n" + sample_q)
    st.stop()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASSO 3: PROCESSAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
valid_orders, total_raw = process(raw_orders)
total_valid = len(valid_orders)
total_comm = sum(o["commission"] for o in valid_orders)
conv_rate = (total_valid / total_raw * 100) if total_raw > 0 else 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4 METRICAS PRINCIPAIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
k1, k2, k3, k4 = st.columns(4, gap="medium")

with k1:
    card(
        "VENDAS TOTAIS",
        "--",
        "Indisponivel via API (purchaseAmount restrito)",
        css="muted",
    )
with k2:
    card(
        "PEDIDOS VALIDOS",
        str(total_valid),
        "de "
        + str(total_raw)
        + " retornados - "
        + str(total_raw - total_valid)
        + " removidos (blacklist)",
    )
with k3:
    card(
        "COMISSAO LIQUIDA",
        brl(total_comm),
        "net + estimated (pedidos validos)",
        css="green",
    )
with k4:
    card(
        "TAXA DE CONVERSAO",
        str(round(conv_rate, 1)) + "%",
        "Pedidos validos / total retornado",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BREAKDOWN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if valid_orders:
    st.markdown('<hr class="sep">', unsafe_allow_html=True)

    comm_done = sum(
        o["commission"] for o in valid_orders if o["type"] == "Concluido"
    )
    comm_pending = sum(
        o["commission"] for o in valid_orders if o["type"] == "Pendente"
    )
    qty_done = sum(1 for o in valid_orders if o["type"] == "Concluido")
    qty_pending = sum(1 for o in valid_orders if o["type"] == "Pendente")

    b1, b2 = st.columns(2, gap="medium")
    with b1:
        card(
            "COMISSAO CONCLUIDA",
            brl(comm_done),
            str(qty_done) + " pedido(s) - netCommission > 0",
            css="green",
        )
    with b2:
        card(
            "COMISSAO PENDENTE",
            brl(comm_pending),
            str(qty_pending) + " pedido(s) - estimatedTotalCommission",
            css="yellow",
        )

    # TABELA
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.markdown("#### Detalhamento")

    def _fmt_ts(ts):
        if ts and ts > 0:
            try:
                return datetime.fromtimestamp(
                    int(ts), tz=BR_TZ
                ).strftime("%d/%m/%Y %H:%M")
            except Exception:
                return "-"
        return "-"

    df = pd.DataFrame(valid_orders)
    df["Data / Hora"] = df["ts"].apply(_fmt_ts)
    df["Status"] = df["status"]
    df["Tipo"] = df["type"]
    df["Comissao (R$)"] = df["commission"].apply(brl)

    display = (
        df[["Data / Hora", "Status", "Tipo", "Comissao (R$)"]]
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
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.info(
        "Nenhum pedido valido no periodo "
        + start_date.strftime("%d/%m/%Y")
        + " - "
        + end_date.strftime("%d/%m/%Y")
        + "."
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RODAPE DEBUG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.expander("Debug / Parametros"):
    sample_q = (
        "{" + root_field
        + "(startTime:" + str(start_ts)
        + ",endTime:" + str(end_ts)
        + ",limit:" + str(PAGE_SIZE)
        + ',scrollId:"")'
        + "{nodes{" + ORDER_FIELDS + "}"
        + "scrollId more}}"
    )
    st.json(
        {
            "endpoint": ENDPOINT,
            "root_field": root_field,
            "discovery_method": method_used,
            "schema_fields": schema_fields if schema_fields else "(via brute-force)",
            "start_ts": start_ts,
            "end_ts": end_ts,
            "start_date_br": start_date.strftime("%d/%m/%Y"),
            "end_date_br": end_date.strftime("%d/%m/%Y"),
            "total_raw": total_raw,
            "total_valid": total_valid,
            "blacklist": list(BLACKLIST),
            "query": sample_q,
        }
    )
