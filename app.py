import re
import streamlit as st
import mysql.connector
from mysql.connector import Error
from urllib.parse import urlparse
from streamlit.components.v1 import iframe

# ================== CONFIG / UI ==================
st.set_page_config(page_title="Demo Tracking - Navegador MySQL", layout="wide")
st.markdown("""
<style>
.block-container { padding-top: 0.75rem; padding-bottom: 0.25rem; }
[data-testid="stSidebar"] { min-width: 300px; width: 300px; border-right: 1px solid #eee; }
h1, h2, h3 { margin-bottom: 0.35rem !important; }
.info-card { border: 1px solid #e9e9e9; border-radius: 12px; padding: 10px 12px; background: #fafafa; margin-top: 10px; }
.actions { text-align: right; margin-bottom: 6px; }
.actions a { text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ================== SECRETS / PARAMS ==================
DB = st.secrets["mysql"]
SCHEMA  = st.secrets.get("schema", "streamlit_apps")
TABLE   = st.secrets.get("table", "links_demos")
TAG_COL = st.secrets.get("tag_col", "tag")
URL_COL = st.secrets.get("url_col", "links")
FQN     = f"`{SCHEMA}`.`{TABLE}`"

# ================== UTILS ==================
def normalize_drive_url(url: str) -> str:
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
st.markdown("### Demo de Producto — Tracking")

# Acciones (arriba del iframe)
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

# Iframe
embed_url = normalize_drive_url(selected["url"])
if open_mode == "iframe (panel principal)":
    try:
        iframe(src=embed_url, height=height, scrolling=True)
        st.caption("Si no se ve, el sitio puede bloquear el embebido (X-Frame-Options/CSP).")
    except Exception:
        st.warning("No se pudo embeber el contenido. Abrilo en nueva pestaña.")

# Info card (ahora DEBAJO del iframe)
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
