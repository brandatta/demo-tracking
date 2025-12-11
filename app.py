import re
import base64
from pathlib import Path
import streamlit as st
import mysql.connector
from mysql.connector import Error
from urllib.parse import urlparse
from streamlit.components.v1 import iframe
import streamlit.components.v1 as components

# ================== CONFIG / UI ==================
st.set_page_config(page_title="Demo Tracking - Navegador MySQL", layout="wide")

# ---------- LOGO ----------
LOGO_HEIGHT_PX = 48

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
        script_dir / "logo.png", script_dir / "logo.svg",
        parent_dir / "logo.png", parent_dir / "logo.svg",
        cwd_dir / "logo.png", cwd_dir / "logo.svg",
        script_dir / "assets" / "logo.png", script_dir / "assets" / "logo.svg",
        parent_dir / "assets" / "logo.png", parent_dir / "assets" / "logo.svg",
        cwd_dir / "assets" / "logo.png", cwd_dir / "assets" / "logo.svg",
    ]
    for p in candidates:
        if p.exists():
            found.append(str(p))
            src = _read_file_as_data_uri(p)
            if src:
                return src, found
    return None, found

LOGO_SRC, _ = resolve_logo_src()

# ---- Estilos base ----
st.markdown(f"""
<style>
.block-container {{
  padding-top: 2.0rem !important;
  padding-bottom: 0.25rem !important;
}}

.top-right-logo {{
  position: fixed;
  top: 72px;
  right: 28px;
  z-index: 999999;
}}

.top-right-logo img {{
  height: {LOGO_HEIGHT_PX}px;
  width: auto;
}}

.info-card {{
  border: 1px solid #e9e9e9;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fafafa;
  margin-top: 10px;
}}
</style>
""", unsafe_allow_html=True)

# Logo
if LOGO_SRC:
    st.markdown(
        f"<div class='top-right-logo'><img src='{LOGO_SRC}'></div>",
        unsafe_allow_html=True
    )

# ================== SECRETS / PARAMS (DB) ==================
DB = st.secrets["mysql"]
SCHEMA  = st.secrets.get("schema", "streamlit_apps")
TABLE   = st.secrets.get("table", "links_demos")
TAG_COL = st.secrets.get("tag_col", "tag")
URL_COL = st.secrets.get("url_col", "links")
HTML_COL = st.secrets.get("html_col", "html_top")
FQN     = f"`{SCHEMA}`.`{TABLE}`"

# ================== UTILS ==================
def normalize_drive_url(url: str) -> str:
    if not url:
        return url
    m = re.search(r"https://drive\.google\.com/file/d/([^/]+)/", url)
    if m:
        return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    return url

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
    rows = []
    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Intento 1: traer html_top
        try:
            cur.execute(
                f"SELECT `{TAG_COL}`, `{URL_COL}`, `{HTML_COL}` "
                f"FROM {FQN} ORDER BY `{TAG_COL}`"
            )
            for tag, url, html_top in cur.fetchall():
                rows.append({
                    "tag": tag,
                    "url": url,
                    "html_top": html_top or ""
                })
        except:
            # Fallback: si no existe html_top
            cur = conn.cursor()
            cur.execute(
                f"SELECT `{TAG_COL}`, `{URL_COL}` FROM {FQN} ORDER BY `{TAG_COL}`"
            )
            for tag, url in cur.fetchall():
                rows.append({
                    "tag": tag,
                    "url": url,
                    "html_top": ""
                })

    except Error as e:
        st.error(f"Error al leer {FQN}: {e}")
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except:
            pass
    return rows

items = load_nav_items()

# ================== SIDEBAR (siempre visible) ==================
st.sidebar.title("Navegador")

if not items:
    st.sidebar.warning("No se encontraron items.")
    st.stop()

choices = [i["tag"] for i in items]
choice = st.sidebar.selectbox("Enlaces", choices, index=0)
selected = next(i for i in items if i["tag"] == choice)

st.sidebar.markdown(f"[Abrir {choice} en nueva pestaña]({selected['url']})")

# ================== MAIN ==================

# Bloque HTML ARRIBA (si existe)
top_html = selected.get("html_top", "").strip()

if top_html:
    st.subheader("Vista general")
    if top_html.startswith("http://") or top_html.startswith("https://"):
        iframe(src=top_html, height=260, scrolling=False)
    else:
        html_path = Path(top_html)
        if not html_path.is_absolute():
            script_dir = Path(__file__).parent.resolve()
            html_path = script_dir / html_path

        if html_path.exists():
            components.html(html_path.read_text(), height=260, scrolling=False)
        else:
            st.warning(f"No se encontró el HTML superior: {html_path}")

# CONTENIDO PRINCIPAL
st.title("Demo de Producto — Tracking")

embed_url = normalize_drive_url(selected["url"])

iframe(src=embed_url, height=900, scrolling=True)

parsed = urlparse(selected["url"])
host = parsed.netloc or parsed.path

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
