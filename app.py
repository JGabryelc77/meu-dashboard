"""
Shopee Affiliates Dashboard - API v2 GraphQL
Endpoint: conversionReport
Layout inspirado em dashboards modernos de afiliados
"""
import streamlit as st
import requests
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone, date
import pandas as pd

# ================================================================
st.set_page_config(
    page_title="Shopee Affiliates",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
BLACKLIST = ("cancel", "reject", "invalid")
BR_TZ = timezone(timedelta(hours=-3))
MAX_PAGES = 50
PAGE_SIZE = 100

# ================================================================
# CSS - LAYOUT MODERNO
# ================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background-color: #0a0a0f !important;
    color: #e0e0e5;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { background: #0d0d14; border-right: 1px solid #1a1a25; }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1380px; }

/* ── HEADER ── */
.dash-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}
.dash-title {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
}
.dash-subtitle {
    font-size: 13px;
    color: #555566;
    margin-bottom: 20px;
}

/* ── METRIC CARDS ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
}
.metric-card {
    background: #12121a;
    border: 1px solid #1e1e2a;
    border-radius: 16px;
    padding: 22px 20px 18px;
    position: relative;
    transition: border-color 0.25s, transform 0.2s;
}
.metric-card:hover {
    border-color: #2a2a3a;
    transform: translateY(-1px);
}
.metric-icon {
    position: absolute;
    top: 18px;
    right: 18px;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
}
.icon-green  { background: #0d2a1a; color: #00d47b; }
.icon-orange { background: #2a1a0d; color: #ff8c42; }
.icon-blue   { background: #0d1a2a; color: #4d9fff; }
.icon-purple { background: #1a0d2a; color: #a855f7; }
.icon-gray   { background: #1a1a1a; color: #666; }

.metric-label {
    font-size: 11.5px;
    font-weight: 600;
    color: #666677;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 10px;
}
.metric-value {
    font-size: 28px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.1;
    letter-spacing: -0.5px;
    margin-bottom: 8px;
}
.metric-value.muted { color: #333344; }
.metric-value.green { color: #00d47b; }

.metric-sub {
    font-size: 11px;
    color: #555566;
    line-height: 1.4;
}
.metric-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    margin-bottom: 4px;
}
.badge-up { background: #0d2a1a; color: #00d47b; }
.badge-neutral { background: #1a1a25; color: #888899; }

/* ── SECTION CARDS ── */
.section-card {
    background: #12121a;
    border: 1px solid #1e1e2a;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
}
.section-title {
    font-size: 13px;
    font-weight: 700;
    color: #888899;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 20px;
}

