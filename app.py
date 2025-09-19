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

# ---------- LOGO: búsqueda robusta en varias carpetas ----------
LOGO_HEIGHT_PX = 48  # podés ajustar el tamaño del logo

def _read_file_as_data_uri(p: Path) -> str | None:
    if not p.exists() or not p.is_file():
        return None
    ext = p.suffix.lower()
    mime = "image/png"
    if ext == ".svg":
        mime = "image/svg+xml"
    elif ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    try:
        data = base64.b64encode(p.read_bytes()).decode("utf-8")
        return f"data:{mime};base64,{data}"
    except Exception:
        return None

def resolve_logo_src() -> tuple[str | None, list[str]]:
    found = []
    try:
        script_dir = Path(__file__).parent.resolve()
    except NameError:
        script_dir = Path.cwd().resolve()
    parent_dir = script_dir.parent
    cwd_dir = Path.cwd().resolve()

    candidates = [
        script_dir / "logo.png",
        script_dir / "logo.svg",
        script_dir / "logo.jpg",
        script_dir / "logo.jpeg",
        script_dir / "assets" / "logo.png",
        script_dir / "assets" / "logo.svg",
        script_dir / "assets" / "logo.jpg",
        script_dir / "assets" / "logo.jpeg",
        parent_dir / "logo.png",
        parent_dir / "logo.svg",
        parent_dir / "logo.jpg",
        parent_dir / "logo.jpeg",
        parent_dir / "assets" / "logo.png",
        parent_dir / "assets" / "logo.svg",
        parent_dir / "assets" / "logo.jpg",
        parent_dir / "assets" / "logo.jpeg",
        cwd_dir / "logo.png",
        cwd_dir / "logo.svg",
        cwd_dir / "logo.jpg",
        cwd_dir / "logo.jpeg",
        cwd_dir / "assets" / "logo.png",
        cwd_dir / "assets" / "logo.svg",
        cwd_dir / "assets" / "logo.jpg",
        cwd_dir / "assets" / "logo.jpeg",
    ]

    for p in candidates:
        if p.exists():
            found.append(str(p))
            src = _read_file_as_data_uri(p)
            if src:
                return src, found
    return None, found

LOGO_SRC, _ = resolve_logo_src()

# ---- Estilos: título chico + logo flotante transparente + layout prolijo ----
st.markdown(f"""
<style>
/* Más aire arriba para evitar recortes del header */
.block-container {{
  padding-top: 2.0rem !important;
  padding-bottom: 0.25rem !important;
}}
[data-testid="stAppViewContainer"] > .main {{
  overflow: visible !important;
}}
header, [data-testid="stHeader"] {{
  height: auto !important;
  overflow: visible !important;
}}

h1 {{
  font-size: 1.15rem !important;
  margin-top: 0.2rem !important;
  margin-bottom: 0.6rem !important;
  line-height: 1.25 !important;
  white-space: normal !important;
  overflow-wrap: anywhere;
}}
[data-testid="stSidebar"] {{
  min-width: 300px; width: 300px; border-right: 1px solid #eee;
}}
.info-card {{
  border: 1px solid #e9e9e9; border-radius: 12px; padding: 10px 12px;
  background: #fafafa; margin-top: 10px;
}}
/* SIN barra de acciones */

/* Logo flotante (fondo transparente) — más abajo y más hacia la izquierda */
.top-right-logo {{
  position: fixed;
  top: 72px;                 /* altura: ajustá si hace falta */
  right: 28px;               /* más a la izquierda */
  z-index: 2147483647;
  background: transparent;
  padding: 0;
  border-radius: 0;
  box-shadow: none;
}}
.top-right-logo img {{
  height: {LOGO_HEIGHT_PX}px; width: auto; display: block;
}}
</style>
""", unsafe_allow_html=True)

# Render del logo (cambiá href='#' por tu sitio si querés que sea clickeable)
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
    m = re.search(r"https://drive\\.google\\.com/file/d/([^/]+)/", url)
    if m: return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    m = re.search(r"https://drive\\.google\\.com/open\\?id=([^&]+)", url)
    if m: return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    m = re.search(r"https://drive\\.google\\.com/uc\\?(?:export=download&)?id=([^&]+)", url)
    if m: return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    m = re.search(r"https://docs\\.google\\.com/document/d/([^/]+)/", url)
    if m: return f"https://docs.google.com/document/d/{m.group(1)}/pub?embedded=true"
    m = re.search(r"https://docs\\.google\\.com/spreadsheets/d/([^/]+)/", url)
    if m: return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/pubhtml?widget=true&headers=false"
    m = re.search(r"https://docs\\.google\\.com/presentation/d/([^/]+)/", url)
    if m: return f"https://docs.google.com/presentation/d/{m.group(1)}/embed?start=false&loop=false"
    return url

# (lo dejamos disponible por si lo querés reusar más adelante)
def drive_download_url(url: str) -> str | None:
    m = re.search(r"https://drive\\.google\\.com/file/d/([^/]+)/", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"https://drive\\.google\\.com/open\\?id=([^&]+)", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"https://drive\\.google\\.com/uc\\?(?:export=download&)?id=([^&]+)", url)
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

choices = [i["tag"] for i in items]
choice = st.sidebar.selectbox("Enlaces", choices, index=0)
selected = next(i for i in items if i["tag"] == choice)

# Link para abrir en nueva pestaña (solo en el navegador)
st.sidebar.markdown(f"[Abrir {choice} en nueva pestaña]({selected['url']})")

# ================== MAIN ==================
st.title("Demo de Producto — Tracking")

# Iframe fijo a 900 px (sin barra de acciones arriba)
embed_url = normalize_drive_url(selected["url"])
try:
    iframe(src=embed_url, height=900, scrolling=True)  # altura fija a 900 px
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
