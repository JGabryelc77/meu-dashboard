"""
Shopee Affiliates Dashboard - API v2 GraphQL
Deep Schema Discovery v3 - partnerOrderReport
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

# ================================================================
# CSS
# ================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*,*::before,*::after{box-sizing:border-box}
.stApp{background-color:#000!important;color:#e5e5e5;
    font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background:#080808;border-right:1px solid #1a1a1a}
.block-container{padding:2rem 2.5rem 3rem;max-width:1400px}
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
.disc .err{color:#ff4444}
.phase{background:#0a0a0a;border:1px solid #1a1a1a;border-radius:12px;
    padding:20px;margin:16px 0}
.phase-title{font-size:14px;font-weight:700;color:#fff;margin-bottom:12px}
.tree{font-family:monospace;font-size:12px;line-height:1.8;color:#888}
.tree .type{color:#3b82f6}
.tree .field{color:#e5e5e5}
.tree .scalar{color:#666}
.tree .nested{color:#f5a623}
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
# API CORE
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
# INTROSPECTION HELPERS
# ================================================================
def _resolve_base(t):
    """Desembrulha NON_NULL/LIST, retorna (name, kind, is_list)"""
    if not t:
        return None, None, False
    is_list = False
    c = t
    while c and c.get("kind") in ("NON_NULL", "LIST"):
        if c.get("kind") == "LIST":
            is_list = True
        c = c.get("ofType", {})
    if not c:
        return None, None, is_list
    return c.get("name"), c.get("kind"), is_list

# ================================================================
# INTROSPECTION PHASE 1: ALL ROOT QUERIES
# ================================================================
def list_root_queries(app_id, secret):
    q = "{__schema{queryType{fields{name}}}}"
    try:
        r = _sign_and_call(app_id, secret, q)
    except Exception as e:
        return [], str(e)
    if "errors" in r:
        return [], r["errors"][0].get("message", "")
    fs = r.get("data", {}).get("__schema", {}).get("queryType", {}).get("fields", [])
    return [f["name"] for f in fs if isinstance(f, dict)], None

# ================================================================
# INTROSPECTION PHASE 2: FIELD ARGS (required vs optional)
# ================================================================
def get_field_args(app_id, secret, field_name):
    q = (
        '{__type(name:"Query"){fields{name'
        ' args{name type{kind name ofType{kind name ofType{kind name ofType{kind name}}}}}'
        '}}}'
    )
    try:
        r = _sign_and_call(app_id, secret, q)
    except Exception as e:
        return [], str(e)
    if "errors" in r:
        return [], r["errors"][0].get("message", "")

    for f in r.get("data", {}).get("__type", {}).get("fields", []):
        if f.get("name") == field_name:
            args = []
            for a in f.get("args", []):
                t = a.get("type", {})
                required = t.get("kind") == "NON_NULL"
                bname, bkind, _ = _resolve_base(t)
                args.append({
                    "name": a["name"],
                    "type": bname,
                    "required": required,
                })
            return args, None
    return [], field_name + " nao encontrado"

# ================================================================
# INTROSPECTION PHASE 3: TYPE FIELDS (deep)
# ================================================================
def get_type_fields(app_id, secret, type_name):
    q = (
        '{__type(name:"' + type_name + '"){name kind'
        ' fields{name type{name kind ofType{name kind ofType{name kind ofType{name kind}}}}}'
        '}}'
    )
    try:
        r = _sign_and_call(app_id, secret, q)
    except Exception as e:
        return None, str(e)
    if "errors" in r:
        return None, r["errors"][0].get("message", "")

    td = r.get("data", {}).get("__type")
    if not td:
        return None, type_name + " nao encontrado"

    fields = []
    for f in td.get("fields", []):
        bname, bkind, is_list = _resolve_base(f.get("type"))
        fields.append({
            "name": f["name"],
            "type": bname,
            "kind": bkind,
            "is_list": is_list,
            "is_scalar": bkind in ("SCALAR", "ENUM"),
        })

    return {
        "name": td.get("name"),
        "type_kind": td.get("kind"),
        "fields": fields,
    }, None

# ================================================================
# DEEP INTROSPECTION: RECURSIVE
# ================================================================
def deep_introspect(app_id, secret, type_name, visited=None, max_depth=3):
    """
    Introspecciona um tipo e todos seus sub-tipos (nao escalares)
    ate max_depth niveis. Retorna arvore completa.
    """
    if visited is None:
        visited = set()
    if type_name in visited or max_depth <= 0:
        return {"name": type_name, "fields": [], "note": "ja visitado ou max depth"}
    visited.add(type_name)

    info, err = get_type_fields(app_id, secret, type_name)
    if err or not info:
        return {"name": type_name, "fields": [], "error": err}

    result = {"name": type_name, "type_kind": info.get("type_kind"), "fields": []}

    for f in info["fields"]:
        field_data = {
            "name": f["name"],
            "type": f["type"],
            "kind": f["kind"],
            "is_list": f["is_list"],
            "is_scalar": f["is_scalar"],
        }
        # Se nao eh escalar, introspeccionar o sub-tipo
        if not f["is_scalar"] and f["type"] and f["type"] not in visited:
            sub = deep_introspect(app_id, secret, f["type"], visited, max_depth - 1)
            field_data["sub_fields"] = sub
        result["fields"].append(field_data)

    return result

# ================================================================
# QUERY BUILDER (com campos nested)
# ================================================================
def build_fields_string(tree, target_fields=None):
    """
    Constroi string de campos GraphQL a partir da arvore.
    Se target_fields fornecido, filtra apenas esses campos (recursivo).
    Se nao, inclui todos os campos escalares.
    """
    parts = []
    for f in tree.get("fields", []):
        if f.get("is_scalar"):
            parts.append(f["name"])
        elif "sub_fields" in f:
            sub_str = build_fields_string(f["sub_fields"])
            if sub_str:
                parts.append(f["name"] + "{" + sub_str + "}")
    return " ".join(parts)

def build_query(start_ts, end_ts, limit, node_fields_str,
                page_info_str=None, include_complete=True, token=None):
    args = ["purchaseTimeStart:" + str(start_ts),
            "purchaseTimeEnd:" + str(end_ts)]
    if include_complete:
        args.append("completeTimeStart:" + str(start_ts))
        args.append("completeTimeEnd:" + str(end_ts))
    args.append("limit:" + str(limit))
    if token:
        args.append('searchNextToken:"' + token + '"')

    inner = "nodes{" + node_fields_str + "}"
    if page_info_str:
        inner += " searchNextPageInfo{" + page_info_str + "}"

    return "{partnerOrderReport(" + ",".join(args) + "){" + inner + "}}"

# ================================================================
# FETCH ORDERS
# ================================================================
def fetch_orders(app_id, secret, start_ts, end_ts,
                 node_fields_str, page_info_str,
                 include_complete=True):
    all_nodes = []
    token = None
    page = 0
    last_query = ""

    while page < MAX_PAGES:
        q = build_query(start_ts, end_ts, PAGE_SIZE, node_fields_str,
                        page_info_str, include_complete, token)
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

        # Paginacao via searchNextPageInfo
        page_info = data.get("searchNextPageInfo", {})
        new_token = page_info.get("searchNextToken")
        has_next = page_info.get("hasNextPage", False)

        if has_next and new_token and str(new_token) != str(token):
            token = str(new_token)
        else:
            break

        page += 1

    return all_nodes, None, last_query

# ================================================================
# PROCESSAMENTO
# ================================================================
def _is_blacklisted(status):
    s = (status or "").lower()
    return any(bl in s for bl in BLACKLIST)

def extract_commission_from_order(order, commission_field_map):
    """
    Extrai comissao do pedido, buscando em items se necessario.
    commission_field_map indica onde encontrar cada campo.
    """
    # Tentar campos diretos primeiro
    net = _sf(order.get("netCommission"))
    est = _sf(order.get("estimatedTotalCommission"))
    status = order.get("conversionStatus") or order.get("orderStatus") or "-"

    # Se nao tem campos diretos, buscar em items
    if net == 0 and est == 0 and "items" in order:
        items = order.get("items", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    # Tentar varios nomes de campo de comissao
                    for key in ["netCommission", "commission", "commissionAmount",
                                "affiliateCommission", "net_commission"]:
                        v = _sf(item.get(key))
                        if v > 0:
                            net += v
                            break
                    for key in ["estimatedTotalCommission", "estimatedCommission",
                                "estimated_commission", "estimateCommission"]:
                        v = _sf(item.get(key))
                        if v > 0:
                            est += v
                            break
                    # Status do item
                    if status == "-":
                        for key in ["conversionStatus", "status", "orderStatus",
                                    "itemStatus", "conversion_status"]:
                            s = item.get(key)
                            if s:
                                status = str(s)
                                break

    # Tentar em extInfo
    if net == 0 and est == 0 and "extInfo" in order:
        ext = order.get("extInfo", {})
        if isinstance(ext, dict):
            net = _sf(ext.get("netCommission", 0))
            est = _sf(ext.get("estimatedTotalCommission", 0))
            if status == "-":
                status = ext.get("conversionStatus", status)

    if net > 0:
        return net, status, "Concluido"
    return est, status, "Pendente"

def process(raw):
    total_raw = len(raw)
    valid = []
    for o in raw:
        comm, status, ctype = extract_commission_from_order(o, {})

        if _is_blacklisted(status):
            continue

        valid.append({
            "ts": o.get("purchaseTime", 0),
            "status": status,
            "commission": comm,
            "type": ctype,
            "order_id": o.get("orderId", "-"),
        })
    return valid, total_raw

# ================================================================
# UI
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
    cls = status
    st.markdown(
        '<div class="disc"><b>' + label + ':</b> '
        + '<span class="' + cls + '">' + str(value) + "</span></div>",
        unsafe_allow_html=True,
    )

def render_tree(tree, indent=0):
    """Renderiza arvore de tipos como HTML"""
    lines = []
    prefix = "&nbsp;" * (indent * 4)
    for f in tree.get("fields", []):
        type_str = str(f.get("type", "?"))
        if f.get("is_list"):
            type_str = "[" + type_str + "]"

        if f.get("is_scalar"):
            lines.append(prefix + '<span class="field">' + f["name"]
                         + '</span> <span class="scalar">: ' + type_str + '</span>')
        else:
            lines.append(prefix + '<span class="field">' + f["name"]
                         + '</span> <span class="nested">: ' + type_str + '</span>')
            if "sub_fields" in f:
                lines.extend(render_tree_lines(f["sub_fields"], indent + 1))
    return lines

def render_tree_lines(tree, indent=0):
    lines = []
    prefix = "&nbsp;" * (indent * 4)
    for f in tree.get("fields", []):
        type_str = str(f.get("type", "?"))
        if f.get("is_list"):
            type_str = "[" + type_str + "]"
        if f.get("is_scalar"):
            lines.append(prefix + '<span class="field">' + f["name"]
                         + '</span> <span class="scalar"> : ' + type_str + '</span>')
        else:
            lines.append(prefix + '<span class="field">' + f["name"]
                         + '</span> <span class="nested"> : ' + type_str + '</span>')
            if "sub_fields" in f:
                lines.extend(render_tree_lines(f["sub_fields"], indent + 1))
    return lines

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
    st.caption("purchaseAmount e customParameters NAO sao solicitados.")

# ================================================================
# HEADER
# ================================================================
st.markdown('<div class="hdr">Shopee Affiliates</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hdr-sub">'
    "Dashboard de Comissoes - Deep Schema Discovery v3"
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
        '<div class="title">Selecione um periodo e clique Consultar</div>'
        '<div class="desc">Deep introspection: descobre TODA a estrutura do schema</div>'
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
# FASE 1: LISTAR TODOS OS ROOT QUERIES
# ================================================================
st.markdown("#### Fase 1: Root Queries disponiveis")

with st.spinner("Listando todos os root queries..."):
    all_queries, q_err = list_root_queries(app_id, secret)

if q_err:
    st.error("Erro: " + q_err)
else:
    show_disc("Total de queries", str(len(all_queries)))
    # Destacar queries relacionadas a order/commission
    order_related = [q for q in all_queries if any(
        kw in q.lower() for kw in ["order", "commission", "report", "affiliate", "partner"]
    )]
    other = [q for q in all_queries if q not in order_related]

    if order_related:
        show_disc("Queries relacionadas", ", ".join(order_related))
    if other:
        show_disc("Outras queries", ", ".join(other))

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 2: ARGUMENTOS DE partnerOrderReport
# ================================================================
st.markdown("#### Fase 2: Argumentos de partnerOrderReport")

with st.spinner("Introspectando argumentos..."):
    field_args, args_err = get_field_args(app_id, secret, "partnerOrderReport")

if args_err:
    st.error("Erro: " + args_err)
    field_args = []

required_args = [a for a in field_args if a.get("required")]
optional_args = [a for a in field_args if not a.get("required")]

if required_args:
    show_disc("Obrigatorios",
              ", ".join(a["name"] + ":" + str(a["type"]) for a in required_args))
if optional_args:
    show_disc("Opcionais",
              ", ".join(a["name"] + ":" + str(a["type"]) for a in optional_args),
              status="warn")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 3: DEEP INTROSPECTION - TODA A ARVORE
# ================================================================
st.markdown("#### Fase 3: Estrutura completa de PartnerOrder")

with st.spinner("Deep introspection de PartnerOrder e sub-tipos..."):
    node_tree = deep_introspect(app_id, secret, "PartnerOrder", max_depth=3)

# Renderizar arvore
tree_lines = render_tree_lines(node_tree)
if tree_lines:
    st.markdown(
        '<div class="tree">' + "<br>".join(tree_lines) + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.warning("Nao foi possivel introspeccionar PartnerOrder")

# Introspeccionar searchNextPageInfo
st.markdown("##### searchNextPageInfo")
with st.spinner("Introspectando searchNextPageInfo..."):
    page_info_tree = deep_introspect(app_id, secret, "SearchNextPageInfo", max_depth=1)
    if not page_info_tree.get("fields"):
        # Tentar outros nomes
        for name in ["PartnerOrderReportPageInfo", "PageInfo", "SearchPageInfo"]:
            page_info_tree = deep_introspect(app_id, secret, name, max_depth=1)
            if page_info_tree.get("fields"):
                break

pi_lines = render_tree_lines(page_info_tree)
if pi_lines:
    st.markdown(
        '<div class="tree">' + "<br>".join(pi_lines) + "</div>",
        unsafe_allow_html=True,
    )

# Descobrir campos do searchNextPageInfo
page_info_fields = [f["name"] for f in page_info_tree.get("fields", []) if f.get("is_scalar")]
page_info_str = " ".join(page_info_fields) if page_info_fields else "searchNextToken hasNextPage"
show_disc("Campos PageInfo", page_info_str)

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 4: CONSTRUIR QUERY COM CAMPOS COMPLETOS
# ================================================================
st.markdown("#### Fase 4: Construcao da Query")

# Construir string de campos do node automaticamente
node_fields_str = build_fields_string(node_tree)
show_disc("Campos auto-gerados", node_fields_str if node_fields_str else "VAZIO")

if not node_fields_str:
    # Fallback manual
    node_fields_str = "orderId purchaseTime orderStatus"
    show_disc("Usando fallback", node_fields_str, status="warn")

# Determinar se completeTime eh obrigatorio
required_names = [a["name"] for a in required_args]
include_complete = "completeTimeStart" in required_names

show_disc("Incluir completeTime", str(include_complete))

# Preview de 3 variantes da query
st.markdown("##### Variantes da query para testar:")

queries_to_try = []

# Variante 1: Todos os campos, com completeTime
q1 = build_query(start_ts, end_ts, 1, node_fields_str, page_info_str, True, None)
queries_to_try.append(("Completa (com completeTime)", q1, True))

# Variante 2: Todos os campos, SEM completeTime
q2 = build_query(start_ts, end_ts, 1, node_fields_str, page_info_str, False, None)
queries_to_try.append(("Sem completeTime", q2, False))

# Variante 3: Campos minimos
q3_fields = "orderId purchaseTime orderStatus"
q3 = build_query(start_ts, end_ts, 1, q3_fields, page_info_str, True, None)
queries_to_try.append(("Campos minimos", q3, True))

for label, q, _ in queries_to_try:
    with st.expander("Query: " + label):
        st.code(q, language="graphql")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 5: TENTAR CADA VARIANTE
# ================================================================
st.markdown("#### Fase 5: Testando queries")

success_query = None
success_result = None
success_include_complete = True
success_fields_str = node_fields_str
all_errors = []

for label, q, inc_complete in queries_to_try:
    with st.spinner("Testando: " + label + "..."):
        try:
            result = _sign_and_call(app_id, secret, q)
        except Exception as exc:
            all_errors.append(label + ": " + str(exc))
            show_disc(label, "ERRO: " + str(exc), status="err")
            continue

        if "errors" in result:
            msg = result["errors"][0].get("message", str(result["errors"]))
            all_errors.append(label + ": " + msg)
            show_disc(label, msg, status="err")
        else:
            show_disc(label, "SUCESSO!", status="ok")
            success_query = q
            success_result = result
            success_include_complete = inc_complete
            if "minimos" in label:
                success_fields_str = "orderId purchaseTime orderStatus"
            break

# Tentar tambem CADA root query alternativa se tudo falhou
if not success_result and all_queries:
    st.markdown("##### Tentando queries alternativas...")
    for rq in all_queries:
        if rq == "partnerOrderReport":
            continue
        # Tentar uma query simples
        test_q = "{" + rq + "{__typename}}"
        with st.spinner("Testando " + rq + "..."):
            try:
                r = _sign_and_call(app_id, secret, test_q)
                if "errors" not in r:
                    show_disc(rq, "Acessivel!", status="ok")
                else:
                    msg = r["errors"][0].get("message", "")[:80]
                    show_disc(rq, msg, status="warn")
            except Exception:
                show_disc(rq, "erro", status="err")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 6: BUSCAR DADOS (se alguma query funcionou)
# ================================================================
if not success_result:
    st.error("Nenhuma query funcionou. Erros encontrados:")
    for e in all_errors:
        st.code(e)

    st.markdown("---")
    st.markdown("### Proximos passos")
    st.markdown("""