/* ── STATUS BARS ── */
.status-bar-container {
    margin-bottom: 14px;
}
.status-bar-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.status-bar-name {
    font-size: 13px;
    color: #aaaabb;
    font-weight: 500;
}
.status-bar-value {
    font-size: 13px;
    color: #ffffff;
    font-weight: 700;
}
.status-bar-track {
    height: 8px;
    background: #1a1a25;
    border-radius: 4px;
    overflow: hidden;
}
.status-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
}
.bar-green  { background: linear-gradient(90deg, #00d47b, #00b866); }
.bar-yellow { background: linear-gradient(90deg, #f5a623, #e8941a); }
.bar-red    { background: linear-gradient(90deg, #ff4757, #e8384a); }
.bar-blue   { background: linear-gradient(90deg, #4d9fff, #3b82f6); }
.bar-purple { background: linear-gradient(90deg, #a855f7, #9333ea); }

/* ── BREAKDOWN MINI ── */
.breakdown-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
}
.breakdown-item {
    background: #0e0e16;
    border: 1px solid #1a1a25;
    border-radius: 12px;
    padding: 18px 16px;
    text-align: center;
}
.breakdown-label {
    font-size: 11px;
    font-weight: 600;
    color: #666677;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
.breakdown-value {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.3px;
}
.breakdown-count {
    font-size: 11px;
    color: #555566;
    margin-top: 4px;
}
.val-green  { color: #00d47b; }
.val-yellow { color: #f5a623; }

/* ── SEPARATOR ── */
.sep { border: none; border-top: 1px solid #1a1a25; margin: 24px 0; }

/* ── TABLE ── */
[data-testid="stDataFrame"] {
    border: 1px solid #1e1e2a;
    border-radius: 14px;
    overflow: hidden;
}

/* ── INPUTS / BUTTONS ── */
.stButton > button {
    background: linear-gradient(135deg, #ff6b35, #ff8c42) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 15px rgba(255,107,53,0.3) !important;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
.stDateInput > div > div > input,
.stTextInput > div > div > input {
    background-color: #12121a !important;
    color: #eee !important;
    border-color: #2a2a3a !important;
    border-radius: 10px !important;
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #2a2a3a; border-radius: 3px; }

.empty-state { text-align: center; padding: 80px 20px; }
.empty-state .icon { font-size: 48px; margin-bottom: 16px; color: #2a2a3a; }
.empty-state .title { font-size: 18px; font-weight: 600; color: #555566; margin-bottom: 6px; }
.empty-state .desc { font-size: 13px; color: #3a3a4a; }

/* ── DISCOVERY (hidden by default in production) ── */
.disc {
    background: #0e0e16;
    border: 1px solid #1a1a25;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 4px 0;
    font-family: monospace;
    font-size: 11.5px;
    color: #666677;
}
.disc b { color: #999aaa; }
.disc .ok { color: #00d47b; }
.disc .warn { color: #f5a623; }
.disc .err { color: #ff4757; }
</style>
""", unsafe_allow_html=True)

# ================================================================
# UTILIDADES
# ================================================================
def to_unix(d, end_of_day=False):
    h, m, s = (23, 59, 59) if end_of_day else (0, 0, 0)
    return int(datetime(d.year, d.month, d.day, h, m, s, tzinfo=BR_TZ).timestamp())

def brl(v):
    return "R$ " + "{:,.2f}".format(v).replace(",", "X").replace(".", ",").replace("X", ".")

def _sf(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0

# ================================================================
# API CORE
# ================================================================
def _sign_and_call(app_id, secret, query):
    payload = json.dumps({"query": query}, separators=(",", ":"), ensure_ascii=False)
    ts = str(int(time.time()))
    sig = hashlib.sha256((app_id + ts + payload + secret).encode("utf-8")).hexdigest()
    headers = {
        "Authorization": "SHA256 Credential=" + app_id + ", Timestamp=" + ts + ", Signature=" + sig,
        "Content-Type": "application/json",
    }
    resp = requests.post(ENDPOINT, headers=headers, data=payload.encode("utf-8"), timeout=30)
    resp.raise_for_status()
    return resp.json()

# ================================================================
# INTROSPECTION (same safe version)
# ================================================================
def _resolve_base(t):
    if not t or not isinstance(t, dict):
        return None, None, False
    is_list = False
    c = t
    depth = 0
    while c and isinstance(c, dict) and c.get("kind") in ("NON_NULL", "LIST") and depth < 10:
        if c.get("kind") == "LIST":
            is_list = True
        c = c.get("ofType")
        if not isinstance(c, dict):
            c = None
        depth += 1
    if not c or not isinstance(c, dict):
        return None, None, is_list
    return c.get("name"), c.get("kind"), is_list

def introspect_type_fields(app_id, secret, type_name):
    if not type_name:
        return [], "type_name vazio"
    q = '{__type(name:"' + type_name + '"){name kind fields{name type{name kind ofType{name kind ofType{name kind ofType{name kind}}}}}}}'
    try:
        r = _sign_and_call(app_id, secret, q)
    except Exception as e:
        return [], str(e)
    if "errors" in r:
        return [], r["errors"][0].get("message", "")
    td = r.get("data", {}).get("__type")
    if not td or not isinstance(td, dict):
        return [], type_name + " nao encontrado"
    fields = []
    for f in td.get("fields", []):
        if not isinstance(f, dict):
            continue
        bname, bkind, is_list = _resolve_base(f.get("type"))
        fields.append({
            "name": f.get("name", "?"),
            "type_name": bname,
            "type_kind": bkind,
            "is_list": is_list,
            "is_scalar": bkind in ("SCALAR", "ENUM") if bkind else False,
        })
    return fields, None

def introspect_deep(app_id, secret, type_name, depth=3, visited=None):
    if visited is None:
        visited = set()
    if not type_name or type_name in visited or depth <= 0:
        return {"name": type_name or "?", "fields": []}
    visited.add(type_name)
    fields, err = introspect_type_fields(app_id, secret, type_name)
    if err:
        return {"name": type_name, "fields": [], "error": err}
    result = {"name": type_name, "fields": []}
    for f in fields:
        fd = dict(f)
        if not fd["is_scalar"] and fd["type_name"] and fd["type_name"] not in visited and depth > 1:
            fd["sub"] = introspect_deep(app_id, secret, fd["type_name"], depth - 1, visited.copy())
        result["fields"].append(fd)
    return result

def fields_from_tree(tree):
    if not tree or not isinstance(tree, dict):
        return ""
    parts = []
    for f in tree.get("fields", []):
        if not isinstance(f, dict):
            continue
        name = f.get("name", "")
        if not name:
            continue
        if f.get("is_scalar"):
            parts.append(name)
        elif "sub" in f and isinstance(f["sub"], dict) and f["sub"].get("fields"):
            sub_str = fields_from_tree(f["sub"])
            if sub_str:
                parts.append(name + "{" + sub_str + "}")
    return " ".join(parts)

# ================================================================
# UI COMPONENTS
# ================================================================
def render_metric_card(label, value, sub="", icon="$", icon_class="icon-green", badge="", value_class=""):
    badge_html = ""
    if badge:
        badge_html = '<div class="metric-badge badge-neutral">' + badge + '</div>'
    vc = "metric-value " + value_class if value_class else "metric-value"
    st.markdown(
        '<div class="metric-card">'
        + '<div class="metric-icon ' + icon_class + '">' + icon + '</div>'
        + '<div class="metric-label">' + label + '</div>'
        + badge_html
        + '<div class="' + vc + '">' + value + '</div>'
        + '<div class="metric-sub">' + sub + '</div>'
        + '</div>',
        unsafe_allow_html=True,
    )

def render_status_bar(name, value, total, bar_class="bar-green"):
    pct = (value / total * 100) if total > 0 else 0
    st.markdown(
        '<div class="status-bar-container">'
        + '<div class="status-bar-label">'
        + '<span class="status-bar-name">' + name + '</span>'
        + '<span class="status-bar-value">' + brl(value) + '</span>'
        + '</div>'
        + '<div class="status-bar-track">'
        + '<div class="status-bar-fill ' + bar_class + '" style="width:' + str(max(pct, 2)) + '%"></div>'
        + '</div></div>',
        unsafe_allow_html=True,
    )

def show_disc(label, value, status="ok"):
    st.markdown(
        '<div class="disc"><b>' + label + ':</b> '
        + '<span class="' + status + '">' + str(value) + '</span></div>',
        unsafe_allow_html=True,
    )

# ================================================================
# SIDEBAR
# ================================================================
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
    st.caption("Usa conversionReport (endpoint acessivel)")

# ================================================================
# HEADER + CALENDARIO
# ================================================================
st.markdown(
    '<div class="dash-title">Dashboard</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="dash-subtitle">Shopee Affiliates - Comissoes em tempo real</div>',
    unsafe_allow_html=True,
)

today = datetime.now(BR_TZ).date()
yesterday = today - timedelta(days=1)
day_before = today - timedelta(days=2)
thirty_ago = today - timedelta(days=30)

c_preset, c_start, c_end, c_btn = st.columns([2.5, 1.5, 1.5, 1])
with c_preset:
    preset = st.selectbox("Periodo",
        ["Ontem", "Anteontem", "Ultimos 30 dias", "Personalizado"],
        label_visibility="collapsed")

if preset == "Ontem":
    d_s, d_e = yesterday, yesterday
elif preset == "Anteontem":
    d_s, d_e = day_before, day_before
elif preset == "Ultimos 30 dias":
    d_s, d_e = thirty_ago, yesterday
else:
    d_s, d_e = yesterday, today

with c_start:
    start_date = st.date_input("De", value=d_s, max_value=today, label_visibility="collapsed")
with c_end:
    end_date = st.date_input("Ate", value=d_e, max_value=today, label_visibility="collapsed")
with c_btn:
    go = st.button("Consultar", use_container_width=True, type="primary")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# EMPTY STATE
# ================================================================
if not go:
    st.markdown(
        '<div class="empty-state">'
        '<div class="icon">S</div>'
        '<div class="title">Selecione um periodo e clique Consultar</div>'
        '<div class="desc">Os dados serao carregados de conversionReport via GraphQL</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

if not app_id or not secret:
    st.error("Preencha App ID e Secret Key na barra lateral.")
    st.stop()
if start_date > end_date:
    st.error("Data inicial maior que data final.")
    st.stop()

start_ts = to_unix(start_date, end_of_day=False)
end_ts = to_unix(end_date, end_of_day=True)

# ================================================================
# INTROSPECT + FETCH (collapsed - runs silently)
# ================================================================
with st.spinner("Conectando a API..."):
    # 1. Introspect ConversionReportConnection
    conn_fields, conn_err = introspect_type_fields(app_id, secret, "ConversionReportConnection")

if conn_err:
    st.error("Erro na conexao: " + conn_err)
    st.stop()

conn_field_names = [f["name"] for f in conn_fields]
list_field = None
list_type = None
for f in conn_fields:
    if f["name"] == "nodes" or (f.get("is_list") and not f.get("is_scalar")):
        list_field = f["name"]
        list_type = f.get("type_name")
        break

has_scroll = "scrollId" in conn_field_names
has_more = "more" in conn_field_names

# 2. Introspect node type
node_type = list_type or "ConversionReport"
with st.spinner("Descobrindo campos..."):
    node_tree = introspect_deep(app_id, secret, node_type, depth=3)

node_fields_str = fields_from_tree(node_tree)
if not node_fields_str:
    node_fields_list, _ = introspect_type_fields(app_id, secret, node_type)
    scalars = [f["name"] for f in node_fields_list if f.get("is_scalar")]
    node_fields_str = " ".join(scalars)

all_node_fields, _ = introspect_type_fields(app_id, secret, node_type)
all_field_names = [f["name"] for f in all_node_fields]

# 3. Test query
extra_conn = ""
if has_scroll:
    extra_conn += " scrollId"
if has_more:
    extra_conn += " more"

test_args = "purchaseTimeStart:" + str(start_ts) + ",purchaseTimeEnd:" + str(end_ts) + ",limit:2"
if list_field and node_fields_str:
    test_body = list_field + "{" + node_fields_str + "}" + extra_conn
else:
    test_body = node_fields_str + extra_conn

test_q = "{conversionReport(" + test_args + "){" + test_body + "}}"

with st.spinner("Testando conexao..."):
    try:
        test_result = _sign_and_call(app_id, secret, test_q)
    except Exception as exc:
        test_result = {"errors": [{"message": str(exc)}]}

if "errors" in test_result:
    # Try scalars only
    scalars_only = " ".join(f["name"] for f in all_node_fields if f.get("is_scalar"))
    if scalars_only and list_field:
        q_v1 = "{conversionReport(" + test_args + "){" + list_field + "{" + scalars_only + "}" + extra_conn + "}}"
        try:
            r_v1 = _sign_and_call(app_id, secret, q_v1)
            if "errors" not in r_v1:
                test_result = r_v1
                node_fields_str = scalars_only
        except Exception:
            pass

    if "errors" in test_result:
        st.error("Erro na query: " + test_result["errors"][0].get("message", ""))
        with st.expander("Debug"):
            st.code(test_q, language="graphql")
        st.stop()

# 4. Fetch all data
all_nodes = []
scroll_id = None
page = 0
last_query = ""

with st.spinner("Buscando dados..."):
    while page < MAX_PAGES:
        args_parts = [
            "purchaseTimeStart:" + str(start_ts),
            "purchaseTimeEnd:" + str(end_ts),
            "limit:" + str(PAGE_SIZE),
        ]
        if scroll_id:
            args_parts.append('scrollId:"' + str(scroll_id) + '"')

        body = ""
        if list_field:
            body = list_field + "{" + node_fields_str + "}"
        else:
            body = node_fields_str
        if has_scroll:
            body += " scrollId"
        if has_more:
            body += " more"

        q = "{conversionReport(" + ",".join(args_parts) + "){" + body + "}}"
        last_query = q

        try:
            result = _sign_and_call(app_id, secret, q)
        except Exception as exc:
            st.error(str(exc))
            break

        if "errors" in result:
            st.error("GraphQL: " + result["errors"][0].get("message", ""))
            break

        data = result.get("data", {}).get("conversionReport", {})
        nodes = []
        if list_field and list_field in data:
            nodes = data.get(list_field, [])
            if not isinstance(nodes, list):
                nodes = []
        elif isinstance(data, list):
            nodes = data

        all_nodes.extend(nodes)
        if not nodes:
            break

        new_scroll = data.get("scrollId")
        has_more_val = data.get("more", False)
        if has_more_val and new_scroll and str(new_scroll) != str(scroll_id):
            scroll_id = str(new_scroll)
        else:
            break
        page += 1

# ================================================================
# PROCESS DATA
# ================================================================
valid_orders = []
total_raw = len(all_nodes)
status_counts = {}

for o in all_nodes:
    if not isinstance(o, dict):
        continue

    net = 0.0
    est = 0.0
    for k in ["netCommission", "commission", "commissionAmount", "affiliateCommission",
              "netAmount", "payout", "earning", "earnings"]:
        v = _sf(o.get(k))
        if v > 0:
            net = v
            break
    for k in ["estimatedTotalCommission", "estimatedCommission", "pendingCommission",
              "estimatedAmount"]:
        v = _sf(o.get(k))
        if v > 0:
            est = v
            break
    if net == 0 and est == 0:
        for k in ["actualAmount", "amount", "totalAmount", "orderAmount",
                   "purchaseAmount", "saleAmount"]:
            v = _sf(o.get(k))
            if v > 0:
                est = v
                break

    status = "-"
    for k in ["conversionStatus", "orderStatus", "status", "displayStatus"]:
        v = o.get(k)
        if v and str(v).strip() and str(v) != "None":
            status = str(v)
            break

    if status not in status_counts:
        status_counts[status] = {"count": 0, "comm": 0.0}

    if any(bl in (status or "").lower() for bl in BLACKLIST):
        status_counts[status]["count"] += 1
        continue

    ts = 0
    for k in ["purchaseTime", "createdTime", "createTime", "timestamp",
              "time", "completeTime"]:
        v = o.get(k)
        if v and isinstance(v, (int, float)) and v > 1000000000:
            ts = int(v)
            break

    if net > 0:
        ctype = "Concluido"
        comm = net
    elif est > 0:
        ctype = "Pendente"
        comm = est
    else:
        ctype = "Pendente"
        comm = 0.0

    status_counts[status]["count"] += 1
    status_counts[status]["comm"] += comm

    valid_orders.append({
        "ts": ts,
        "status": status,
        "commission": comm,
        "type": ctype,
        "raw": o,
    })

total_valid = len(valid_orders)
total_comm = sum(o["commission"] for o in valid_orders)
conv_rate = (total_valid / total_raw * 100) if total_raw > 0 else 0.0
c_done = sum(o["commission"] for o in valid_orders if o["type"] == "Concluido")
c_pend = sum(o["commission"] for o in valid_orders if o["type"] == "Pendente")
q_done = sum(1 for o in valid_orders if o["type"] == "Concluido")
q_pend = sum(1 for o in valid_orders if o["type"] == "Pendente")
ticket_medio = (total_comm / total_valid) if total_valid > 0 else 0.0

# ================================================================
# RENDER DASHBOARD
# ================================================================

# 5 METRIC CARDS
k1, k2, k3, k4, k5 = st.columns(5, gap="small")
with k1:
    render_metric_card(
        "Vendas Totais", "--",
        "purchaseAmount restrito",
        icon="~", icon_class="icon-gray",
        value_class="muted"
    )
with k2:
    render_metric_card(
        "Pedidos", str(total_valid),
        str(total_raw) + " retornados total",
        icon="#", icon_class="icon-orange",
        badge=str(total_raw - total_valid) + " filtrados" if total_raw > total_valid else ""
    )
with k3:
    render_metric_card(
        "Comissao Liquida", brl(total_comm),
        "net + estimated combinados",
        icon="$", icon_class="icon-green",
        value_class="green"
    )
with k4:
    render_metric_card(
        "Ticket Medio", brl(ticket_medio),
        "comissao / pedidos validos",
        icon="=", icon_class="icon-blue"
    )
with k5:
    render_metric_card(
        "Comissao Validada", brl(c_done),
        str(q_done) + " pedido(s) concluido(s)",
        icon="!", icon_class="icon-purple"
    )

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# COMISSAO POR STATUS + BREAKDOWN
if valid_orders or total_raw > 0:
    col_left, col_right = st.columns([1.2, 1], gap="medium")

    with col_left:
        st.markdown(
            '<div class="section-card">'
            '<div class="section-title">Comissao por Status</div>',
            unsafe_allow_html=True,
        )

        max_val = max(c_done, c_pend, 0.01)

        if c_done > 0:
            render_status_bar("Concluido", c_done, max_val, "bar-green")
        if c_pend > 0:
            render_status_bar("Pendente", c_pend, max_val, "bar-yellow")

        # Show other statuses from status_counts
        for sname, sdata in sorted(status_counts.items(), key=lambda x: x[1]["comm"], reverse=True):
            if sname in ("-",) or sdata["comm"] <= 0:
                continue
            if any(bl in sname.lower() for bl in BLACKLIST):
                render_status_bar(sname + " (filtrado)", sdata["comm"], max_val, "bar-red")

        if c_done == 0 and c_pend == 0:
            st.markdown('<div class="metric-sub">Nenhuma comissao registrada</div>',
                        unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown(
            '<div class="section-card">'
            '<div class="section-title">Resumo</div>'
            '<div class="breakdown-grid">',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="breakdown-item">'
            '<div class="breakdown-label">Concluida</div>'
            '<div class="breakdown-value val-green">' + brl(c_done) + '</div>'
            '<div class="breakdown-count">' + str(q_done) + ' pedido(s)</div>'
            '</div>'
            '<div class="breakdown-item">'
            '<div class="breakdown-label">Pendente</div>'
            '<div class="breakdown-value val-yellow">' + brl(c_pend) + '</div>'
            '<div class="breakdown-count">' + str(q_pend) + ' pedido(s)</div>'
            '</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="sep">', unsafe_allow_html=True)

    # EVOLUCAO DA COMISSAO (chart)
    if valid_orders:
        orders_with_time = [o for o in valid_orders if o["ts"] > 0 and o["commission"] > 0]

        if orders_with_time:
            st.markdown(
                '<div class="section-card">'
                '<div class="section-title">Evolucao da Comissao</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            chart_data = []
            for o in orders_with_time:
                chart_data.append({
                    "data": datetime.fromtimestamp(o["ts"], tz=BR_TZ).strftime("%d/%m"),
                    "comissao": o["commission"],
                })

            df_chart = pd.DataFrame(chart_data)
            if not df_chart.empty:
                # Agrupar por data
                df_grouped = df_chart.groupby("data")["comissao"].sum().reset_index()
                df_grouped.columns = ["Data", "Comissao"]

                st.bar_chart(
                    df_grouped.set_index("Data"),
                    color="#00d47b",
                    height=280,
                )

        st.markdown('<hr class="sep">', unsafe_allow_html=True)

    # TABELA DE PEDIDOS
    st.markdown(
        '<div class="section-title" style="margin-bottom:12px">Detalhamento dos Pedidos</div>',
        unsafe_allow_html=True,
    )

    def _fmt_ts(ts):
        if ts and ts > 0:
            try:
                return datetime.fromtimestamp(int(ts), tz=BR_TZ).strftime("%d/%m/%Y %H:%M")
            except Exception:
                return "-"
        return "-"

    df = pd.DataFrame([{
        "Data/Hora": _fmt_ts(o["ts"]),
        "Status": o["status"],
        "Tipo": o["type"],
        "Comissao": brl(o["commission"]),
    } for o in valid_orders])

    if not df.empty:
        display = df.sort_values("Data/Hora", ascending=False).reset_index(drop=True)
        st.dataframe(display, use_container_width=True, hide_index=True,
                     height=min(520, 36 * len(display) + 40))
    else:
        st.info("Nenhum pedido para exibir")

elif total_raw == 0:
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.info("Nenhum registro retornado para "
            + start_date.strftime("%d/%m/%Y") + " - "
            + end_date.strftime("%d/%m/%Y"))

# ================================================================
# DEBUG (collapsed)
# ================================================================
with st.expander("Debug / Schema"):
    st.json({
        "endpoint": ENDPOINT,
        "root_field": "conversionReport",
        "connection_fields": conn_field_names,
        "node_type": node_type,
        "node_fields": node_fields_str,
        "all_node_fields": all_field_names,
        "has_scroll": has_scroll,
        "has_more": has_more,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "total_raw": total_raw,
        "total_valid": total_valid,
        "pages_fetched": page + 1,
        "last_query": last_query,
        "status_breakdown": {k: v for k, v in status_counts.items()},
    })
    if all_nodes:
        st.markdown("**Amostra (primeiro registro):**")
        st.json(all_nodes[0] if all_nodes else {})
