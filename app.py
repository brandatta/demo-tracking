import re
import base64
from pathlib import Path
import streamlit as st
import mysql.connector
from mysql.connector import Error
from urllib.parse import urlparse
from streamlit.components.v1 import iframe

# ================== CONFIG / UI ==================
st.set_page_config(page_title="Demo Tracking - Navegador MySQL", layout="wide")

# ---------- LOGO (archivo local en raíz o /assets, sin secrets) ----------
LOCAL_LOGO_CANDIDATES = [
    "logo.png", "logo.svg", "logo.jpg", "logo.jpeg",                # raíz del repo
    "assets/logo.png", "assets/logo.svg", "assets/logo.jpg", "assets/logo.jpeg",  # fallback
]
RAW_GITHUB_LOGO_URL = ""  # opcional: raw URL de GitHub si querés forzar URL externa
LOGO_HEIGHT_PX = 28

def data_uri_from_file(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    ext = p.suffix.lower()
    mime = "image/png"
    if ext == ".svg":
        mime = "image/svg+xml"
    elif ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    data = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"

def resolve_logo_src() -> str | None:
    # 1) archivo local (prioriza raíz del repo)
    for candidate in LOCAL_LOGO_CANDIDATES:
        src = data_uri_from_file(candidate)
        if src:
            return src
    # 2) fallback: URL cruda de GitHub si la completaste arriba
    if RAW_GITHUB_LOGO_URL.strip():
        return RAW_GITHUB_LOGO_URL.strip()
    return None

LOGO_SRC = resolve_logo_src()

# ---- Estilos: título chico + logo arriba derecha + layout prolijo ----
st.markdown(f"""
<style>
.block-container {{
  padding-top: 1.2rem !important;
  padding-bottom: 0.25rem !important;
}}
h1 {{
  font-size: 1.15rem !important;
  margin-top: 0.2rem !important;
  margin-bottom: 0.6rem !important;
  line-height: 1.25 !important;
  white-space: normal !important;
  overflow-wrap: anywhere;
}}
[data-testid="stAppViewContainer"] > .main {{ overflow: visible !important; }}
[data-testid="stSidebar"] {{
  min-width: 300px; width: 300px; border-right: 1px solid #eee;
}}
.info-card {{
  border: 1px solid #e9e9e9; border-radius: 12px; padding: 10px 12px;
  background: #fafafa; margin-top: 10px;
}}
.actions {{ text-align: right; margin-bottom: 6px; }}
.actions a {{ text-decoration: none; }}

/* Logo fijo arriba a la derecha (z-index alto por si el header tapa) */
.top-right-logo {{
  position: fixed; top: 10px; right: 14px; z-index: 99999;
}}
.top-right-logo img {{
  height: {LOGO_HEIGHT_PX}px; width: auto; display: block;
}}
</style>
""", unsafe_allow_html=True)

# Render del logo (clickeable si querés: cambiá href='#' por tu sitio)
if LOGO_SRC:
    st.markdown(
        f"<div class='top-right-logo'><a href='#' target='_blank'><img src='{LOGO_SRC}' alt='Logo'></a></div>",
        unsafe_allow_html=True
    )

# ================== SECRETS / PARAMS (DB) ==================
DB = st.secrets["mysql"]  # credenciales
SCHEMA  = st.secrets.get("schema", "streamlit_apps")
TABLE   = st.secrets.get("table", "links_demos")
TAG_COL = st.secrets.get("tag_col", "tag")
URL_COL = st.secrets.get("url_col", "links")
FQN     = f"`{SCHEMA}`.`{TABLE}`"

# ================== UTILS (Drive + PDF) ==================
def normalize_drive_url(url: str) -> str:
    """Convierte links de Drive/Docs a URLs embebibles para iframe."""
    if not url:
        return url
    m = re.search(r"https://drive\.google\.com/file/d/([^/]+)/", url)
    if m: return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    m = re.search(r"https://drive\.google\.com/open\?id=([^&]+)", url)
    if m: return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    m = re.search(r"https://drive\.google\.com/uc\?(?:export=download&)?id=([^&]+)", url)
    if m: return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    m = re.search(r"https://docs\.google\.com/document/d/([^/]+)/", url)
    if m: return f"https://docs.google.com/document/d/{m.group(1)}/pub?embedded=true"
    m = re.search(r"https://docs\.google\.com/spreadsheets/d/([^/]+)/", url)
    if m: return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/pubhtml?widget=true&headers=false"
    m = re.search(r"https://docs\.google\.com/presentation/d/([^/]+)/", url)
    if m: return f"https://docs.google.com/presentation/d/{m.group(1)}/embed?start=false&loop=false"
    return url

def drive_download_url(url: str) -> str | None:
    """Genera link de descarga directa para archivos de Drive."""
    m = re.search(r"https://drive\.google\.com/file/d/([^/]+)/", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"https://drive\.google\.com/open\?id=([^&]+)", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"https://drive\.google\.com/uc\?(?:export=download&)?id=([^&]+)", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    return None

def is_pdf_url(url: str) -> bool:
    if not url: return False
    if "drive.google.com" in url: return True
    return url.lower().split("?")[0].endswith(".pdf")

# ================== DB ==================
def get_connection():
    return mysql.connector.connect(
        host=DB["host"],
        user=DB["user"],
        password=DB["password"],
        database=DB.get("database", SCHEMA),
        port=DB.get("port", 3306),
        autocommit=True,
    )

@st.cache_data(ttl=60)
def load_nav_items():
    """Devuelve [{'tag':..., 'url':...}] desde streamlit_apps.links_demos"""
    rows = []
    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT `{TAG_COL}`, `{URL_COL}` FROM {FQN} ORDER BY `{TAG_COL}`")
        for tag, url in cur.fetchall():
            if tag and url:
                rows.append({"tag": str(tag), "url": str(url)})
    except Error as e:
        st.error(f"Error al leer {FQN}: {e}")
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except:
            pass
    return rows

# ================== DATA ==================
items = load_nav_items()

# ================== SIDEBAR ==================
st.sidebar.title("Navegador")
if not items:
    st.sidebar.warning(f"No se encontraron ítems en {FQN}.")
    st.stop()

height = st.sidebar.slider("Altura del iframe (px)", 500, 1600, 900, 50)
choices = [i["tag"] for i in items]
choice = st.sidebar.selectbox("Enlaces", choices, index=0)
selected = next(i for i in items if i["tag"] == choice)

open_mode = st.sidebar.radio("Abrir enlace en", ["iframe (panel principal)", "Nueva pestaña"], index=0)
if open_mode == "Nueva pestaña":
    st.sidebar.markdown(f"[Abrir {choice} en nueva pestaña]({selected['url']})")

# ================== MAIN ==================
st.title("Demo de Producto — Tracking")

# Acciones (arriba del iframe): abrir / descargar si es PDF
pdf_download = None
if "drive.google.com" in selected["url"]:
    pdf_download = drive_download_url(selected["url"])
elif is_pdf_url(selected["url"]):
    pdf_download = selected["url"]

actions = f"<div class='actions'><a href='{selected['url']}' target='_blank'>Abrir en nueva pestaña</a>"
if pdf_download:
    actions += f" &nbsp;&nbsp;|&nbsp;&nbsp; <a href='{pdf_download}' download>Descargar PDF</a>"
actions += "</div>"
st.markdown(actions, unsafe_allow_html=True)

# Iframe (con URL normalizada si es Drive/Docs)
embed_url = normalize_drive_url(selected["url"])
if open_mode == "iframe (panel principal)":
    try:
        iframe(src=embed_url, height=height, scrolling=True)
        st.caption("Si no se ve, el sitio puede bloquear el embebido (X-Frame-Options/CSP).")
    except Exception:
        st.warning("No se pudo embeber el contenido. Abrilo en nueva pestaña.")

# Tarjeta de info (debajo del iframe)
parsed = urlparse(selected["url"])
host = (parsed.netloc or parsed.path).split('/')[0]
st.markdown(
    f"""
    <div class="info-card">
      <b>Item seleccionado:</b> {choice}<br>
      <b>URL:</b> <code>{selected['url']}</code><br>
      <b>Host:</b> {host}
    </div>
    """,
    unsafe_allow_html=True
)
