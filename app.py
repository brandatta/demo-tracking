import streamlit as st
import mysql.connector
from mysql.connector import Error
from urllib.parse import urlparse
from streamlit.components.v1 import iframe

# ================== CONFIG / UI ==================
st.set_page_config(page_title="Demo Tracking - Navegador MySQL", layout="wide", page_icon="🧭")
st.markdown("""
<style>
.block-container { padding-top: 0.75rem; padding-bottom: 0.25rem; }
[data-testid="stSidebar"] { min-width: 300px; width: 300px; border-right: 1px solid #eee; }
h1, h2, h3 { margin-bottom: 0.35rem !important; }
.info-card { border: 1px solid #e9e9e9; border-radius: 12px; padding: 10px 12px; background: #fafafa; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# ================== SECRETS ==================
DB = st.secrets["mysql"]

# Permite override desde secrets si querés cambiar nombres sin tocar el código
SCHEMA = st.secrets.get("schema", "streamlit_apps")
TABLE  = st.secrets.get("table", "links_demos")
TAG_COL = st.secrets.get("tag_col", "tag")
URL_COL = st.secrets.get("url_col", "links")

FQN = f"`{SCHEMA}`.`{TABLE}`"  # fully qualified name schema.tabla

# ================== DB ==================
def get_connection():
    return mysql.connector.connect(
        host=DB["host"],
        user=DB["user"],
        password=DB["password"],
        database=DB.get("database", SCHEMA),  # por si tu usuario requiere seleccionar DB
        port=DB.get("port", 3306),
        autocommit=True,
    )

@st.cache_data(ttl=60)
def load_nav_items():
    """Devuelve [{'tag':..., 'url':...}] desde streamlit_apps.links_demos"""
    rows = []
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        sql = f"SELECT `{TAG_COL}`, `{URL_COL}` FROM {FQN} ORDER BY `{TAG_COL}`"
        cur.execute(sql)
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

items = load_nav_items()

# ================== SIDEBAR ==================
st.sidebar.title("📚 Navegador (MySQL)")
if not items:
    st.sidebar.warning(f"No se encontraron ítems en {FQN}.")
    st.stop()

height = st.sidebar.slider("Altura del iframe (px)", 500, 1400, 850, 50)

choices = [i["tag"] for i in items]
choice = st.sidebar.selectbox("Enlaces disponibles", choices, index=0)
selected = next(i for i in items if i["tag"] == choice)

open_mode = st.sidebar.radio("Abrir enlace en:", ["iframe (panel principal)", "Nueva pestaña"], index=0)

st.sidebar.markdown("---")
custom_url = st.sidebar.text_input("O pegar un enlace personalizado", value=selected["url"])
if open_mode == "Nueva pestaña":
    st.sidebar.markdown(f"[Abrir **{choice}** en nueva pestaña]({custom_url})")

# ================== MAIN ==================
st.markdown("### 🎯 Demo de Producto — Tracking")
st.markdown(
    f"<div style='text-align:right'><a href='{custom_url}' target='_blank'>🔗 Abrir en nueva pestaña</a></div>",
    unsafe_allow_html=True
)

parsed = urlparse(custom_url)
host = (parsed.netloc or parsed.path).split('/')[0]
st.markdown(
    f"""
    <div class="info-card">
      <b>Item seleccionado:</b> {choice}<br>
      <b>URL:</b> <code>{custom_url}</code><br>
      <b>Host:</b> {host}
    </div>
    """,
    unsafe_allow_html=True
)

if open_mode == "iframe (panel principal)":
    try:
        iframe(src=custom_url, height=height, scrolling=True)
        st.caption("Si no se ve, el sitio puede bloquear el embebido (X-Frame-Options/CSP).")
    except Exception:
        st.warning("No se pudo embeber el contenido. Abrilo en nueva pestaña.")