**O erro `[10031]: access deny` significa que seu App nao tem permissao para `partnerOrderReport`.**

**Para resolver:**

1. Acesse [Shopee Open Platform](https://open.shopee.com.br/)
2. Va em **App Management** > seu app
3. Procure por permissoes como:
   - **Partner Order Report**
   - **Affiliate Order Report**
   - **Order Data Access**
4. Ative a permissao necessaria
5. Aguarde aprovacao (pode levar ate 24h)

**Queries disponiveis no seu schema:**
""")
    for q in all_queries:
        st.code(q)

    with st.expander("Schema completo descoberto"):
        st.json({
            "root_queries": all_queries,
            "partnerOrderReport_args": field_args,
            "required_args": [a["name"] for a in required_args],
            "optional_args": [a["name"] for a in optional_args],
            "node_type": "PartnerOrder",
            "node_tree": json.loads(json.dumps(node_tree, default=str)),
            "page_info_fields": page_info_fields,
            "queries_tried": [{"label": l, "query": q} for l, q, _ in queries_to_try],
            "errors": all_errors,
        })
    st.stop()

# Se chegou aqui, temos dados!
st.markdown("#### Fase 6: Buscando todos os pedidos")

with st.spinner("Buscando pedidos com paginacao..."):
    raw_orders, fetch_err, last_q = fetch_orders(
        app_id, secret, start_ts, end_ts,
        success_fields_str, page_info_str,
        success_include_complete
    )

if fetch_err:
    st.error(fetch_err)
    with st.expander("Debug"):
        st.code("Ultima query:\n" + last_q, language="graphql")
    st.stop()

# ================================================================
# FASE 7: PROCESSAR E EXIBIR
# ================================================================
valid_orders, total_raw = process(raw_orders)
total_valid = len(valid_orders)
total_comm = sum(o["commission"] for o in valid_orders)
conv_rate = (total_valid / total_raw * 100) if total_raw > 0 else 0.0

# Mostrar amostra dos dados brutos
if raw_orders:
    with st.expander("Amostra dados brutos (" + str(len(raw_orders)) + " pedidos)"):
        st.json(raw_orders[:3])

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
             str(q_done) + " pedido(s)", css="green")
    with b2:
        card("COMISSAO PENDENTE", brl(c_pend),
             str(q_pend) + " pedido(s)", css="yellow")

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
    df["Pedido"] = df["order_id"]
    df["Status"] = df["status"]
    df["Tipo"] = df["type"]
    df["Comissao"] = df["commission"].apply(brl)
    display = (
        df[["Data/Hora", "Pedido", "Status", "Tipo", "Comissao"]]
        .sort_values("Data/Hora", ascending=False)
        .reset_index(drop=True)
    )
    st.dataframe(display, use_container_width=True, hide_index=True,
                 height=min(520, 36 * len(display) + 40))
else:
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.info("Nenhum pedido valido: "
            + start_date.strftime("%d/%m/%Y") + " - "
            + end_date.strftime("%d/%m/%Y"))

# RODAPE DEBUG COMPLETO
with st.expander("Debug completo"):
    st.json({
        "endpoint": ENDPOINT,
        "root_queries_available": all_queries,
        "field_args": field_args,
        "required_args": [a["name"] for a in required_args],
        "node_fields_auto": node_fields_str,
        "page_info_fields": page_info_str,
        "include_complete_time": success_include_complete,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "total_raw": total_raw,
        "total_valid": total_valid,
        "last_query": last_q if last_q else str(queries_to_try[0][1] if queries_to_try else ""),
        "schema_tree": json.loads(json.dumps(node_tree, default=str)),
    })
