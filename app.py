"""
Shopee Affiliates Dashboard - API v2 GraphQL
Usa conversionReport (descoberto via deep schema discovery)
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
.tree{font-family:monospace;font-size:12px;line-height:1.8;color:#888;
    background:#0a0a0a;border:1px solid #1a1a1a;border-radius:10px;padding:16px}
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
# INTROSPECTION
# ================================================================
def _resolve_base(t):
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

def get_field_detail(app_id, secret, field_name):
    """Pega args + return type de um campo do Query type."""
    q = (
        '{__type(name:"Query"){fields{name'
        ' args{name type{kind name ofType{kind name ofType{kind name ofType{kind name}}}}}'
        ' type{name kind ofType{name kind ofType{name kind ofType{name kind}}}}'
        '}}}'
    )
    try:
        r = _sign_and_call(app_id, secret, q)
    except Exception as e:
        return None, str(e)
    if "errors" in r:
        return None, r["errors"][0].get("message", "")

    for f in r.get("data", {}).get("__type", {}).get("fields", []):
        if f.get("name") == field_name:
            args = []
            for a in f.get("args", []):
                t = a.get("type", {})
                required = t.get("kind") == "NON_NULL"
                bname, bkind, _ = _resolve_base(t)
                args.append({"name": a["name"], "type": bname, "required": required})

            ret_name, ret_kind, ret_list = _resolve_base(f.get("type"))
            return {
                "args": args,
                "return_type": ret_name,
                "return_kind": ret_kind,
                "return_is_list": ret_list,
            }, None
    return None, field_name + " nao encontrado"

def get_type_fields_deep(app_id, secret, type_name, visited=None, depth=3):
    """Introspecciona tipo recursivamente."""
    if visited is None:
        visited = set()
    if type_name in visited or depth <= 0 or not type_name:
        return {"name": type_name, "fields": []}
    visited.add(type_name)

    q = (
        '{__type(name:"' + type_name + '"){name kind'
        ' fields{name type{name kind ofType{name kind ofType{name kind ofType{name kind}}}}}'
        '}}'
    )
    try:
        r = _sign_and_call(app_id, secret, q)
    except Exception:
        return {"name": type_name, "fields": []}
    if "errors" in r:
        return {"name": type_name, "fields": []}

    td = r.get("data", {}).get("__type")
    if not td:
        return {"name": type_name, "fields": []}

    result = {"name": type_name, "type_kind": td.get("kind"), "fields": []}

    for f in td.get("fields", []):
        bname, bkind, is_list = _resolve_base(f.get("type"))
        fd = {
            "name": f["name"],
            "type": bname,
            "kind": bkind,
            "is_list": is_list,
            "is_scalar": bkind in ("SCALAR", "ENUM"),
        }
        if not fd["is_scalar"] and bname and bname not in visited:
            fd["sub"] = get_type_fields_deep(app_id, secret, bname, visited, depth - 1)
        result["fields"].append(fd)

    return result

# ================================================================
# BUILD QUERY STRING FROM TREE
# ================================================================
def fields_from_tree(tree):
    """Constroi string de campos GraphQL a partir da arvore."""
    parts = []
    for f in tree.get("fields", []):
        if f.get("is_scalar"):
            parts.append(f["name"])
        elif "sub" in f and f["sub"].get("fields"):
            sub_str = fields_from_tree(f["sub"])
            if sub_str:
                parts.append(f["name"] + "{" + sub_str + "}")
    return " ".join(parts)

def tree_to_lines(tree, indent=0):
    """Renderiza arvore como linhas HTML."""
    lines = []
    prefix = "&nbsp;" * (indent * 4)
    for f in tree.get("fields", []):
        ts = str(f.get("type", "?"))
        if f.get("is_list"):
            ts = "[" + ts + "]"
        if f.get("is_scalar"):
            lines.append(prefix + '<span class="field">' + f["name"]
                         + '</span><span class="scalar"> : ' + ts + '</span>')
        else:
            lines.append(prefix + '<span class="field">' + f["name"]
                         + '</span><span class="nested"> : ' + ts + '</span>')
            if "sub" in f:
                lines.extend(tree_to_lines(f["sub"], indent + 1))
    return lines

# ================================================================
# CLASSIFY ARGS + BUILD QUERY
# ================================================================
def classify_arg(name):
    low = name.lower().replace("_", "")
    if any(k in low for k in ["start", "begin", "from", "since"]):
        if any(k in low for k in ["time", "date", "purchase", "created"]):
            return "start"
    if any(k in low for k in ["end", "finish", "to", "until"]):
        if any(k in low for k in ["time", "date", "purchase", "created"]):
            return "end"
    if low in ("limit", "pagesize", "size", "count", "first", "top"):
        return "limit"
    if any(k in low for k in ["scroll", "cursor", "token", "offset", "page", "after"]):
        return "cursor"
    return "unknown"

def build_dynamic_query(root_field, args_info, start_ts, end_ts,
                        limit, fields_str, page_info_str=None, token=None):
    """Constroi query dinamicamente baseado nos args descobertos."""
    arg_parts = []

    for a in args_info:
        cls = classify_arg(a["name"])
        if cls == "start":
            arg_parts.append(a["name"] + ":" + str(start_ts))
        elif cls == "end":
            arg_parts.append(a["name"] + ":" + str(end_ts))
        elif cls == "limit":
            arg_parts.append(a["name"] + ":" + str(limit))
        elif cls == "cursor":
            if token:
                # Verificar se eh tipo String
                if a.get("type") in ("String", "ID"):
                    arg_parts.append(a["name"] + ':"' + str(token) + '"')
                else:
                    arg_parts.append(a["name"] + ":" + str(token))
            # Se nao tem token, OMITIR (nao mandar vazio)

    args_str = ",".join(arg_parts)

    # Montar body
    body = "{" + fields_str + "}"

    # Se temos page info, incluir
    if page_info_str:
        body = "{nodes{" + fields_str + "} " + page_info_str + "}"
    else:
        # Tentar formato simples
        body = "{" + fields_str + "}"

    q = "{" + root_field
    if args_str:
        q += "(" + args_str + ")"
    q += body + "}"
    return q

# ================================================================
# FETCH WITH PAGINATION
# ================================================================
def fetch_data(app_id, secret, root_field, args_info, start_ts, end_ts,
               node_fields_str, return_structure):
    """
    Busca dados com paginacao automatica.
    return_structure indica como os dados estao organizados.
    """
    all_nodes = []
    token = None
    page = 0
    last_q = ""

    # Descobrir estrutura de paginacao
    has_connection = return_structure.get("has_connection", False)
    list_field = return_structure.get("list_field")
    page_info_field = return_structure.get("page_info_field")
    page_info_fields_str = return_structure.get("page_info_fields_str", "")
    token_field = return_structure.get("token_field", "searchNextToken")
    has_next_field = return_structure.get("has_next_field")

    while page < MAX_PAGES:
        if has_connection:
            # Formato Connection: {rootField(...){nodes{...} pageInfo{...}}}
            inner = ""
            if list_field:
                inner += list_field + "{" + node_fields_str + "}"
            else:
                inner += node_fields_str

            if page_info_field and page_info_fields_str:
                inner += " " + page_info_field + "{" + page_info_fields_str + "}"

            arg_parts = []
            for a in args_info:
                cls = classify_arg(a["name"])
                if cls == "start":
                    arg_parts.append(a["name"] + ":" + str(start_ts))
                elif cls == "end":
                    arg_parts.append(a["name"] + ":" + str(end_ts))
                elif cls == "limit":
                    arg_parts.append(a["name"] + ":" + str(PAGE_SIZE))
                elif cls == "cursor" and token:
                    if a.get("type") in ("String", "ID"):
                        arg_parts.append(a["name"] + ':"' + str(token) + '"')
                    else:
                        arg_parts.append(a["name"] + ":" + str(token))

            q = "{" + root_field
            if arg_parts:
                q += "(" + ",".join(arg_parts) + ")"
            q += "{" + inner + "}}"

        else:
            # Formato simples: {rootField(...){field1 field2 ...}}
            arg_parts = []
            for a in args_info:
                cls = classify_arg(a["name"])
                if cls == "start":
                    arg_parts.append(a["name"] + ":" + str(start_ts))
                elif cls == "end":
                    arg_parts.append(a["name"] + ":" + str(end_ts))
                elif cls == "limit":
                    arg_parts.append(a["name"] + ":" + str(PAGE_SIZE))
                elif cls == "cursor" and token:
                    if a.get("type") in ("String", "ID"):
                        arg_parts.append(a["name"] + ':"' + str(token) + '"')
                    else:
                        arg_parts.append(a["name"] + ":" + str(token))

            q = "{" + root_field
            if arg_parts:
                q += "(" + ",".join(arg_parts) + ")"
            q += "{" + node_fields_str + "}}"

        last_q = q

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

        data = result.get("data", {}).get(root_field, {})

        # Extrair nodes
        nodes = []
        if has_connection and list_field and list_field in data:
            nodes = data[list_field]
            if not isinstance(nodes, list):
                nodes = []
        elif isinstance(data, list):
            nodes = data
        elif isinstance(data, dict):
            # Procurar lista nos valores
            for k, v in data.items():
                if isinstance(v, list):
                    nodes = v
                    break
            if not nodes:
                # O proprio data eh um unico resultado
                nodes = [data]

        all_nodes.extend(nodes)

        if not nodes:
            break

        # Paginacao
        if has_connection and page_info_field:
            pi = data.get(page_info_field, {})
            if isinstance(pi, dict):
                new_tok = pi.get(token_field)
                has_next = pi.get(has_next_field, False) if has_next_field else bool(new_tok)
                if has_next and new_tok and str(new_tok) != str(token):
                    token = str(new_tok)
                else:
                    break
            else:
                break
        else:
            # Sem paginacao em formato simples
            break

        page += 1

    return all_nodes, None, last_q

# ================================================================
# PROCESSAMENTO
# ================================================================
def _is_blacklisted(status):
    s = (status or "").lower()
    return any(bl in s for bl in BLACKLIST)

def extract_commission(order):
    """
    Extrai comissao de qualquer formato de pedido.
    Busca em campos diretos, items, extInfo, etc.
    """
    # Campos comuns de comissao
    comm_keys = ["netCommission", "commission", "commissionAmount",
                 "affiliateCommission", "estimatedCommission", "amount",
                 "netAmount", "payout", "earning", "earnings"]
    est_keys = ["estimatedTotalCommission", "estimatedCommission",
                "pendingCommission", "estimatedAmount"]
    status_keys = ["conversionStatus", "orderStatus", "status",
                   "displayStatus", "itemStatus"]

    net = 0.0
    est = 0.0
    status = "-"

    # Busca direta no order
    for k in comm_keys:
        v = _sf(order.get(k))
        if v > 0:
            net = v
            break

    for k in est_keys:
        v = _sf(order.get(k))
        if v > 0:
            est = v
            break

    for k in status_keys:
        v = order.get(k)
        if v and str(v) != "-":
            status = str(v)
            break

    # Buscar em sub-objetos
    if net == 0 and est == 0:
        # Tentar em items
        items = order.get("items", [])
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                for k in comm_keys:
                    v = _sf(item.get(k))
                    if v > 0:
                        net += v
                        break
                for k in est_keys:
                    v = _sf(item.get(k))
                    if v > 0:
                        est += v
                        break
                if status == "-":
                    for k in status_keys:
                        v = item.get(k)
                        if v:
                            status = str(v)
                            break

        # Tentar em extInfo
        ext = order.get("extInfo")
        if isinstance(ext, dict):
            for k in comm_keys:
                v = _sf(ext.get(k))
                if v > 0:
                    net += v
                    break
            for k in est_keys:
                v = _sf(ext.get(k))
                if v > 0:
                    est += v
                    break
            if status == "-":
                for k in status_keys:
                    v = ext.get(k)
                    if v:
                        status = str(v)
                        break

    # Tentar actualAmount dos items como fallback
    if net == 0 and est == 0:
        items = order.get("items", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    aa = _sf(item.get("actualAmount"))
                    if aa > 0:
                        est += aa

    if net > 0:
        return net, status, "Concluido"
    if est > 0:
        return est, status, "Pendente"
    return 0.0, status, "Pendente"

def process(raw):
    total_raw = len(raw)
    valid = []
    for o in raw:
        comm, status, ctype = extract_commission(o)
        if _is_blacklisted(status):
            continue
        # Extrair timestamp
        ts = 0
        for k in ["purchaseTime", "createdTime", "createTime", "timestamp",
                   "time", "date", "created_at", "purchase_time"]:
            v = o.get(k)
            if v and (isinstance(v, (int, float)) and v > 1000000000):
                ts = int(v)
                break

        valid.append({
            "ts": ts,
            "status": status,
            "commission": comm,
            "type": ctype,
            "raw": o,
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
    st.markdown(
        '<div class="disc"><b>' + label + ':</b> '
        + '<span class="' + status + '">' + str(value) + "</span></div>",
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
    st.caption("Usa conversionReport (acessivel) em vez de partnerOrderReport (bloqueado)")

# ================================================================
# HEADER
# ================================================================
st.markdown('<div class="hdr">Shopee Affiliates</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hdr-sub">'
    "Dashboard de Comissoes - conversionReport + Auto-Discovery"
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

if not go:
    st.markdown(
        '<div class="empty-state">'
        '<div class="title">Selecione um periodo e clique Consultar</div>'
        '<div class="desc">Usa conversionReport para dados de comissao</div>'
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
# FASE 1: INTROSPECT conversionReport
# ================================================================
st.markdown("#### Fase 1: Estrutura de conversionReport")

with st.spinner("Introspectando conversionReport..."):
    cr_detail, cr_err = get_field_detail(app_id, secret, "conversionReport")

if cr_err:
    st.error("Erro: " + cr_err)
    st.stop()

cr_args = cr_detail.get("args", [])
cr_return_type = cr_detail.get("return_type")
cr_return_kind = cr_detail.get("return_kind")
cr_return_list = cr_detail.get("return_is_list", False)

show_disc("Return type", str(cr_return_type) + " (" + str(cr_return_kind) + ")"
          + (" [LIST]" if cr_return_list else ""))

required = [a for a in cr_args if a.get("required")]
optional = [a for a in cr_args if not a.get("required")]

if required:
    show_disc("Args obrigatorios",
              ", ".join(a["name"] + ":" + str(a["type"]) for a in required))
if optional:
    show_disc("Args opcionais",
              ", ".join(a["name"] + ":" + str(a["type"]) for a in optional))

# Mapeamento de args
mapped = []
unmapped = []
for a in cr_args:
    cls = classify_arg(a["name"])
    if cls != "unknown":
        mapped.append(a["name"] + " -> " + cls)
    else:
        unmapped.append(a["name"] + " (" + str(a["type"]) + ")")

show_disc("Args mapeados", ", ".join(mapped) if mapped else "nenhum")
if unmapped:
    show_disc("Args nao mapeados", ", ".join(unmapped), status="warn")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 2: DEEP INTROSPECT DO RETURN TYPE
# ================================================================
st.markdown("#### Fase 2: Estrutura de " + str(cr_return_type))

with st.spinner("Deep introspection de " + str(cr_return_type) + "..."):
    ret_tree = get_type_fields_deep(app_id, secret, cr_return_type, max_depth=3)

tree_lines = tree_to_lines(ret_tree)
if tree_lines:
    st.markdown(
        '<div class="tree">' + "<br>".join(tree_lines) + "</div>",
        unsafe_allow_html=True,
    )

# Analisar estrutura
ret_fields = ret_tree.get("fields", [])
ret_field_names = [f["name"] for f in ret_fields]

# Descobrir se eh Connection type (tem nodes + pageInfo)
has_nodes = "nodes" in ret_field_names
has_connection = has_nodes

# Encontrar campos de paginacao
page_info_candidates = [f for f in ret_fields
                        if any(k in f["name"].lower() for k in ["page", "scroll", "next", "cursor"])]
page_info_field = None
page_info_fields_str = ""
token_field_name = None
has_next_field_name = None

if page_info_candidates:
    pf = page_info_candidates[0]
    page_info_field = pf["name"]
    if "sub" in pf and pf["sub"].get("fields"):
        pi_fields = pf["sub"]["fields"]
        pi_scalar_names = [f["name"] for f in pi_fields if f.get("is_scalar")]
        page_info_fields_str = " ".join(pi_scalar_names)
        for f in pi_fields:
            n = f["name"].lower()
            if "token" in n or "cursor" in n:
                token_field_name = f["name"]
            if "hasnext" in n or "has_next" in n or "hasmore" in n:
                has_next_field_name = f["name"]

# Descobrir o tipo do node (se connection)
node_tree = None
node_fields_str = ""
if has_nodes:
    for f in ret_fields:
        if f["name"] == "nodes" and "sub" in f:
            node_tree = f["sub"]
            break

    if node_tree:
        node_fields_str = fields_from_tree(node_tree)
    else:
        # Introspeccionar tipo do node manualmente
        for f in ret_fields:
            if f["name"] == "nodes" and f.get("type"):
                with st.spinner("Introspectando " + f["type"] + "..."):
                    node_tree = get_type_fields_deep(app_id, secret, f["type"], max_depth=2)
                    node_fields_str = fields_from_tree(node_tree)
                break
else:
    # Nao eh connection, usar campos diretos
    node_fields_str = fields_from_tree(ret_tree)

show_disc("Formato", "Connection" if has_connection else "Direto")
show_disc("Node fields", node_fields_str if node_fields_str else "VAZIO")
if page_info_field:
    show_disc("Page info", page_info_field + "{" + page_info_fields_str + "}")
if token_field_name:
    show_disc("Token field", token_field_name)

# Se node_fields vazio, tentar ALL scalar fields
if not node_fields_str:
    if has_connection and node_tree:
        scalars = [f["name"] for f in node_tree.get("fields", []) if f.get("is_scalar")]
        node_fields_str = " ".join(scalars)
    else:
        scalars = [f["name"] for f in ret_fields if f.get("is_scalar")]
        node_fields_str = " ".join(scalars)

    if node_fields_str:
        show_disc("Fallback campos", node_fields_str, status="warn")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 3: TESTAR QUERY
# ================================================================
st.markdown("#### Fase 3: Testando query")

return_structure = {
    "has_connection": has_connection,
    "list_field": "nodes" if has_connection else None,
    "page_info_field": page_info_field,
    "page_info_fields_str": page_info_fields_str,
    "token_field": token_field_name or "searchNextToken",
    "has_next_field": has_next_field_name,
}

# Montar query de teste (limit=2)
test_args = []
for a in cr_args:
    cls = classify_arg(a["name"])
    if cls == "start":
        test_args.append(a["name"] + ":" + str(start_ts))
    elif cls == "end":
        test_args.append(a["name"] + ":" + str(end_ts))
    elif cls == "limit":
        test_args.append(a["name"] + ":2")

if has_connection:
    test_inner = "nodes{" + node_fields_str + "}"
    if page_info_field and page_info_fields_str:
        test_inner += " " + page_info_field + "{" + page_info_fields_str + "}"
    test_q = "{conversionReport(" + ",".join(test_args) + "){" + test_inner + "}}"
else:
    test_q = "{conversionReport(" + ",".join(test_args) + "){" + node_fields_str + "}}"

with st.expander("Query de teste"):
    st.code(test_q, language="graphql")

with st.spinner("Testando query..."):
    try:
        test_result = _sign_and_call(app_id, secret, test_q)
    except Exception as exc:
        st.error("Erro: " + str(exc))
        st.stop()

if "errors" in test_result:
    msg = test_result["errors"][0].get("message", str(test_result["errors"]))
    st.error("Erro na query de teste: " + msg)

    # Tentar variantes
    st.markdown("##### Tentando variantes...")

    # Variante: sem args de tempo (talvez nao use timestamps)
    test_q2 = "{conversionReport{" + (("nodes{" + node_fields_str + "}") if has_connection else node_fields_str) + "}}"
    with st.spinner("Sem args..."):
        try:
            r2 = _sign_and_call(app_id, secret, test_q2)
            if "errors" not in r2:
                show_disc("Sem args", "SUCESSO!", status="ok")
                test_result = r2
                cr_args = []  # Nao precisa args
            else:
                show_disc("Sem args", r2["errors"][0].get("message", "")[:80], status="err")
        except Exception as e2:
            show_disc("Sem args", str(e2)[:80], status="err")

    # Variante: apenas __typename
    test_q3 = "{conversionReport{__typename}}"
    with st.spinner("Apenas __typename..."):
        try:
            r3 = _sign_and_call(app_id, secret, test_q3)
            if "errors" not in r3:
                show_disc("__typename", str(r3.get("data", {})), status="ok")
            else:
                show_disc("__typename", r3["errors"][0].get("message", "")[:80], status="err")
        except Exception as e3:
            show_disc("__typename", str(e3)[:80], status="err")

    if "errors" in test_result:
        with st.expander("Debug completo"):
            st.json({
                "cr_args": cr_args,
                "cr_return_type": cr_return_type,
                "node_fields_str": node_fields_str,
                "return_structure": return_structure,
                "test_query": test_q,
                "test_result": test_result,
                "tree": json.loads(json.dumps(ret_tree, default=str)),
            })
        st.stop()

show_disc("Teste", "SUCESSO!", status="ok")

# Mostrar amostra
with st.expander("Resposta do teste"):
    st.json(test_result)

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 4: BUSCAR TODOS OS DADOS
# ================================================================
st.markdown("#### Fase 4: Buscando todos os dados")

with st.spinner("Buscando dados com paginacao..."):
    raw_data, fetch_err, last_q = fetch_data(
        app_id, secret, "conversionReport", cr_args,
        start_ts, end_ts, node_fields_str, return_structure
    )

if fetch_err:
    st.error(fetch_err)
    with st.expander("Debug"):
        st.code("Ultima query:\n" + last_q, language="graphql")
    st.stop()

show_disc("Registros obtidos", str(len(raw_data)))

if raw_data:
    with st.expander("Amostra dados brutos (" + str(min(3, len(raw_data))) + " registros)"):
        st.json(raw_data[:3])

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 5: PROCESSAR E EXIBIR
# ================================================================
valid_orders, total_raw = process(raw_data)
total_valid = len(valid_orders)
total_comm = sum(o["commission"] for o in valid_orders)
conv_rate = (total_valid / total_raw * 100) if total_raw > 0 else 0.0

# 4 METRICAS
k1, k2, k3, k4 = st.columns(4, gap="medium")
with k1:
    card("VENDAS TOTAIS", "--",
         "purchaseAmount restrito", css="muted")
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
    df["Status"] = df["status"]
    df["Tipo"] = df["type"]
    df["Comissao"] = df["commission"].apply(brl)

    cols = ["Data/Hora", "Status", "Tipo", "Comissao"]
    display = (
        df[cols]
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

# RODAPE
with st.expander("Debug completo"):
    st.json({
        "endpoint": ENDPOINT,
        "root_field": "conversionReport",
        "args": cr_args,
        "return_type": cr_return_type,
        "return_structure": return_structure,
        "node_fields": node_fields_str,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "total_raw": total_raw,
        "total_valid": total_valid,
        "last_query": last_q,
        "tree": json.loads(json.dumps(ret_tree, default=str)),
    })
