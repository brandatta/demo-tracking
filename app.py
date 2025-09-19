import streamlit as st
import mysql.connector
from mysql.connector import Error
from streamlit.components.v1 import iframe
from urllib.parse import urlparse

# ============== CONFIG ==============
st.set_page_config(page_title="Demo Tracking - Navegador MySQL", layout="wide", page_icon="🧭")

st.markdown("""
<style>
.block-container { padding-top: 0.75rem; padding-bottom: 0.25rem; }
[data-testid="stSidebar"] { min-width: 300px; width: 300px; border-right: 1px solid #eee; }
h1, h2, h3 { margin-bottom: 0.35rem !important; }
.info-card { border: 1px solid #e9e9e9; border-radius: 12px; padding: 10px 12px; background: #fafafa; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# ============== PARAMS ==============
# Nombre de tabla y columnas en tu DB.
TABLE_NAME = st.secrets.get("table_name", "nav_links")
COL_TAG = st.secrets.get("col_tag", "tags")
COL_URL = st.secrets.get("col_url", "links")
COL_ACTIVE = st.secrets.get("col_active", "active")  # opcional, si no existe ignora

# ============== DB ==============
def get_connection():
    cfg = st.secrets["mysql"]
    return mysql.connector.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=cfg.get("port", 3306)
    )

@st.cache_data(ttl=60)
def load_nav_items():
    """
    Devuelve lista de dicts: [{'tag': ..., 'url': ...}, ...]
    Filtra por active=1 si existe la columna.
    """
    rows = []
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Intentamos detectar si existe columna 'active' para filtrar
        has_active = False
        cur.execute(f"SHOW COLUMNS FROM `{TABLE_NAME}` LIKE %s", (COL_ACTIVE,))
        if cur.fetchone():
            has_active = True

        base_sql = f"SELECT `{COL_TAG}`, `{COL_URL}` FROM `{TABLE_NAME}`"
        if has_active:
            base_sql += f" WHERE `{COL_ACTIVE}` = 1"

        # Opcional: si tenés una columna 'sort' podés ordenar por ahí
        try:
            cur.execute(f"SHOW COLUMNS FROM `{TABLE_NAME}` LIKE 'sort'")
            if cur.fetchone():
                base_sql += " ORDER BY `sort`, 1"
        except:
            pass

        cur.execute(base_sql)
        for tag, url in cur.fetchall():
            if tag and url:
                rows.append({"tag": str(tag), "url": str(url)})
    except Error as e:
        st.error(f"Error al leer la tabla `{TABLE_NAME}`: {e}")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    return rows

items = load_nav_items()

# ============== SIDEBAR ==============
st.sidebar.title("📚 Navegador (desde MySQL)")
if not items:
    st.sidebar.warning("No se encontraron ítems. Verificá la tabla/columnas y los filtros.")
    st.stop()

tags = [i["tag"] for i in items]
default_index = 0

choice = st.sidebar.selectbox("Enlaces disponibles", tags, index=default_index)
selected = next(i for i in items if i["tag"] == choice)

# Controles
height = st.sidebar.slider("Altura del iframe (px)", 500, 1400, 850, 50)
open_mode = st.sidebar.radio("Abrir enlace en:", ["iframe (panel principal)", "Nueva pestaña"], index=0)

st.sidebar.markdown("---")
custom_url = st.sidebar.text_input("O pegar un enlace personalizado", value=selected["url"])

if open_mode == "Nueva pestaña":
    st.sidebar.markdown(f"[Abrir **{choice}** en nueva pestaña]({custom_url})")

# ============== MAIN ==============
st.markdown("### 🎯 Demo de Producto — Tracking")

# Botón fallback
st.markdown(
    f"<div style='text-align:right'><a href='{custom_url}' target='_blank'>🔗 Abrir en nueva pestaña</a></div>",
    unsafe_allow_html=True
)

# Tarjeta informativa
parsed = urlparse(custom_url)
host = (parsed.netloc or parsed.path).split('/')[0]
st.markdown(
    f"""
    <div class="info-card">
      <b>Recurso seleccionado:</b> {choice}<br>
      <b>URL:</b> <code>{custom_url}</code><br>
      <b>Host:</b> {host}
    </div>
    """,
    unsafe_allow_html=True
)

# Render iframe
if open_mode == "iframe (panel principal)":
    try:
        iframe(src=custom_url, height=height, scrolling=True)
        st.caption("Si no se ve, el sitio podría bloquear el embebido (X-Frame-Options/CSP). Usá el botón para abrir en nueva pestaña.")
    except Exception:
        st.warning("No se pudo embeber el contenido. Abrilo en nueva pestaña.")
