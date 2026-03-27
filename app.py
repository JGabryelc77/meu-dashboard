"""
Shopee Affiliates Dashboard - API v2 GraphQL
Endpoint: conversionReport (acessivel)
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
# INTROSPECTION - SAFE VERSION
# ================================================================
def _resolve_base(t):
    """Desembrulha NON_NULL/LIST, retorna (name, kind, is_list)"""
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
    """
    Introspecciona um tipo e retorna lista de campos.
    Retorna: (list_of_fields, error)
    Cada campo: {name, type_name, type_kind, is_list, is_scalar}
    """
    if not type_name:
        return [], "type_name vazio"

    q = (
        '{__type(name:"' + type_name + '"){name kind'
        ' fields{name type{name kind ofType{name kind ofType{name kind ofType{name kind}}}}}'
        '}}'
    )
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
    """
    Introspecciona recursivamente. SAFE contra loops e None.
    Retorna dict com campos e sub-campos.
    """
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
        fd = dict(f)  # copia
        # Se nao eh escalar e temos profundidade, recursear
        if not fd["is_scalar"] and fd["type_name"] and fd["type_name"] not in visited and depth > 1:
            fd["sub"] = introspect_deep(app_id, secret, fd["type_name"], depth - 1, visited.copy())
        result["fields"].append(fd)

    return result

# ================================================================
# BUILD FIELDS STRING FROM TREE
# ================================================================
def fields_from_tree(tree):
    """Constroi string de campos GraphQL."""
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

def tree_to_lines(tree, indent=0):
    """Renderiza arvore como linhas para exibicao."""
    if not tree or not isinstance(tree, dict):
        return []
    lines = []
    prefix = "    " * indent
    for f in tree.get("fields", []):
        if not isinstance(f, dict):
            continue
        name = f.get("name", "?")
        ts = str(f.get("type_name", "?"))
        if f.get("is_list"):
            ts = "[" + ts + "]"
        if f.get("is_scalar"):
            lines.append(prefix + name + " : " + ts)
        else:
            lines.append(prefix + name + " : " + ts + " (OBJECT)")
            if "sub" in f and isinstance(f["sub"], dict):
                lines.extend(tree_to_lines(f["sub"], indent + 1))
    return lines

# ================================================================
# UI HELPERS
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
    st.caption("Usa conversionReport (acessivel)")

# ================================================================
# HEADER
# ================================================================
st.markdown('<div class="hdr">Shopee Affiliates</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hdr-sub">'
    "Dashboard de Comissoes - conversionReport"
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
        '<div class="desc">conversionReport com auto-discovery</div>'
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
# FASE 1: INTROSPECT ConversionReportConnection
# ================================================================
st.markdown("#### Fase 1: Estrutura de ConversionReportConnection")

with st.spinner("Introspectando ConversionReportConnection..."):
    conn_fields, conn_err = introspect_type_fields(app_id, secret, "ConversionReportConnection")

if conn_err:
    st.error("Erro: " + conn_err)
    st.stop()

conn_field_names = [f["name"] for f in conn_fields]
show_disc("Campos connection", ", ".join(conn_field_names))

# Identificar campo de lista (nodes)
list_field = None
list_type = None
for f in conn_fields:
    if f["name"] == "nodes" or (f.get("is_list") and not f.get("is_scalar")):
        list_field = f["name"]
        list_type = f.get("type_name")
        break

# Identificar campo scrollId
has_scroll = "scrollId" in conn_field_names
has_more = "more" in conn_field_names

# Outros campos de paginacao
page_fields = []
for f in conn_fields:
    if f.get("is_scalar") and f["name"] not in (list_field,):
        page_fields.append(f["name"])

show_disc("Campo lista", str(list_field) + " -> " + str(list_type))
show_disc("scrollId", "SIM" if has_scroll else "NAO")
show_disc("more", "SIM" if has_more else "NAO")
show_disc("Outros campos", ", ".join(page_fields) if page_fields else "nenhum")

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 2: INTROSPECT NODE TYPE
# ================================================================
node_type = list_type or "ConversionReport"
st.markdown("#### Fase 2: Estrutura de " + node_type)

with st.spinner("Deep introspection de " + node_type + "..."):
    node_tree = introspect_deep(app_id, secret, node_type, depth=3)

tree_lines = tree_to_lines(node_tree)
if tree_lines:
    st.code("\n".join(tree_lines))

node_fields_str = fields_from_tree(node_tree)
show_disc("Campos auto-gerados", node_fields_str if node_fields_str else "VAZIO")

# Se vazio, tentar apenas escalares diretos
if not node_fields_str:
    with st.spinner("Tentando campos escalares de " + node_type + "..."):
        node_fields_list, nf_err = introspect_type_fields(app_id, secret, node_type)
    if not nf_err and node_fields_list:
        scalars = [f["name"] for f in node_fields_list if f.get("is_scalar")]
        node_fields_str = " ".join(scalars)
        show_disc("Fallback escalares", node_fields_str, status="warn")
    else:
        show_disc("Erro", str(nf_err), status="err")

# Listar TODOS os campos do node (para analise)
all_node_fields, _ = introspect_type_fields(app_id, secret, node_type)
all_field_names = [f["name"] for f in all_node_fields]
show_disc("Todos campos do node", ", ".join(all_field_names))

# Verificar campos de comissao
commission_fields = [n for n in all_field_names
                     if any(k in n.lower() for k in ["commission", "amount", "earning",
                                                      "payout", "net", "estimated", "revenue"])]
status_fields = [n for n in all_field_names
                 if any(k in n.lower() for k in ["status", "conversion"])]
time_fields = [n for n in all_field_names
               if any(k in n.lower() for k in ["time", "date", "created"])]

if commission_fields:
    show_disc("Campos de comissao encontrados", ", ".join(commission_fields))
else:
    show_disc("Campos de comissao", "Nenhum direto - pode estar em sub-objetos", status="warn")

if status_fields:
    show_disc("Campos de status", ", ".join(status_fields))
if time_fields:
    show_disc("Campos de tempo", ", ".join(time_fields))

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 3: MONTAR E TESTAR QUERY
# ================================================================
st.markdown("#### Fase 3: Testando query")

# Construir args
test_args = "purchaseTimeStart:" + str(start_ts) + ",purchaseTimeEnd:" + str(end_ts) + ",limit:2"

# Construir body
extra_conn_fields = ""
if has_scroll:
    extra_conn_fields += " scrollId"
if has_more:
    extra_conn_fields += " more"
# Outros campos escalares do connection
for pf in page_fields:
    if pf not in ("scrollId", "more"):
        extra_conn_fields += " " + pf

if list_field and node_fields_str:
    test_body = list_field + "{" + node_fields_str + "}" + extra_conn_fields
else:
    test_body = node_fields_str + extra_conn_fields

test_q = "{conversionReport(" + test_args + "){" + test_body + "}}"

with st.expander("Query de teste"):
    st.code(test_q, language="graphql")

# Testar
with st.spinner("Testando..."):
    try:
        test_result = _sign_and_call(app_id, secret, test_q)
    except Exception as exc:
        test_result = {"errors": [{"message": str(exc)}]}

if "errors" in test_result:
    err_msg = test_result["errors"][0].get("message", str(test_result["errors"]))
    show_disc("Teste completo", err_msg, status="err")

    # Tentar variante minima
    st.markdown("##### Tentando variantes...")

    # Variante 1: Apenas campos escalares diretos, sem sub-objetos
    scalars_only = " ".join(f["name"] for f in all_node_fields if f.get("is_scalar"))
    if scalars_only:
        q_v1 = "{conversionReport(" + test_args + "){" + list_field + "{" + scalars_only + "}" + extra_conn_fields + "}}"
        with st.spinner("Apenas escalares..."):
            try:
                r_v1 = _sign_and_call(app_id, secret, q_v1)
                if "errors" not in r_v1:
                    show_disc("Apenas escalares", "SUCESSO!", status="ok")
                    test_result = r_v1
                    node_fields_str = scalars_only
                else:
                    show_disc("Apenas escalares", r_v1["errors"][0].get("message", "")[:80], status="err")
            except Exception as e1:
                show_disc("Apenas escalares", str(e1)[:60], status="err")

    # Variante 2: Sem completeTime nos args
    if "errors" in test_result:
        for fields_try in [scalars_only, node_fields_str]:
            if not fields_try:
                continue
            body_try = list_field + "{" + fields_try + "}" + extra_conn_fields if list_field else fields_try + extra_conn_fields
            q_v2 = "{conversionReport(purchaseTimeStart:" + str(start_ts) + ",purchaseTimeEnd:" + str(end_ts) + ",limit:2){" + body_try + "}}"
            with st.spinner("Sem completeTime..."):
                try:
                    r_v2 = _sign_and_call(app_id, secret, q_v2)
                    if "errors" not in r_v2:
                        show_disc("Sem completeTime", "SUCESSO!", status="ok")
                        test_result = r_v2
                        node_fields_str = fields_try
                        break
                    else:
                        show_disc("Sem completeTime", r_v2["errors"][0].get("message", "")[:80], status="err")
                except Exception as e2:
                    show_disc("Sem completeTime", str(e2)[:60], status="err")

    # Variante 3: Sem nenhum arg
    if "errors" in test_result:
        body_try = list_field + "{" + scalars_only + "}" + extra_conn_fields if list_field and scalars_only else "__typename"
        q_v3 = "{conversionReport{" + body_try + "}}"
        with st.spinner("Sem args..."):
            try:
                r_v3 = _sign_and_call(app_id, secret, q_v3)
                if "errors" not in r_v3:
                    show_disc("Sem args", "SUCESSO!", status="ok")
                    test_result = r_v3
                else:
                    show_disc("Sem args", r_v3["errors"][0].get("message", "")[:80], status="err")
            except Exception as e3:
                show_disc("Sem args", str(e3)[:60], status="err")

    if "errors" in test_result:
        st.error("Nenhuma variante funcionou")
        with st.expander("Debug completo"):
            st.json({
                "conn_fields": conn_field_names,
                "node_type": node_type,
                "all_node_fields": all_field_names,
                "node_fields_str": node_fields_str,
                "scalars_only": scalars_only if scalars_only else "",
                "test_query": test_q,
                "errors": test_result.get("errors"),
            })
        st.stop()
else:
    show_disc("Teste", "SUCESSO!", status="ok")

# Mostrar amostra
with st.expander("Resposta do teste (amostra)"):
    st.json(test_result)

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 4: BUSCAR TODOS OS DADOS
# ================================================================
st.markdown("#### Fase 4: Buscando todos os dados")

all_nodes = []
scroll_id = None
page = 0
last_query = ""
fetch_err = None

while page < MAX_PAGES:
    # Construir args
    args_parts = [
        "purchaseTimeStart:" + str(start_ts),
        "purchaseTimeEnd:" + str(end_ts),
        "limit:" + str(PAGE_SIZE),
    ]
    # Adicionar scrollId APENAS se temos um
    if scroll_id:
        args_parts.append('scrollId:"' + str(scroll_id) + '"')

    args_str = ",".join(args_parts)

    # Construir body
    body = ""
    if list_field:
        body = list_field + "{" + node_fields_str + "}"
    else:
        body = node_fields_str

    if has_scroll:
        body += " scrollId"
    if has_more:
        body += " more"

    q = "{conversionReport(" + args_str + "){" + body + "}}"
    last_query = q

    with st.spinner("Pagina " + str(page + 1) + "..."):
        try:
            result = _sign_and_call(app_id, secret, q)
        except requests.exceptions.HTTPError as exc:
            code = getattr(exc.response, "status_code", "?")
            b = ""
            if exc.response is not None:
                b = exc.response.text[:500]
            fetch_err = "HTTP " + str(code) + ": " + b
            break
        except Exception as exc:
            fetch_err = str(exc)
            break

    if "errors" in result:
        fetch_err = "GraphQL: " + result["errors"][0].get("message", str(result["errors"]))
        break

    data = result.get("data", {}).get("conversionReport", {})

    # Extrair nodes
    nodes = []
    if list_field and list_field in data:
        nodes = data.get(list_field, [])
        if not isinstance(nodes, list):
            nodes = []
    elif isinstance(data, list):
        nodes = data
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                nodes = v
                break

    all_nodes.extend(nodes)

    if not nodes:
        break

    # Paginacao
    new_scroll = data.get("scrollId")
    has_more_val = data.get("more", False)

    if has_more_val and new_scroll and str(new_scroll) != str(scroll_id):
        scroll_id = str(new_scroll)
    else:
        break

    page += 1

if fetch_err:
    st.error(fetch_err)
    with st.expander("Debug"):
        st.code("Ultima query:\n" + last_query, language="graphql")
    st.stop()

show_disc("Total registros", str(len(all_nodes)))
show_disc("Paginas", str(page + 1))

if all_nodes:
    with st.expander("Amostra dados brutos (" + str(min(3, len(all_nodes))) + " registros)"):
        st.json(all_nodes[:3])

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ================================================================
# FASE 5: PROCESSAR E EXIBIR
# ================================================================

def _is_blacklisted(status):
    s = (status or "").lower()
    return any(bl in s for bl in BLACKLIST)

# Primeiro, analisar a estrutura dos dados reais
if all_nodes:
    sample = all_nodes[0]
    sample_keys = list(sample.keys()) if isinstance(sample, dict) else []
    show_disc("Campos no primeiro registro", ", ".join(sample_keys))

    # Auto-detectar campos de comissao nos dados reais
    comm_val_keys = []
    status_val_key = None
    time_val_key = None
    id_val_key = None

    for k in sample_keys:
        v = sample.get(k)
        # Detectar campos numericos que parecem comissao
        if any(kw in k.lower() for kw in ["commission", "amount", "earning",
                                           "payout", "net", "estimated", "revenue"]):
            comm_val_keys.append(k)
        # Detectar status
        if any(kw in k.lower() for kw in ["status", "conversion"]):
            if status_val_key is None:
                status_val_key = k
        # Detectar tempo
        if any(kw in k.lower() for kw in ["time", "date", "created"]):
            if v and (isinstance(v, (int, float)) and v > 1000000000):
                if time_val_key is None:
                    time_val_key = k
        # Detectar ID
        if any(kw in k.lower() for kw in ["id", "order"]):
            if id_val_key is None:
                id_val_key = k

    if comm_val_keys:
        show_disc("Campos de comissao detectados", ", ".join(comm_val_keys))
    if status_val_key:
        show_disc("Campo de status", status_val_key)
    if time_val_key:
        show_disc("Campo de tempo", time_val_key)

# Processar
valid_orders = []
total_raw = len(all_nodes)

for o in all_nodes:
    if not isinstance(o, dict):
        continue

    # Extrair comissao - tentar varios campos
    net = 0.0
    est = 0.0

    for k in ["netCommission", "commission", "commissionAmount",
              "affiliateCommission", "netAmount", "payout",
              "earning", "earnings", "net_commission"]:
        v = _sf(o.get(k))
        if v > 0:
            net = v
            break

    for k in ["estimatedTotalCommission", "estimatedCommission",
              "pendingCommission", "estimatedAmount",
              "estimated_commission", "estimated_total_commission"]:
        v = _sf(o.get(k))
        if v > 0:
            est = v
            break

    # Se nao achou em campos diretos, tentar actualAmount
    if net == 0 and est == 0:
        for k in ["actualAmount", "amount", "totalAmount", "orderAmount",
                   "purchaseAmount", "saleAmount"]:
            v = _sf(o.get(k))
            if v > 0:
                est = v
                break

    # Extrair status
    status = "-"
    for k in ["conversionStatus", "orderStatus", "status",
              "displayStatus", "conversion_status"]:
        v = o.get(k)
        if v and str(v).strip() and str(v) != "None":
            status = str(v)
            break

    # Filtro blacklist
    if _is_blacklisted(status):
        continue

    # Extrair timestamp
    ts = 0
    for k in ["purchaseTime", "createdTime", "createTime", "timestamp",
              "time", "created_at", "purchase_time", "completeTime"]:
        v = o.get(k)
        if v and isinstance(v, (int, float)) and v > 1000000000:
            ts = int(v)
            break

    # Tipo
    if net > 0:
        ctype = "Concluido"
        comm = net
    elif est > 0:
        ctype = "Pendente"
        comm = est
    else:
        ctype = "Pendente"
        comm = 0.0

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

    df = pd.DataFrame([{
        "Data/Hora": _fmt_ts(o["ts"]),
        "Status": o["status"],
        "Tipo": o["type"],
        "Comissao": brl(o["commission"]),
    } for o in valid_orders])

    display = df.sort_values("Data/Hora", ascending=False).reset_index(drop=True)
    st.dataframe(display, use_container_width=True, hide_index=True,
                 height=min(520, 36 * len(display) + 40))

elif total_raw > 0:
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.warning("Todos os " + str(total_raw) + " registros foram filtrados pela blacklist")
else:
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.info("Nenhum registro retornado para "
            + start_date.strftime("%d/%m/%Y") + " - "
            + end_date.strftime("%d/%m/%Y"))

# RODAPE
with st.expander("Debug completo"):
    st.json({
        "endpoint": ENDPOINT,
        "root_field": "conversionReport",
        "conn_fields": conn_field_names,
        "node_type": node_type,
        "node_fields": node_fields_str,
        "all_node_field_names": all_field_names,
        "has_scroll": has_scroll,
        "has_more": has_more,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "total_raw": total_raw,
        "total_valid": total_valid,
        "pages_fetched": page + 1,
        "last_query": last_query,
    })
