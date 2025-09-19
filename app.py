import streamlit as st
from urllib.parse import urlparse
from streamlit.components.v1 import iframe

# ================== CONFIG ==================
st.set_page_config(
    page_title="Demo Tracking - Brandatta",
    layout="wide",
    page_icon="🧭",
)

# ================== ESTILOS ==================
st.markdown("""
<style>
.block-container { padding-top: 0.75rem; padding-bottom: 0.25rem; }
[data-testid="stSidebar"] {
    min-width: 280px;
    width: 280px;
    border-right: 1px solid #eee;
}
h1, h2, h3 { margin-bottom: 0.35rem !important; }
.info-card {
    border: 1px solid #e9e9e9;
    border-radius: 12px;
    padding: 10px 12px;
    background: #fafafa;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ================== DATOS ==================
DEFAULT_URL = "https://tracking.georgalosproduccion.com"
LINKS = {
    "App de Tracking (Georgalos)": DEFAULT_URL,
    "Página principal Brandatta": "https://www.brandatta.com.ar",
    "Demo pública de seguimiento": "https://tracking.demobrandatta.net",
}

# ================== SIDEBAR ==================
st.sidebar.title("📚 Navegador")
choice = st.sidebar.selectbox("Enlaces disponibles", list(LINKS.keys()), index=0)
selected_url = LINKS[choice]

open_mode = st.sidebar.radio("Abrir enlace en:", ["iframe (panel principal)", "Nueva pestaña"], index=0)
height = st.sidebar.slider("Altura del iframe (px)", 500, 1400, 850, 50)

custom_url = st.sidebar.text_input("O pegar un enlace personalizado", value=selected_url)

if open_mode == "Nueva pestaña":
    st.sidebar.markdown(f"[Abrir **{choice}** en nueva pestaña]({custom_url})")

# ================== MAIN ==================
st.markdown("### 🎯 Demo de Producto — Tracking")
st.markdown(f"<div style='text-align:right'><a href='{custom_url}' target='_blank'>🔗 Abrir en nueva pestaña</a></div>", unsafe_allow_html=True)

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

if open_mode == "iframe (panel principal)":
    try:
        iframe(src=custom_url, height=height, scrolling=True)
        st.caption("Si el contenido no se ve, puede que el sitio bloquee el embebido.")
    except Exception:
        st.warning("No se pudo embeber el sitio. Probá abrirlo en nueva pestaña.")
