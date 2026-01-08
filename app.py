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
# SECCIÓN 1 · PANEL FISCAL (VISTA EJECUTIVA + CARTERA)
# ======================================================
if seccion == "📅 Panel Fiscal":

    st.markdown("## 📅 Panel Fiscal · Vencimientos del mes")
    st.markdown(
        "<div class='subtitulo'>Situación fiscal actual · vista ejecutiva</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ==================================================
    # ORGANISMOS INCLUIDOS
    # ==================================================
    st.markdown("### 🏛️ Organismos incluidos en el análisis")

    organismos_disponibles = [
        "ARCA",
        "DGR Corrientes · IIBB",
        "ATP Chaco · IIBB",
        "Tasa Municipal"
    ]

    seleccion = st.multiselect(
        "Seleccioná los organismos relevantes:",
        options=organismos_disponibles,
        default=["ARCA", "DGR Corrientes · IIBB"]
    )

    st.markdown("---")

    # ==================================================
    # ALERTAS (placeholder lógico, sin vencimientos aún)
    # ==================================================
    st.markdown("## 🚨 Alertas del mes")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🔴 Vence hoy / mañana", 0)
    col2.metric("🟡 Próximos días", 0)
    col3.metric("🟢 En regla", 8)
    col4.metric("⚪ Cumplidos", 0)

    st.markdown("---")

    # ==================================================
    # ORDEN DE TRABAJO
    # ==================================================
    st.markdown("## 🧠 Orden de trabajo sugerido")

    st.info(
        "1️⃣ **ARCA** — siempre priorizar, independientemente de la fecha.\n\n"
        "2️⃣ **Ingresos Brutos** — se devengan a partir de la información fiscal base.\n\n"
        "3️⃣ **Tasas municipales** — última etapa del proceso.\n\n"
        "_Este panel está diseñado para organizar el trabajo diario del estudio._"
    )

    st.markdown("---")

    # ==================================================
    # ESTADO GENERAL POR ORGANISMO
    # ==================================================
    st.markdown("## 📌 Estado general por organismo")

    df_estado = pd.DataFrame({
        "Organismo": ["ARCA", "DGR"],
        "Situación": ["🟢 En regla", "🟢 En regla"]
    })

    st.dataframe(df_estado, hide_index=True, use_container_width=True)

    st.markdown("---")

    # ==================================================
    # CONFIDENCIALIDAD
    # ==================================================
    st.markdown("## 🔐 Confidencialidad de la información")

    st.warning(
        "Las claves fiscales y datos sensibles se utilizan **exclusivamente** "
        "para el procesamiento solicitado.\n\n"
        "**NEA DATA no almacena credenciales ni información fiscal de los clientes.**"
    )

    st.markdown("---")

    # ==================================================
    # EJEMPLO VISUAL DE CARTERA (NO DESCARGABLE)
    # ==================================================
    st.markdown("## 📄 Ejemplo de estructura de cartera")

    df_ejemplo = pd.DataFrame({
        "CUIT": ["30-70888534-9", "27-12345678-6"],
        "RAZON_SOCIAL": ["Empresa Ejemplo SA", "Cliente Prueba"],
        "ARCA": ["SI", "SI"],
        "DGR_CORRIENTES": ["SI", "NO"],
        "ATP_CHACO": ["NO", "NO"],
        "TASA_MUNICIPAL": ["SI", "NO"],
    })

    st.caption("Ejemplo ilustrativo. La estructura debe respetarse para el análisis.")
    st.dataframe(df_ejemplo, hide_index=True, use_container_width=True)

    st.markdown("---")

    # ==================================================
    # CARGA DE CARTERA REAL
    # ==================================================
    st.markdown("## 📤 Cargar cartera de clientes")

    archivo_cartera = st.file_uploader(
        "Subí el Excel con tu cartera de clientes",
        type=["xlsx"]
    )

    if archivo_cartera:
        try:
            df_cartera = pd.read_excel(archivo_cartera, dtype=str)
            df_cartera.columns = [c.strip().upper() for c in df_cartera.columns]

            st.success("✅ Cartera cargada correctamente")
            st.dataframe(df_cartera.head(20), use_container_width=True)

            # Normalizar SI / NO
            for col in ["ARCA", "DGR_CORRIENTES", "ATP_CHACO", "TASA_MUNICIPAL"]:
                if col in df_cartera.columns:
                    df_cartera[col] = (
                        df_cartera[col]
                        .fillna("NO")
                        .str.upper()
                        .str.strip()
                    )

            st.markdown("### 📊 Resumen automático por organismo")

            resumen = {
                "ARCA": int((df_cartera.get("ARCA") == "SI").sum()),
                "DGR Corrientes": int((df_cartera.get("DGR_CORRIENTES") == "SI").sum()),
                "ATP Chaco": int((df_cartera.get("ATP_CHACO") == "SI").sum()),
                "Tasa Municipal": int((df_cartera.get("TASA_MUNICIPAL") == "SI").sum()),
            }

            df_resumen = pd.DataFrame(
                resumen.items(),
                columns=["Organismo", "CUITs involucrados"]
            )

            st.dataframe(df_resumen, hide_index=True, use_container_width=True)

            st.info(
                "Este resumen permite **priorizar tareas** y organizar el trabajo "
                "por organismo, incluso sin sistema de login."
            )

        except Exception as e:
            st.error("❌ Error procesando el archivo de cartera")
            st.exception(e)



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
    st.markdown(
        "<div class='subtitulo'>Procesamiento controlado · hasta 24 hs hábiles</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # --------------------------------------------------
    # INFORMACIÓN GENERAL + SEGURIDAD
    # --------------------------------------------------
    st.info(
        "📨 Este formulario permite **enviar un pedido de procesamiento fiscal** a NEA DATA.\n\n"
        "🔐 La información proporcionada se utiliza **exclusivamente** para el procesamiento solicitado.\n"
        "❗ **No almacenamos claves fiscales ni credenciales** de los contribuyentes.\n"
        "📬 Los resultados se enviarán **únicamente** al correo electrónico indicado."
    )

    # --------------------------------------------------
    # EJEMPLO VISUAL DEL EXCEL 
    # --------------------------------------------------
    with st.expander("📘 Ver ejemplo de cómo debe completarse el Excel", expanded=False):

        df_ejemplo = pd.DataFrame(
            [
                {
                    "CUIT": "30703088534",
                    "CLAVE": "CLAVE_FISCAL",
                    "NOMBRE / RAZÓN SOCIAL": "EMPRESA EJEMPLO SA",
                    "EMITIDOS": "SI",
                    "RECIBIDOS": "NO",
                    "DESDE": "01-2024",
                    "HASTA": "12-2024",
                }
            ]
        )

        st.dataframe(df_ejemplo, use_container_width=True)

        st.markdown(
            """
**Indicaciones para completar el archivo:**
- **CUIT**: 11 dígitos, sin guiones ni espacios.
- **CLAVE**: clave fiscal vigente del contribuyente.
- **EMITIDOS / RECIBIDOS**: valores permitidos → `SI` / `NO`.
- **DESDE / HASTA**: período en formato `MM-AAAA`.

⚠️ Las credenciales se utilizan únicamente durante la ejecución del proceso
y no se almacenan ni reutilizan.
"""
        )

    # --------------------------------------------------
    # DESCARGA PLANTILLA BASE
    # --------------------------------------------------
    plantilla = Path("templates/clientes.xlsx")

    if plantilla.exists():
        with open(plantilla, "rb") as f:
            st.download_button(
                "⬇️ Descargar plantilla base",
                data=f,
                file_name="clientes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    st.markdown("---")

    # --------------------------------------------------
    # CORREO DESTINO RESULTADOS
    # --------------------------------------------------
    email_resultados = st.text_input(
        "📧 Correo para enviar los resultados del procesamiento",
        placeholder="ejemplo@empresa.com.ar"
    )

    # --------------------------------------------------
    # SUBIDA DEL EXCEL
    # --------------------------------------------------
    archivo = st.file_uploader("📎 Subí el Excel completo", type=["xlsx"])

    if archivo:
        # Vista previa
        try:
            df_preview = pd.read_excel(archivo, dtype=str)
            st.markdown("### 👁️ Vista previa del archivo")
            st.dataframe(df_preview.head(50), use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error leyendo el Excel: {e}")
            st.stop()

        # --------------------------------------------------
        # ENVÍO DEL PEDIDO
        # --------------------------------------------------
        if st.button("📨 Enviar pedido"):
            if not email_resultados or "@" not in email_resultados:
                st.error("❌ Ingresá un correo válido para enviar los resultados.")
                st.stop()

            try:
                from core.mailer import enviar_pedido

                # rebobinar archivo
                archivo.seek(0)

                mail_cfg = st.secrets

                enviar_pedido(
                    archivo=archivo,
                    smtp_user=mail_cfg["SMTP_USER"],
                    smtp_password=mail_cfg["SMTP_APP_PASSWORD"],
                    notify_to=email_resultados,
                )

                st.success("✅ Pedido registrado correctamente.")
                st.info("⏳ Procesamiento dentro de las próximas 24 hs hábiles.")

            except Exception as e:
                st.error("❌ Error al enviar el pedido.")
                st.exception(e)



# ======================================================
# FOOTER
# ======================================================
st.markdown("---")
st.markdown(
    "<small>© 2026 <b>NEA DATA</b> · Soluciones en Ciencia de Datos y Automatización · Corrientes, Argentina</small>",
    unsafe_allow_html=True
)

