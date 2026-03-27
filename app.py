"""
Shopee Affiliates Dashboard - API v2 GraphQL
Deep auto-discovery: root field, arguments, return type, nested fields
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

ORDER_FIELDS = [
    "purchaseTime",
    "conversionStatus",
    "netCommission",
    "estimatedTotalCommission",
]

NODE_KEYS = ["nodes", "orders", "items", "edges", "list", "data"]
SCROLL_KEYS = ["scrollId", "scroll_id", "cursor", "after",
               "nextCursor", "endCursor"]
MORE_KEYS = ["more", "hasMore", "hasNextPage", "has_more"]

# ================================================================
# CSS  - DARK MODE
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
# API CORE — ASSINATURA SHA256 + CHAMADA
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
# INTROSPECTION — RESOLUCAO DE TIPOS
# ================================================================
def _resolve_type(t):
    """Desembrulha NON_NULL e LIST ate o tipo base."""
    if not t:
        return None, None
    if t.get("kind") in ("NON_NULL", "LIST"):
        return _resolve_type(t.get("ofType"))
    return t.get("name"), t.get("kind")


def _is_required(t):
    """Verifica se o tipo eh NON_NULL (obrigatorio)."""
    if not t:
        return False
    return t.get("kind") == "NON_NULL"


# ================================================================
# INTROSPECTION — FASE 1: ROOT FIELDS
# ================================================================
def introspect_root_fields(app_id, secret):
    q = "{__schema{queryType{fields{name}}}}"
    try:
        result = _sign_and_call(app_id, secret, q)
    except Exception as exc:
        return [], str(exc)
    if "errors" in result:
        return [], result["errors"][0].get("message", "")
    fields = (
        result.get("data", {})
        .get("__schema", {})
        .get("queryType", {})
        .get("fields", [])
    )
    return [f["name"] for f in fields if isinstance(f, dict)], None


def find_order_field(names):
    priority = [
        "partnerOrderReport",
        "orderList",
        "affiliateOrderList",
        "getOrderList",
        "orderListV2",
        "orders",
        "affiliateOrders",
    ]
    lower_map = {n.lower(): n for n in names}
    for p in priority:
        if p.lower() in lower_map:
            return lower_map[p.lower()]
    for low, orig in lower_map.items():
        if "order" in low:
            return orig
    return None


# ================================================================
# INTROSPECTION — FASE 2: ARGUMENTOS + TIPO DE RETORNO
# ================================================================
def introspect_field_deep(app_id, secret, field_name):
    """
    Retorna:
      args: lista de {name, type_name, type_kind, required, raw_type}
      return_type_name: str
      error: str ou None
    """
    q = (
        '{__type(name:"Query"){fields{name'
        " args{name type{name kind ofType{name kind ofType{name kind}}}}"
        " type{name kind ofType{name kind}}"
        "}}}"
    )
    try:
        result = _sign_and_call(app_id, secret, q)
    except Exception as exc:
        return [], None, str(exc)

    if "errors" in result:
        return [], None, result["errors"][0].get("message", "")

    all_fields = (
        result.get("data", {}).get("__type", {}).get("fields", [])
    )
    target = None
    for f in all_fields:
        if f.get("name") == field_name:
            target = f
            break

    if not target:
        return [], None, "Campo " + field_name + " nao encontrado"

    args = []
    for a in target.get("args", []):
        tname, tkind = _resolve_type(a.get("type"))
        args.append({
            "name": a["name"],
            "type_name": tname,
            "type_kind": tkind,
            "required": _is_required(a.get("type")),
            "raw_type": a.get("type", {}),
        })

    ret_name, _ = _resolve_type(target.get("type"))
    return args, ret_name, None


# ================================================================
# INTROSPECTION — FASE 3: CAMPOS DE UM TIPO
# ================================================================
def introspect_type(app_id, secret, type_name):
    q = (
        '{__type(name:"' + type_name + '")'
        "{name kind"
        " fields{name type{name kind ofType{name kind}"
        " fields{name type{name kind ofType{name kind}}}}}"
        " inputFields{name type{name kind"
        " ofType{name kind ofType{name kind}}}}"
        "}}"
    )
    try:
        result = _sign_and_call(app_id, secret, q)
    except Exception as exc:
        return None, str(exc)
    if "errors" in result:
        return None, result["errors"][0].get("message", "")
    return result.get("data", {}).get("__type"), None


# ================================================================
# MAPEAMENTO DE ARGUMENTOS
# ================================================================
def _classify_arg(name):
    low = name.lower().replace("_", "")

    start_kw = {
        "starttime", "startdate", "purchasetimestart",
        "startpurchasetime", "fromtime", "timestart",
        "beginttime", "since", "startcreatedtime",
    }
    end_kw = {
        "endtime", "enddate", "purchasetimeend",
        "endpurchasetime", "totime", "timeend",
        "until", "endcreatedtime",
    }
    limit_kw = {
        "limit", "pagesize", "size", "count",
        "first", "perpage", "top",
    }
    cursor_kw = {
        "scrollid", "cursor", "after", "offset",
        "page", "nextcursor", "endcursor", "pageno",
    }

    if low in start_kw:
        return "start"
    if low in end_kw:
        return "end"
    if low in limit_kw:
        return "limit"
    if low in cursor_kw:
        return "cursor"

    if ("start" in low or "begin" in low or "from" in low) and (
        "time" in low or "date" in low or "purchase" in low
    ):
        return "start"
    if ("end" in low or "finish" in low or "to" in low) and (
        "time" in low or "date" in low or "purchase" in low
    ):
        return "end"

    return "unknown"


def _is_string_type(type_name):
    if not type_name:
        return False
    return type_name.lower() in ("string", "str", "id")


def map_args_flat(args, start_ts, end_ts, page_size, scroll_id):
    """
    Mapeia argumentos escalares.
    Retorna: (lista_mapeada, lista_nao_mapeados, lista_input_objects)
    Cada item mapeado: {name, value, is_string, classification, is_scroll}
    """
    mapped = []
    unknown = []
    input_objects = []

    for arg in args:
        name = arg["name"]
        tkind = arg.get("type_kind", "")
        tname = arg.get("type_name", "")

        if tkind == "INPUT_OBJECT":
            input_objects.append(arg)
            continue

        cls = _classify_arg(name)
        is_str = _is_string_type(tname)

        if cls == "start":
            mapped.append({"name": name, "value": start_ts,
                           "is_string": is_str, "cls": cls, "is_scroll": False})
        elif cls == "end":
            mapped.append({"name": name, "value": end_ts,
                           "is_string": is_str, "cls": cls, "is_scroll": False})
        elif cls == "limit":
            mapped.append({"name": name, "value": page_size,
                           "is_string": False, "cls": cls, "is_scroll": False})
        elif cls == "cursor":
            mapped.append({"name": name, "value": scroll_id,
                           "is_string": is_str, "cls": cls, "is_scroll": True})
        else:
            unknown.append(arg)

    return mapped, unknown, input_objects


def map_input_object(app_id, secret, arg, start_ts, end_ts, page_size, scroll_id):
    """
    Introspects an INPUT_OBJECT argument and maps its sub-fields.
    Retorna: {name, inner_fields: [{name, value, is_string, is_scroll}], error}
    """
    tname = arg.get("type_name", "")
    if not tname:
        return None, "Tipo desconhecido para " + arg["name"]

    type_info, err = introspect_type(app_id, secret, tname)
    if err or not type_info:
        return None, "Erro ao introspeccionar " + tname + ": " + str(err)

    input_fields = type_info.get("inputFields", [])
    if not input_fields:
        return None, tname + " nao tem inputFields"

    inner = []
    inner_unknown = []
    for ifield in input_fields:
        iname = ifield["name"]
        itype_name, _ = _resolve_type(ifield.get("type"))
        icls = _classify_arg(iname)
        is_str = _is_string_type(itype_name)
        is_req = _is_required(ifield.get("type"))

        if icls == "start":
            inner.append({"name": iname, "value": start_ts,
                          "is_string": is_str, "is_scroll": False})
        elif icls == "end":
            inner.append({"name": iname, "value": end_ts,
                          "is_string": is_str, "is_scroll": False})
        elif icls == "limit":
            inner.append({"name": iname, "value": page_size,
                          "is_string": False, "is_scroll": False})
        elif icls == "cursor":
            inner.append({"name": iname, "value": scroll_id,
                          "is_string": is_str, "is_scroll": True})
        else:
            inner_unknown.append({"name": iname, "type": itype_name,
                                  "required": is_req})

    return {
        "name": arg["name"],
        "type_name": tname,
        "inner_fields": inner,
        "inner_unknown": inner_unknown,
    }, None


# ================================================================
# ANALISE DO TIPO DE RETORNO
# ================================================================
def analyze_return_type(app_id, secret, type_name):
    """
    Descobre a estrutura de retorno:
      list_field, item_type, scroll_field, more_field, all_fields
    """
    type_info, err = introspect_type(app_id, secret, type_name)
    if err or not type_info:
        return None, err

    fields = type_info.get("fields", [])
    field_names = [f["name"] for f in fields]

    result = {
        "all_fields": field_names,
        "list_field": None,
        "item_type": None,
        "scroll_field": None,
        "more_field": None,
    }

    for candidate in NODE_KEYS:
        if candidate in field_names:
            result["list_field"] = candidate
            for f in fields:
                if f["name"] == candidate:
                    ft = f.get("type", {})
                    iname, _ = _resolve_type(ft)
                    result["item_type"] = iname
                    # Se eh uma lista, o tipo base esta dentro de ofType
                    if ft.get("kind") == "LIST" or (
                        ft.get("kind") == "NON_NULL"
                        and ft.get("ofType", {}).get("kind") == "LIST"
                    ):
                        inner = ft.get("ofType", ft)
                        if inner.get("kind") == "LIST":
                            inner = inner.get("ofType", inner)
                        iname2, _ = _resolve_type(inner)
                        if iname2:
                            result["item_type"] = iname2
            break

    for c in SCROLL_KEYS:
        if c in field_names:
            result["scroll_field"] = c
            break

    for c in MORE_KEYS:
        if c in field_names:
            result["more_field"] = c
            break

    return result, None


def discover_item_fields(app_id, secret, item_type_name):
    """Descobre os campos disponiveis dentro de cada item (pedido)."""
    if not item_type_name:
        return []
    type_info, err = introspect_type(app_id, secret, item_type_name)
    if err or not type_info:
        return []
    return [f["name"] for f in type_info.get("fields", [])]


# ================================================================
# CONSTRUCAO DINAMICA DA QUERY
# ================================================================
def _render_arg_value(value, is_string):
    if is_string:
        return '"' + str(value) + '"'
    return str(value)


def build_args_string(mapped_flat, mapped_inputs, scroll_override=None):
    parts = []

    for item in mapped_flat:
        val = item["value"]
        if item["is_scroll"] and scroll_override is not None:
            val = scroll_override
        parts.append(item["name"] + ":" + _render_arg_value(val, item["is_string"]))

    for inp in mapped_inputs:
        inner_parts = []
        for ifield in inp["inner_fields"]:
            val = ifield["value"]
            if ifield["is_scroll"] and scroll_override is not None:
                val = scroll_override
            inner_parts.append(
                ifield["name"] + ":" + _render_arg_value(val, ifield["is_string"])
            )
        parts.append(inp["name"] + ":{" + ",".join(inner_parts) + "}")

    return ",".join(parts)


def build_full_query(root_field, args_string, ret_analysis, order_fields_str):
    q = "{" + root_field
    if args_string:
        q += "(" + args_string + ")"

    if ret_analysis and ret_analysis.get("list_field"):
        q += "{"
        q += ret_analysis["list_field"] + "{" + order_fields_str + "}"
        if ret_analysis.get("scroll_field"):
            q += " " + ret_analysis["scroll_field"]
        if ret_analysis.get("more_field"):
            q += " " + ret_analysis["more_field"]
        q += "}"
    else:
        q += "{" + order_fields_str + "}"

    return q


# ================================================================
# FETCH ORDERS — PAGINACAO DINAMICA
# ================================================================
def fetch_orders(app_id, secret, root_field,
                 mapped_flat, mapped_inputs,
                 ret_analysis, order_fields_str):
    all_nodes = []
    scroll_value = ""
    has_more = True
    page = 0

    list_key = ret_analysis.get("list_field") if ret_analysis else None
    scroll_key = ret_analysis.get("scroll_field") if ret_analysis else None
    more_key = ret_analysis.get("more_field") if ret_analysis else None

    while has_more and page < MAX_PAGES:
        override = scroll_value if page > 0 else None
        args_str = build_args_string(mapped_flat, mapped_inputs,
                                     scroll_override=override)
        q = build_full_query(root_field, args_str, ret_analysis, order_fields_str)

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
        if list_key and list_key in data and isinstance(data[list_key], list):
            nodes = data[list_key]
        elif isinstance(data, list):
            nodes = data
        else:
            for v in data.values():
                if isinstance(v, list):
                    nodes = v
                    break

        all_nodes.extend(nodes)

        if not nodes:
            break

        # Paginacao
        if scroll_key and scroll_key in data:
            new_scroll = data[scroll_key]
            if new_scroll and str(new_scroll) != scroll_value:
                scroll_value = str(new_scroll)
            else:
                break
        else:
            break

        if more_key and more_key in data:
            has_more = bool(data[more_key])
        else:
            has_more = False

        page += 1

    return all_nodes, None, ""


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


def show_discovery(label, value, status="ok"):
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
st.markdown(
    '<div class="hdr">Shopee Affiliates</div>', unsafe_allow_html=True
)
st.markdown(
    '<div class="hdr-sub">'
    "Dashboard de Comissoes - API v2 GraphQL - Deep Auto-Discovery"
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
        '<div class="desc">O sistema faz deep introspection automatica</div>'
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
# DISCOVERY PIPELINE
# ================================================================
st.markdown("#### Descoberta automatica do schema")

# --- FASE 1: Root field ---
with st.spinner("Fase 1/4: Descobrindo root field..."):
    root_names, err1 = introspect_root_fields(app_id, secret)

if err1 or not root_names:
    st.error("Falha na introspection: " + str(err1))
    st.stop()

root_field = find_order_field(root_names)
if not root_field:
    st.error("Nenhum campo de pedidos encontrado. Campos disponiveis:")
    for n in sorted(root_names):
        st.code(n)
    st.stop()

show_discovery("Root field", root_field)


# --- FASE 2: Argumentos ---
with st.spinner("Fase 2/4: Descobrindo argumentos de " + root_field + "..."):
    args, ret_type_name, err2 = introspect_field_deep(app_id, secret, root_field)

if err2:
    st.error("Erro ao introspeccionar argumentos: " + err2)
    st.stop()

args_summary = ", ".join(
    a["name"] + "(" + str(a["type_name"]) + ")" for a in args
)
show_discovery(
    "Argumentos (" + str(len(args)) + ")",
    args_summary if args_summary else "nenhum",
)
show_discovery("Tipo de retorno", str(ret_type_name))


# --- FASE 3: Tipo de retorno ---
ret_analysis = None
available_order_fields = []

if ret_type_name:
    with st.spinner("Fase 3/4: Analisando tipo " + ret_type_name + "..."):
        ret_analysis, err3 = analyze_return_type(app_id, secret, ret_type_name)

    if ret_analysis:
        show_discovery(
            "Estrutura",
            "list=" + str(ret_analysis.get("list_field"))
            + " scroll=" + str(ret_analysis.get("scroll_field"))
            + " more=" + str(ret_analysis.get("more_field")),
        )

        # Descobrir campos dentro dos items
        item_type = ret_analysis.get("item_type")
        if item_type:
            available_order_fields = discover_item_fields(
                app_id, secret, item_type
            )
            show_discovery(
                "Campos do item (" + str(item_type) + ")",
                ", ".join(available_order_fields) if available_order_fields else "?",
            )
    else:
        show_discovery("Estrutura", "nao foi possivel analisar", status="warn")
else:
    show_discovery("Tipo de retorno", "desconhecido", status="warn")


# --- Validar campos solicitados ---
if available_order_fields:
    valid_fields = [f for f in ORDER_FIELDS if f in available_order_fields]
    missing = [f for f in ORDER_FIELDS if f not in available_order_fields]
    if missing:
        show_discovery(
            "Campos indisponiveis",
            ", ".join(missing),
            status="warn",
        )
    order_fields_str = " ".join(valid_fields) if valid_fields else " ".join(ORDER_FIELDS)
else:
    order_fields_str = " ".join(ORDER_FIELDS)


# --- FASE 4: Mapear argumentos ---
with st.spinner("Fase 4/4: Mapeando argumentos..."):
    mapped_flat, unknown_args, input_obj_args = map_args_flat(
        args, start_ts, end_ts, PAGE_SIZE, ""
    )

    mapped_inputs = []
    input_errors = []
    for io_arg in input_obj_args:
        result_io, io_err = map_input_object(
            app_id, secret, io_arg, start_ts, end_ts, PAGE_SIZE, ""
        )
        if io_err:
            input_errors.append(io_err)
        elif result_io:
            mapped_inputs.append(result_io)
            if result_io.get("inner_unknown"):
                for unk in result_io["inner_unknown"]:
                    if unk.get("required"):
                        input_errors.append(
                            "Campo obrigatorio nao mapeado em "
                            + result_io["type_name"]
                            + ": " + unk["name"]
                            + " (" + str(unk.get("type")) + ")"
                        )

# Resumo do mapeamento
mapping_lines = []
for m in mapped_flat:
    mapping_lines.append(
        m["name"] + " -> " + m["cls"] + " = " + str(m["value"])
    )
for mi in mapped_inputs:
    for inner in mi["inner_fields"]:
        mapping_lines.append(
            mi["name"] + "." + inner["name"]
            + " -> " + str(inner["value"])
        )

show_discovery(
    "Mapeamento",
    "; ".join(mapping_lines) if mapping_lines else "nenhum arg mapeado",
    status="ok" if mapping_lines else "warn",
)

if unknown_args:
    unk_names = [a["name"] + "(" + str(a.get("type_name")) + ")" for a in unknown_args]
    # Verificar se algum eh obrigatorio
    required_unknown = [a for a in unknown_args if a.get("required")]
    if required_unknown:
        show_discovery(
            "Args obrigatorios NAO mapeados",
            ", ".join(a["name"] for a in required_unknown),
            status="warn",
        )
        st.error(
            "Existem argumentos obrigatorios que o sistema nao conseguiu mapear: "
            + ", ".join(a["name"] + " (" + str(a.get("type_name")) + ")"
                        for a in required_unknown)
        )
        # Vamos tentar mesmo assim — talvez o GraphQL aceite sem eles
    else:
        show_discovery(
            "Args opcionais ignorados",
            ", ".join(unk_names),
        )

if input_errors:
    for ie in input_errors:
        show_discovery("Aviso", ie, status="warn")

# Preview da query
preview_args = build_args_string(mapped_flat, mapped_inputs)
preview_query = build_full_query(
    root_field, preview_args, ret_analysis, order_fields_str
)

with st.expander("Query que sera enviada"):
    st.code(preview_query, language="graphql")

st.markdown('<hr class="sep">', unsafe_allow_html=True)


# ================================================================
# EXECUTAR QUERY
# ================================================================
with st.spinner("Buscando pedidos..."):
    raw_orders, fetch_err, last_query = fetch_orders(
        app_id, secret, root_field,
        mapped_flat, mapped_inputs,
        ret_analysis, order_fields_str,
    )

if fetch_err:
    st.error(fetch_err)
    with st.expander("Debug"):
        st.code("Ultima query:\n" + last_query, language="graphql")
        st.json({
            "endpoint": ENDPOINT,
            "root_field": root_field,
            "args": [a["name"] + ":" + str(a.get("type_name")) for a in args],
            "return_type": ret_type_name,
            "start_ts": start_ts,
            "end_ts": end_ts,
        })
    st.stop()


# ================================================================
# PROCESSAR E EXIBIR
# ================================================================
valid_orders, total_raw = process(raw_orders)
total_valid = len(valid_orders)
total_comm = sum(o["commission"] for o in valid_orders)
conv_rate = (total_valid / total_raw * 100) if total_raw > 0 else 0.0

# 4 METRICAS
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
        "de " + str(total_raw) + " retornados - "
        + str(total_raw - total_valid) + " removidos",
    )
with k3:
    card(
        "COMISSAO LIQUIDA",
        brl(total_comm),
        "net + estimated (validos)",
        css="green",
    )
with k4:
    card(
        "TAXA CONVERSAO",
        str(round(conv_rate, 1)) + "%",
        "validos / total retornado",
    )


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
                return datetime.fromtimestamp(
                    int(ts), tz=BR_TZ
                ).strftime("%d/%m/%Y %H:%M")
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
        "root_field": root_field,
        "args_discovered": [
            {"name": a["name"], "type": a.get("type_name"),
             "kind": a.get("type_kind"), "required": a.get("required")}
            for a in args
        ],
        "return_type": ret_type_name,
        "return_structure": ret_analysis,
        "available_item_fields": available_order_fields,
        "requested_fields": order_fields_str,
        "mapping_flat": [
            {"name": m["name"], "cls": m["cls"], "value": m["value"]}
            for m in mapped_flat
        ],
        "mapping_inputs": [
            {"name": mi["name"], "type": mi["type_name"],
             "fields": [f["name"] for f in mi["inner_fields"]]}
            for mi in mapped_inputs
        ],
        "unknown_args": [a["name"] for a in unknown_args],
        "start_ts": start_ts,
        "end_ts": end_ts,
        "query_preview": preview_query,
    })
