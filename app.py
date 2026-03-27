"""
Shopee Affiliates Dashboard - API v2 GraphQL
Root field: partnerOrderReport (descoberto via introspection)
"""
import streamlit as st
import requests
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone, date
import pandas as pd

# ================================================================
# CONFIG
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

DESIRED_FIELDS = [
    "purchaseTime",
    "conversionStatus",
    "netCommission",
    "estimatedTotalCommission",
]

# ================================================================
# CSS - DARK MODE
# ================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*,*::before,*::after{box-sizing:border-box}
.stApp{background-color:#000!important;color:#e5e5e5;
    font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background:#080808;border-right:1px solid #1a1a1a}
.block-container{padding:2rem 2.5rem 3rem;max-width:1280px}
.m-card{background:#111;border:1px solid #222;border-radius:14px;
    padding:28px 24px;transition:border-color .25s,box-shadow .25s}
.m-card:hover{border-color:#333;box-shadow:0 0 0 1px #222}
.m-label{font-size:12px;font-weight:600;color:#666;
    text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px}
.m-value{font-size:34px;font-weight:800;color:#fff;
    line-height:1.15;letter-spacing:-.5px}
.m-sub{font-size:11.5px;color:#4a4a4a;margin-top:10px;line-height:1.4}
.green{color:#00d47b!important}
.yellow{color:#f5a623!important}
.muted{color:#333!important}
.hdr{font-size:30px;font-weight:800;color:#fff;letter-spacing:-.6px}
.hdr-sub{font-size:14px;color:#555;margin-bottom:28px}
.sep{border:none;border-top:1px solid #1a1a1a;margin:28px 0}
.disc{background:#0a0a0a;border:1px solid #1a1a1a;border-radius:10px;
    padding:14px 18px;margin:6px 0;font-family:monospace;font-size:12.5px;color:#888}
.disc b{color:#ccc}
.disc .ok{color:#00d47b}
.disc .warn{color:#f5a623}
.stButton>button{background:#111!important;color:#fff!important;
    border:1px solid #333!important;border-radius:10px!important;
    font-weight:600!important;transition:all .2s!important}
.stButton>button:hover{background:#1a1a1a!important;border-color:#555!important}
div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,
.stDateInput>div>div>input,.stTextInput>div>div>input{
    background-color:#111!important;color:#eee!important;
    border-color:#333!important;border-radius:8px!important}
[data-testid="stDataFrame"]{border:1px solid #222;border-radius:12px;overflow:hidden}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:#000}
::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
.empty-state{text-align:center;padding:100px 20px;color:#333}
.empty-state .icon{font-size:52px;margin-bottom:16px}
.empty-state .title{font-size:18px;font-weight:600;color:#555;margin-bottom:6px}
.empty-state .desc{font-size:13px;color:#3a3a3a}
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
# API CORE - ASSINATURA SHA256 + CHAMADA
# ================================================================
def _sign_and_call(app_id, secret, query):
    payload = json.dumps({"query": query}, separators=(",", ":"), ensure_ascii=False)
    ts = str(int(time.time()))
    sig = hashlib.sha256((app_id + ts + payload + secret).encode("utf-8")).hexdigest()
    headers = {
        "Authorization": (
            "SHA256 Credential=" + app_id
            + ", Timestamp=" + ts
            + ", Signature=" + sig
        ),
        "Content-Type": "application/json",
    }
    resp = requests.post(ENDPOINT, headers=headers,
                         data=payload.encode("utf-8"), timeout=30)
    resp.raise_for_status()
    return resp.json()

# ================================================================
# INTROSPECTION - DESCOBRE CAMPOS DO NODE
# ================================================================
def _resolve_type_name(t):
    """Desembrulha NON_NULL e LIST ate o tipo base."""
    if not t:
        return None
    if t.get("kind") in ("NON_NULL", "LIST"):
        return _resolve_type_name(t.get("ofType"))
    return t.get("name")

def introspect_node_fields(app_id, secret):
    """
    Descobre quais campos estao disponiveis dentro dos nodes
    de partnerOrderReport.
    Retorna: (info_dict, error_string)
    """
    # Passo 1: Pegar o tipo de retorno de partnerOrderReport
    q1 = (
        '{__type(name:"Query"){fields{name'
        ' type{name kind ofType{name kind ofType{name kind ofType{name kind}}}}'
        '}}}'
    )
    try:
        r1 = _sign_and_call(app_id, secret, q1)
    except Exception as exc:
        return None, "Erro introspection Query: " + str(exc)

    if "errors" in r1:
        return None, r1["errors"][0].get("message", "")

    all_fields = r1.get("data", {}).get("__type", {}).get("fields", [])
    target = None
    for f in all_fields:
        if f.get("name") == "partnerOrderReport":
            target = f
            break

    if not target:
        return None, "partnerOrderReport nao encontrado no schema"

    ret_type = _resolve_type_name(target.get("type"))
    if not ret_type:
        return None, "Tipo de retorno nao resolvido"

    # Passo 2: Introspeccionar PartnerOrderReportConnection
    q2 = (
        '{__type(name:"' + ret_type + '"){fields{name'
        ' type{name kind ofType{name kind ofType{name kind ofType{name kind}}}}'
        '}}}'
    )
    try:
        r2 = _sign_and_call(app_id, secret, q2)
    except Exception as exc:
        return None, "Erro introspection " + ret_type + ": " + str(exc)

    if "errors" in r2:
        return None, r2["errors"][0].get("message", "")

    conn_fields = r2.get("data", {}).get("__type", {}).get("fields", [])
    conn_field_names = [f["name"] for f in conn_fields]

    # Encontrar o campo "nodes" e seu tipo
    nodes_f = None
    for f in conn_fields:
        if f.get("name") == "nodes":
            nodes_f = f
            break

    if not nodes_f:
        return {
            "return_type": ret_type,
            "connection_fields": conn_field_names,
            "node_type": None,
            "node_fields": [],
        }, None

    node_type_name = _resolve_type_name(nodes_f.get("type"))
    if not node_type_name:
        return {
            "return_type": ret_type,
            "connection_fields": conn_field_names,
            "node_type": None,
            "node_fields": [],
        }, None

    # Passo 3: Introspeccionar o tipo do node
    q3 = (
        '{__type(name:"' + node_type_name + '"){fields{name'
        ' type{name kind ofType{name kind}}'
        '}}}'
    )
    try:
        r3 = _sign_and_call(app_id, secret, q3)
    except Exception as exc:
        return None, "Erro introspection " + node_type_name + ": " + str(exc)

    if "errors" in r3:
        return None, r3["errors"][0].get("message", "")

    node_fields = r3.get("data", {}).get("__type", {}).get("fields", [])

    return {
        "return_type": ret_type,
        "connection_fields": conn_field_names,
        "node_type": node_type_name,
        "node_fields": [f["name"] for f in node_fields],
    }, None

# ================================================================
# CONSTRUCAO DA QUERY
# ================================================================
def build_query(start_ts, end_ts, limit, fields_str, conn_extra_fields, token=None):
    """
    Monta a query para partnerOrderReport.
    IMPORTANTE: searchNextToken so eh incluido quando token != None
    (evita o erro syntax error: unexpected "")
    """
    args = (
        "purchaseTimeStart:" + str(start_ts)
        + ",purchaseTimeEnd:" + str(end_ts)
        + ",completeTimeStart:" + str(start_ts)
        + ",completeTimeEnd:" + str(end_ts)
        + ",limit:" + str(limit)
    )
    # SO adiciona searchNextToken se temos um token real
    if token is not None and token != "":
        args += ',searchNextToken:"' + str(token) + '"'

    # Montar campos de retorno
    inner = "nodes{" + fields_str + "}"
    # Adicionar searchNextToken no retorno se existir no connection type
    if "searchNextToken" in conn_extra_fields:
        inner += " searchNextToken"

    q = "{partnerOrderReport(" + args + "){" + inner + "}}"
    return q

# ================================================================
# FETCH ORDERS - PAGINACAO
# ================================================================
def fetch_orders(app_id, secret, start_ts, end_ts, fields_str, conn_extra_fields):
    all_nodes = []
    token = None  # None = nao incluir na primeira chamada
    page = 0
    last_query = ""

    while page < MAX_PAGES:
        q = build_query(start_ts, end_ts, PAGE_SIZE, fields_str, conn_extra_fields, token)
        last_query = q

        try:
            result = _sign_and_call(app_id, secret, q)
        except requests.exceptions.HTTPError as exc:
            code = getattr(exc.response, "status_code", "?")
            body = ""
            if exc.response is not None:
                body = exc.response.text[:500]
            return all_nodes, "HTTP " + str(code) + ": " + body, q
        except Exception as exc:
            return all_nodes, str(exc), q

        if "errors" in result:
            msg = result["errors"][0].get("message", str(result["errors"]))
            return all_nodes, "GraphQL: " + msg, q

        data = result.get("data", {}).get("partnerOrderReport", {})
        nodes = data.get("nodes", [])
        all_nodes.extend(nodes)

        if not nodes:
            break

        # Paginacao via searchNextToken
        new_token = data.get("searchNextToken")
        if new_token and str(new_token) != "" and str(new_token) != str(token):
            token = str(new_token)
        else:
            break

        page += 1

    return all_nodes, None, last_query

# ================================================================
# PROCESSAMENTO DE DADOS
# ================================================================
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
        valid.append({
            "ts": o.get("purchaseTime", 0),
            "status": o.get("conversionStatus", "-"),
            "commission": comm,
            "type": ctype,
        })
    return valid, total_raw

# ================================================================
# UI COMPONENTS
# ================================================================
def card(label, value, sub="", css=""):
    vc = "m-value " + css if css else "m-value"
    sub_html = '<div class="m-sub">' + sub + "</div>" if sub else ""
    st.markdown(
        '<div class="m-card">'
        + '<div class="m-label">' + label + "</div>"
        + '<div class="' + vc + '">' + value + "</div>"
        + sub_html + "</div>",
        unsafe_allow_html=True,
    )

def show_disc(label, value, status="ok"):
    cls = "ok" if status == "ok" else "warn"
    st.markdown(
        '<div class="disc"><b>' + label + ':</b> '
        + '<span class="' + cls + '">' + str(value) + "</span></div>",
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
    st.caption(
        "purchaseAmount e customParameters "
        "NAO sao solicitados (restricao de acesso)."
    )

# ================================================================
# HEADER
# ================================================================
st.markdown('<div class="hdr">Shopee Affiliates</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hdr-sub">'
    "Dashboard de Comissoes - API v2 GraphQL - partnerOrderReport"
    "</div>",
    unsafe_allow_html=True,
)

# ================================================================
# CALENDARIO
# ================================================================
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
    d_s, d_e = yesterday, yesterday
elif preset == "Anteontem":
    d_s, d_e = day_before, day_before
elif preset == "Ultimos 30 dias":
    d_s, d_e = thirty_ago, yesterday
else:
    d_s, d_e = yesterday, today

with c_start:
    start_date = st.date_input("De", value=d_s, max_value=today,
                               label_visibility="collapsed")
with c_end:
    end_date = st.date_input("Ate", value=d_e, max_value=today,
                             label_visibility="collapsed")
with c_btn:
    go = st.button("Consultar", use_container_width=True, type="primary")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# ESTADO VAZIO
# ================================================================
if not go:
    st.markdown(
        '<div class="empty-state">'
        '<div class="icon">.</div>'
        '<div class="title">Selecione um periodo e clique Consultar</div>'
        '<div class="desc">partnerOrderReport com introspection automatica</div>'
        "</div>",
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
# FASE 1: INTROSPECTION DOS CAMPOS
# ================================================================
st.markdown("#### Descoberta do schema")

with st.spinner("Introspectando campos de partnerOrderReport..."):
    schema_info, intro_err = introspect_node_fields(app_id, secret)

if intro_err:
    st.error("Erro na introspection: " + intro_err)
    st.info("Tentando com campos padrao...")
    schema_info = None

if schema_info:
    show_disc("Tipo retorno", schema_info.get("return_type", "?"))
    show_disc("Campos connection", ", ".join(schema_info.get("connection_fields", [])))
    show_disc("Tipo node", str(schema_info.get("node_type", "?")))

    available = schema_info.get("node_fields", [])
    if available:
        show_disc("Campos node (" + str(len(available)) + ")", ", ".join(available))

        # Validar quais dos nossos campos desejados existem
        valid_fields = [f for f in DESIRED_FIELDS if f in available]
        missing = [f for f in DESIRED_FIELDS if f not in available]

        if missing:
            show_disc("Campos indisponiveis", ", ".join(missing), status="warn")

        if not valid_fields:
            # Nenhum campo desejado existe - usar todos os disponiveis
            st.warning("Nenhum campo desejado encontrado. Usando todos os campos disponiveis.")
            valid_fields = available

        fields_str = " ".join(valid_fields)
    else:
        st.warning("Nao foi possivel descobrir campos do node. Usando padrao.")
        fields_str = " ".join(DESIRED_FIELDS)

    conn_extra = schema_info.get("connection_fields", [])
else:
    fields_str = " ".join(DESIRED_FIELDS)
    conn_extra = ["searchNextToken"]

show_disc("Campos solicitados", fields_str)

# Preview da query
preview_q = build_query(start_ts, end_ts, 1, fields_str, conn_extra, None)
with st.expander("Preview da query (primeira pagina)"):
    st.code(preview_q, language="graphql")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 2: BUSCAR PEDIDOS
# ================================================================
with st.spinner("Buscando pedidos..."):
    raw_orders, fetch_err, last_query = fetch_orders(
        app_id, secret, start_ts, end_ts, fields_str, conn_extra
    )

if fetch_err:
    st.error(fetch_err)
    with st.expander("Debug"):
        st.code("Ultima query:\n" + last_query, language="graphql")
        st.json({
            "endpoint": ENDPOINT,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "fields_requested": fields_str,
            "schema_info": schema_info,
        })
    st.stop()

# ================================================================
# FASE 3: PROCESSAR E EXIBIR
# ================================================================
valid_orders, total_raw = process(raw_orders)
total_valid = len(valid_orders)
total_comm = sum(o["commission"] for o in valid_orders)
conv_rate = (total_valid / total_raw * 100) if total_raw > 0 else 0.0

# 4 METRICAS
k1, k2, k3, k4 = st.columns(4, gap="medium")
with k1:
    card("VENDAS TOTAIS", "--",
         "Indisponivel via API (purchaseAmount restrito)", css="muted")
with k2:
    card("PEDIDOS VALIDOS", str(total_valid),
         "de " + str(total_raw) + " retornados - "
         + str(total_raw - total_valid) + " removidos")
with k3:
    card("COMISSAO LIQUIDA", brl(total_comm),
         "net + estimated (validos)", css="green")
with k4:
    card("TAXA CONVERSAO", str(round(conv_rate, 1)) + "%",
         "validos / total retornado")

# BREAKDOWN
if valid_orders:
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    c_done = sum(o["commission"] for o in valid_orders if o["type"] == "Concluido")
    c_pend = sum(o["commission"] for o in valid_orders if o["type"] == "Pendente")
    q_done = sum(1 for o in valid_orders if o["type"] == "Concluido")
    q_pend = sum(1 for o in valid_orders if o["type"] == "Pendente")

    b1, b2 = st.columns(2, gap="medium")
    with b1:
        card("COMISSAO CONCLUIDA", brl(c_done),
             str(q_done) + " pedido(s) - netCommission > 0", css="green")
    with b2:
        card("COMISSAO PENDENTE", brl(c_pend),
             str(q_pend) + " pedido(s) - estimatedTotalCommission", css="yellow")

    # TABELA
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.markdown("#### Detalhamento")

    def _fmt_ts(ts):
        if ts and ts > 0:
            try:
                return datetime.fromtimestamp(int(ts), tz=BR_TZ).strftime("%d/%m/%Y %H:%M")
            except Exception:
                return "-"
        return "-"

    df = pd.DataFrame(valid_orders)
    df["Data/Hora"] = df["ts"].apply(_fmt_ts)
    df["Status"] = df["status"]
    df["Tipo"] = df["type"]
    df["Comissao"] = df["commission"].apply(brl)
    display = (
        df[["Data/Hora", "Status", "Tipo", "Comissao"]]
        .sort_values("Data/Hora", ascending=False)
        .reset_index(drop=True)
    )
    st.dataframe(display, use_container_width=True, hide_index=True,
                 height=min(520, 36 * len(display) + 40))
else:
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.info(
        "Nenhum pedido valido: "
        + start_date.strftime("%d/%m/%Y") + " - "
        + end_date.strftime("%d/%m/%Y")
    )

# RODAPE DEBUG
with st.expander("Debug completo"):
    st.json({
        "endpoint": ENDPOINT,
        "root_field": "partnerOrderReport",
        "args": "purchaseTimeStart, purchaseTimeEnd, completeTimeStart, completeTimeEnd, limit, searchNextToken",
        "fields_requested": fields_str,
        "schema_info": schema_info,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "total_raw": total_raw,
        "total_valid": total_valid,
        "last_query": last_query if last_query else preview_q,
    })
