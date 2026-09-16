"""
Dashboard: vista "mis leads de hoy" por asesor, filtrada por empresa
(una comercializadora no ve los leads de otra).
"""
import sqlite3
from pathlib import Path
 
import pandas as pd
import streamlit as st
 
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "priorizador.db"
 
st.set_page_config(page_title="Priorizador de Leads", page_icon="◆", layout="wide")
 
TEMP_LABEL = {"Caliente": "Alta prioridad", "Tibio": "Prioridad media", "Frío": "Baja prioridad"}
TEMP_ACCENT = {"Caliente": "#C0392B", "Tibio": "#B7791F", "Frío": "#5A6B7D"}
 
# ---------------------------------------------------------------- estilo --
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
 
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
 
:root {
    --navy: #101A2B;
    --navy-light: #1B2A45;
    --slate: #5A6B7D;
    --border: #E3E7ED;
    --bg: #F7F8FA;
}
 
[data-testid="stAppViewContainer"] { background-color: var(--bg); }
[data-testid="stSidebar"] { background-color: var(--navy); }
[data-testid="stSidebar"] label { color: #E7ECF3 !important; font-weight: 500; font-size: 0.85rem; letter-spacing: 0.02em; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] span { color: #B8C4D6 !important; }
[data-testid="stSidebar"] .streamlit-expanderHeader { color: #E7ECF3 !important; }
 
h1 {
    font-weight: 700 !important;
    color: var(--navy) !important;
    letter-spacing: -0.02em;
    border-bottom: 3px solid var(--navy);
    padding-bottom: 0.6rem;
}
h2, h3 { color: var(--navy) !important; font-weight: 600 !important; }
 
.kpi-row { display: flex; gap: 1rem; margin: 1.2rem 0 1.6rem 0; }
.kpi-card {
    flex: 1;
    background: white;
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 6px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 3px rgba(16,26,43,0.06);
}
.kpi-card .kpi-label {
    font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--slate); font-weight: 600;
}
.kpi-card .kpi-value {
    font-size: 2.1rem; font-weight: 700; color: var(--navy); line-height: 1.2;
}
.kpi-card .kpi-sub { font-size: 0.8rem; color: var(--slate); }
 
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)
 
 
def kpi_card(label, valor, color, sub=""):
    return (
        f'<div class="kpi-card" style="--accent:{color}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{valor}</div>'
        f'<div class="kpi-sub">{sub}</div>'
        f'</div>'
    )
 
 
@st.cache_data(ttl=60)
def cargar_empresas():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT empresa_id, nombre FROM empresas", conn)
 
 
@st.cache_data(ttl=60)
def cargar_asesores(empresa_id):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT asesor_id, nombre, punto_venta_id FROM asesores "
            "WHERE empresa_id = ? AND activo = 'SI' ORDER BY nombre",
            conn, params=(empresa_id,)
        )
 
 
@st.cache_data(ttl=60)
def cargar_leads_del_asesor(asesor_id):
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT s.score, s.temperatura, l.nombre_cliente, l.telefono_normalizado AS telefono,
                   l.ciudad, l.modelo_interes_texto AS modelo_declarado,
                   e.modelo_interes_ia, e.presupuesto_cuota, e.forma_pago,
                   e.intencion, e.objecion_principal, e.pidio_cita, l.estado_gestion
            FROM asignaciones a
            JOIN leads l ON a.lead_id = l.lead_id
            JOIN scores s ON l.lead_id = s.lead_id
            LEFT JOIN extracciones_ia e ON l.lead_id = e.lead_id
            WHERE a.asesor_id = ?
            ORDER BY s.score DESC
            """,
            conn, params=(asesor_id,)
        )
    if len(df):
        df["temperatura"] = df["temperatura"].map(lambda t: TEMP_LABEL.get(t, t))
    return df
 
 
@st.cache_data(ttl=60)
def resumen_por_empresa(empresa_id):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            """
            SELECT s.temperatura, COUNT(*) as cantidad
            FROM leads l JOIN scores s ON l.lead_id = s.lead_id
            WHERE l.empresa_id = ?
            GROUP BY s.temperatura
            """,
            conn, params=(empresa_id,)
        )
 
 
st.title("Priorizador de Leads")
 
if not DB_PATH.exists():
    st.warning(
        "Todavia no existe la base de datos. Corre primero: "
        "`python -m src.pipeline`"
    )
    st.stop()
 
empresas = cargar_empresas()
empresa_sel = st.sidebar.selectbox(
    "COMERCIALIZADORA",
    empresas["empresa_id"],
    format_func=lambda eid: empresas.set_index("empresa_id").loc[eid, "nombre"],
)
st.sidebar.caption("Cada comercializadora solo ve sus propios leads y asesores.")
 
with st.sidebar.expander("Criterio de priorización"):
    st.markdown(
        "**Alta prioridad** (score ≥ 70): alta probabilidad de compra, llamar ya.\n\n"
        "**Prioridad media** (40-69): vale la pena, no es urgencia máxima.\n\n"
        "**Baja prioridad** (< 40): baja probabilidad (a menudo por antigüedad sin gestionar)."
    )
 
resumen = resumen_por_empresa(empresa_sel)
tarjetas = ""
for temp in ["Caliente", "Tibio", "Frío"]:
    fila = resumen[resumen["temperatura"] == temp]
    valor = int(fila["cantidad"].iloc[0]) if len(fila) else 0
    tarjetas += kpi_card(TEMP_LABEL[temp], valor, TEMP_ACCENT[temp])
st.markdown(f'<div class="kpi-row">{tarjetas}</div>', unsafe_allow_html=True)
 
asesores = cargar_asesores(empresa_sel)
if asesores.empty:
    st.info("No hay asesores activos para esta comercializadora.")
    st.stop()
 
asesor_sel = st.sidebar.selectbox(
    "ASESOR",
    asesores["asesor_id"],
    format_func=lambda aid: asesores.set_index("asesor_id").loc[aid, "nombre"],
)
 
st.subheader(f"Leads de hoy — {asesores.set_index('asesor_id').loc[asesor_sel, 'nombre']}")
 
leads = cargar_leads_del_asesor(asesor_sel)
if leads.empty:
    st.info("Este asesor no tiene leads asignados hoy.")
else:
    st.dataframe(
        leads,
        use_container_width=True,
        hide_index=True,
        column_config={
            "score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%.0f"
            ),
            "temperatura": "Prioridad",
            "nombre_cliente": "Cliente",
            "telefono": "Teléfono",
            "modelo_declarado": "Modelo (declarado)",
            "modelo_interes_ia": "Modelo (IA)",
            "presupuesto_cuota": "Presupuesto/cuota",
            "forma_pago": "Forma de pago",
            "intencion": "Intención",
            "objecion_principal": "Objeción",
            "pidio_cita": "¿Pidió cita?",
            "estado_gestion": "Estado",
        },
    )
 