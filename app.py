import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
from io import BytesIO

# ======================================================
# CONFIG STREAMLIT (SIEMPRE PRIMERO)
# ======================================================
st.set_page_config(
    page_title="NEA DATA · Panel Fiscal",
    page_icon="📊",
    layout="wide"
)

# ======================================================
# ESTILOS DE MARCA NEA DATA
# ======================================================
st.markdown("""
<style>
body { background-color: #0E1117; }
h1, h2, h3 { color: #E5E7EB; }
.subtitulo { color: #6EE7B7; font-size: 18px; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.markdown("## 📊 **NEA DATA**")
st.sidebar.markdown("Soluciones en Ciencia de Datos y Automatización")
st.sidebar.markdown("---")

MENU = [
    "📅 Panel Fiscal",
    "🔎 Consultor de CUITs",
    "📤 Emitidos / Recibidos"
]

seccion = st.sidebar.radio(
    "Menú",
    MENU,
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("📩 neadata.contacto@gmail.com")
st.sidebar.markdown("📍 Corrientes, Argentina")

# ======================================================
# FUNCIONES GENERALES
# ======================================================
@st.cache_data
def cargar_vencimientos():
    df = pd.read_excel("data/vencimientos_anuales.xlsx")

    hoy = date.today()
    mes_actual = hoy.month
    anio = hoy.year

    df = df[df["mes"] == mes_actual].copy()

    df["fecha"] = df["dia"].apply(lambda d: date(anio, mes_actual, int(d)))
    df["dias_restantes"] = df["fecha"].apply(lambda f: (f - hoy).days)

    def estado(dias):
        if dias < 0:
            return "⚪"
        elif dias <= 1:
            return "🔴"
        elif dias <= 5:
            return "🟡"
        else:
            return "🟢"

    df["estado"] = df["dias_restantes"].apply(estado)

    df["vencimiento"] = (
        df["impuesto"] + " · " +
        df["fecha"].apply(lambda f: f.strftime("%d/%m")) +
        " " + df["estado"]
    )

    return df


def excel_bytes(df: pd.DataFrame) -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    bio.seek(0)
    return bio.getvalue()


def normalizar_col(c: str) -> str:
    return str(c).strip().upper()

# ======================================================
# SECCIÓN 1 · PANEL FISCAL
# ======================================================
if seccion == "📅 Panel Fiscal":

    st.markdown("## 📅 Vencimientos del mes")
    st.markdown("<div class='subtitulo'>Situación fiscal actual</div>", unsafe_allow_html=True)
    st.markdown("---")

    df_base = cargar_vencimientos()

    organismos_cfg = {
        "ARCA": ("ARCA", None),
        "DGR Corrientes · IIBB": ("DGR", "IIBB"),
        "ATP Chaco · IIBB": ("ATP(CHACO)", "IIBB"),
        "Tasa Municipal Corrientes": ("ACOR", "TS"),
    }

    seleccion = st.multiselect(
        "Seleccioná los organismos que aplican:",
        options=list(organismos_cfg.keys()),
        default=["ARCA", "DGR Corrientes · IIBB"]
    )

    frames = []
    for key in seleccion:
        org, imp = organismos_cfg[key]
        if imp:
            frames.append(df_base[(df_base["organismo"] == org) & (df_base["impuesto"] == imp)])
        else:
            frames.append(df_base[df_base["organismo"] == org])

    df = pd.concat(frames) if frames else df_base.iloc[0:0]

    st.markdown("---")

    st.markdown("## 📊 Resumen Ejecutivo")
    col1, col2, col3, col4 = st.columns(4)

    def count_estado(e):
        return int((df["estado"] == e).sum())

    col1.metric("🔴 Vence hoy / mañana", count_estado("🔴"))
    col2.metric("🟡 Próximos días", count_estado("🟡"))
    col3.metric("🟢 En regla", count_estado("🟢"))
    col4.metric("⚪ Cumplidos", count_estado("⚪"))

    st.markdown("### 📌 Organismos con vencimientos")

    resumen_org = (
        df.groupby("organismo")["estado"]
        .apply(lambda x:
            "🔴 Riesgo alto" if "🔴" in x.values else
            "🟡 Riesgo medio" if "🟡" in x.values else
            "🟢 En regla"
        )
        .reset_index()
        .rename(columns={"organismo": "Organismo", "estado": "Situación"})
    )

    st.dataframe(resumen_org, hide_index=True, use_container_width=True)
    st.markdown("---")

    # ======================================================
    # DETALLE DE VENCIMIENTOS POR ORGANISMO
    # ======================================================
    st.markdown("## 📅 Detalle de vencimientos")

    colA, colB = st.columns(2)
    colC, colD = st.columns(2)

    def render_detalle(titulo, filtro, col):
        with col:
            st.markdown(titulo)
            if filtro.empty:
                st.info("Sin vencimientos este mes.")
            else:
                st.dataframe(
                    filtro[["terminacion", "vencimiento"]]
                    .rename(columns={
                        "terminacion": "Terminación CUIT",
                        "vencimiento": "Vencimiento"
                    }),
                    hide_index=True,
                    use_container_width=True
                )

    if "ARCA" in seleccion:
        render_detalle(
            "### 🔵 ARCA",
            df[df["organismo"] == "ARCA"],
            colA
        )

    if "DGR Corrientes · IIBB" in seleccion:
        render_detalle(
            "### 🟢 DGR Corrientes · IIBB",
            df[
                (df["organismo"] == "DGR") &
                (df["impuesto"] == "IIBB")
            ],
            colB
        )

    if "ATP Chaco · IIBB" in seleccion:
        render_detalle(
            "### 🟠 ATP Chaco · IIBB",
            df[
                (df["organismo"] == "ATP(CHACO)") &
                (df["impuesto"] == "IIBB")
            ],
            colC
        )

    if "Tasa Municipal Corrientes" in seleccion:
        render_detalle(
            "### 🟣 Tasa Municipal · Corrientes",
            df[
                (df["organismo"] == "ACOR") &
                (df["impuesto"] == "TS")
            ],
            colD
        )

    # ======================================================
    # LEYENDA
    # ======================================================
    st.markdown("---")
    st.markdown("""
    ⚪ **Cumplido** &nbsp;&nbsp;
    🔴 **Vence hoy / mañana** &nbsp;&nbsp;
    🟡 **Próximos días** &nbsp;&nbsp;
    🟢 **En regla**
    """)


# ======================================================
# SECCIÓN 2 · CONSULTOR DE CUITs
# ======================================================
elif seccion == "🔎 Consultor de CUITs":

    from core.consultor_cuit import consultar_cuit

    st.markdown("## 🔎 Consultor de CUITs")
    st.markdown("<div class='subtitulo'>Consulta fiscal individual y masiva</div>", unsafe_allow_html=True)
    st.info("🔐 La consulta se realiza en tiempo real. No se almacena información.")
    st.markdown("---")

    tipo = st.radio(
        "Tipo de consulta",
        ["Consulta individual", "Consulta masiva (Excel)"],
        horizontal=True
    )

    if tipo == "Consulta individual":
        cuit = st.text_input("CUIT (11 dígitos)")

        if st.button("🔍 Consultar"):
            if not cuit.isdigit() or len(cuit) != 11:
                st.error("El CUIT debe tener 11 dígitos numéricos.")
            else:
                with st.spinner("Consultando ARCA..."):
                    res = consultar_cuit(cuit)
                df_res = pd.DataFrame(res.items(), columns=["Campo", "Valor"])
                st.table(df_res)

    else:
        df_tpl = pd.DataFrame({"CUIT": [""], "OBSERVACIONES": [""]})

        st.download_button(
            "⬇️ Descargar plantilla (Excel)",
            data=excel_bytes(df_tpl),
            file_name="plantilla_cuits.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        archivo = st.file_uploader("Subí un Excel con columna CUIT", type=["xlsx"])

        if archivo:
            df_in = pd.read_excel(archivo, dtype=str)

            cols_map = {normalizar_col(c): c for c in df_in.columns}
            col_cuit = cols_map.get("CUIT") or cols_map.get("CUITS")

            if not col_cuit:
                st.error("El Excel debe tener una columna 'CUIT'.")
            else:
                st.dataframe(df_in.head(50), use_container_width=True)

                if st.button("🔍 Procesar CUITs"):
                    resultados = []
                    prog = st.progress(0)
                    total = len(df_in)

                    for i, row in enumerate(df_in.to_dict(orient="records"), start=1):
                        raw = (row.get(col_cuit) or "").strip()
                        cuit_norm = "".join(ch for ch in raw if ch.isdigit())

                        if cuit_norm.isdigit() and len(cuit_norm) == 11:
                            res = consultar_cuit(cuit_norm)
                        else:
                            res = {"CUIT": raw, "Error": "CUIT inválido"}

                        resultados.append(res)
                        prog.progress(int(i * 100 / max(total, 1)))

                    df_out = pd.DataFrame(resultados)

                    st.dataframe(df_out, use_container_width=True)

                    st.download_button(
                        "📥 Descargar resultados (Excel)",
                        data=excel_bytes(df_out),
                        file_name="resultado_consulta_cuits.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

# ======================================================
# SECCIÓN 3 · EMITIDOS / RECIBIDOS
# ======================================================
elif seccion == "📤 Emitidos / Recibidos":

    st.markdown("## 📤 Envío de pedido · Emitidos / Recibidos")
    st.markdown("<div class='subtitulo'>Procesamiento controlado · hasta 24 hs hábiles</div>", unsafe_allow_html=True)
    st.markdown("---")

    st.info(
        "📨 Este formulario permite **enviar un pedido de procesamiento** a NEA DATA.\n\n"
        "El archivo será analizado y los resultados se entregarán una vez finalizado el proceso."
    )

    plantilla = Path("templates/clientes.xlsx")

    if plantilla.exists():
        with open(plantilla, "rb") as f:
            st.download_button(
                "⬇️ Descargar plantilla Excel",
                data=f,
                file_name="clientes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    archivo = st.file_uploader("Subí el Excel completo", type=["xlsx"])

    if archivo:
        try:
            # 🔍 Vista previa (esto consume el archivo)
            df_preview = pd.read_excel(archivo, dtype=str)
            st.dataframe(df_preview.head(50), use_container_width=True)

            if st.button("📨 Enviar pedido"):
                from core.mailer import enviar_pedido

                # 🔑 CLAVE: rebobinar el archivo antes de enviarlo
                archivo.seek(0)

                smtp_user = st.secrets["SMTP_USER"]
                smtp_pwd = st.secrets["SMTP_APP_PASSWORD"]
                notify_to = st.secrets["NOTIFY_TO"]

                enviar_pedido(
                    archivo=archivo,
                    smtp_user=smtp_user,
                    smtp_password=smtp_pwd,
                    notify_to=notify_to,
                )

                st.success("✅ Pedido registrado correctamente.")
                st.info("⏳ Procesamiento dentro de las próximas 24 hs hábiles.")

        except Exception:
            st.error("❌ No se pudo leer el archivo. Verificá el formato.")


# ======================================================
# FOOTER
# ======================================================
st.markdown("---")
st.markdown(
    "<small>© 2026 <b>NEA DATA</b> · Soluciones en Ciencia de Datos y Automatización · Corrientes, Argentina</small>",
    unsafe_allow_html=True
)

