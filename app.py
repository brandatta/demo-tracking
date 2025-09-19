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
DEFAULT_URL = "https://lookerstudio.google.com/reporting/1wL0OBhOAbBG8KYjJF7_V5psEHCS604dD"

# 1) Sitios web (para iframe o nueva pestaña)
SITES = {
    "App de Tracking (Georgalos)": DEFAULT_URL,
    "Página principal Brandatta": "https://www.brandatta.com.ar",
    "Demo pública de seguimiento": "https://lookerstudio.google.com/reporting/1wL0OBhOAbBG8KYjJF7_V5psEHCS604dD",
}

# 2) PDFs (reemplazá las URLs por las tuyas)
PDFS = {
    "Presentación Comercial (PDF)": "https://example.com/presentacion.pdf",
    "Ficha Técnica (PDF)": "https://example.com/ficha-tecnica.pdf",
    "Catálogo (PDF)": "https://example.com/catalogo.pdf",
}

# 3) Links con tooltip (cada uno tiene 'url' y 'help')
TOOLTIP_LINKS = {
    "Panel de Control": {
        "url": "https://example.com/dashboard",
        "help": "KPIs y métricas en tiempo real del sistema.",
    },
    "Documentación Técnica": {
        "url": "https://example.com/docs",
        "help": "Guía técnica para integraciones y API.",
    },
    "Soporte / Helpdesk": {
        "url": "https://example.com/soporte",
        "help": "Abrí tickets y revisá el estado de soporte.",
    },
}

# ================== SIDEBAR ==================
st.sidebar.title("📚 Navegador")

section = st.sidebar.radio(
    "Sección",
    ["Sitios", "PDFs", "Links con tooltip"],
    index=0
)

# Controles comunes
height = st.sidebar.slider("Altura del iframe (px)", 500, 1400, 850, 50)

# ================== LÓGICA DEL NAVEGADOR ==================
selected_label = None
selected_url = None
open_mode = "iframe (panel principal)"  # default

if section == "Sitios":
    selected_label = st.sidebar.selectbox("Enlaces disponibles", list(SITES.keys()), index=0)
    selected_url = SITES[selected_label]
    open_mode = st.sidebar.radio("Abrir enlace en:", ["iframe (panel principal)", "Nueva pestaña"], index=0)

    # Campo para pegar un enlace propio
    st.sidebar.markdown("---")
    custom_url = st.sidebar.text_input("O pegar un enlace personalizado", value=selected_url)
    selected_url = custom_url

    if open_mode == "Nueva pestaña":
        st.sidebar.markdown(f"[Abrir **{selected_label}** en nueva pestaña]({selected_url})")

elif section == "PDFs":
    selected_label = st.sidebar.selectbox("PDFs disponibles", list(PDFS.keys()), index=0)
    selected_url = PDFS[selected_label]

    # Botón para abrir el PDF en nueva pestaña
    st.sidebar.link_button(f"Abrir {selected_label}", url=selected_url, help="Abrir en nueva pestaña")

elif section == "Links con tooltip":
    # Mostramos cada link como botón con tooltip (help)
    st.sidebar.caption("Pasá el mouse por cada botón para ver el tooltip.")
    for name, meta in TOOLTIP_LINKS.items():
        st.sidebar.link_button(name, url=meta["url"], help=meta.get("help", ""))
    # Además permitimos elegir uno para embeber si querés
    st.sidebar.markdown("---")
    selected_label = st.sidebar.selectbox("Embeber uno (opcional)", list(TOOLTIP_LINKS.keys()), index=0)
    selected_url = TOOLTIP_LINKS[selected_label]["url"]

# ================== CONTENIDO PRINCIPAL ==================
st.markdown("### 🎯 Demo de Producto — Tracking")

# Botón fallback “Abrir en nueva pestaña”
if selected_url:
    st.markdown(
        f"<div style='text-align:right'><a href='{selected_url}' target='_blank'>🔗 Abrir en nueva pestaña</a></div>",
        unsafe_allow_html=True
    )

# Info card
if selected_label and selected_url:
    parsed = urlparse(selected_url)
    host = (parsed.netloc or parsed.path).split('/')[0]
    st.markdown(
        f"""
        <div class="info-card">
          <b>Recurso seleccionado:</b> {selected_label}<br>
          <b>URL:</b> <code>{selected_url}</code><br>
          <b>Host:</b> {host}
        </div>
        """,
        unsafe_allow_html=True
    )

# Render iframe:
# - Sitios: respeta "open_mode"
# - PDFs: siempre iframe (lector del navegador)
# - Links con tooltip: embeber el seleccionado en el selectbox opcional
render_iframe = (
    (section == "Sitios" and open_mode == "iframe (panel principal)") or
    (section == "PDFs") or
    (section == "Links con tooltip" and selected_url)
)

if render_iframe and selected_url:
    try:
        iframe(src=selected_url, height=height, scrolling=True)
        st.caption("Si el contenido no se ve, puede que el sitio bloquee el embebido (X-Frame-Options/CSP).")
    except Exception:
        st.warning("No se pudo embeber el contenido. Probá abrirlo en nueva pestaña.")
