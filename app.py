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
    "📅 Gestión Fiscal",
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
# SECCIÓN 1 · GESTIÓN FISCAL POR CARTERA
# ======================================================

if seccion == "📊 Gestión Fiscal":

    st.markdown("## 📊 Gestión fiscal por cartera")
    st.markdown(
        "Listado automático de vencimientos según la cartera de clientes cargada. "
        "Las fechas se obtienen directamente del calendario fiscal."
    )
    st.markdown("---")

    # ======================================================
    # MODELO EXCEL DE CARTERA
    # ======================================================

    def generar_modelo_cartera():
        df = pd.DataFrame({
            "CUIT": [],
            "RAZON_SOCIAL": [],
            "ARCA": [],
            "DGR_CORRIENTES": [],
            "ATP_CHACO": [],
            "TASA_MUNICIPAL": []
        })
        return excel_bytes(df)

    st.download_button(
        "⬇️ Descargar modelo de cartera (Excel)",
        generar_modelo_cartera(),
        file_name="modelo_cartera_fiscal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    archivo = st.file_uploader(
        "📤 Subí el Excel de cartera",
        type=["xlsx"]
    )

    if not archivo:
        st.info(
            "📂 Pasos:\n"
            "1️⃣ Descargá el modelo de cartera\n"
            "2️⃣ Indicá con SI los organismos aplicables por CUIT\n"
            "3️⃣ Subí el archivo para ver los vencimientos"
        )
        st.stop()

    # ======================================================
    # CARGA DE CARTERA
    # ======================================================

    df_cartera = pd.read_excel(archivo, dtype=str)
    df_cartera.columns = df_cartera.columns.str.upper().str.strip()

    for col in ["ARCA", "DGR_CORRIENTES", "ATP_CHACO", "TASA_MUNICIPAL"]:
        if col in df_cartera.columns:
            df_cartera[col] = df_cartera[col].fillna("").str.upper().str.strip()

    # ======================================================
    # VENCIMIENTOS BASE (EXCEL FISCAL)
    # ======================================================

    df_venc = cargar_vencimientos()

    hoy = date.today()
    df_venc["fecha"] = pd.to_datetime(
        dict(year=hoy.year, month=df_venc["mes"], day=df_venc["dia"]),
        errors="coerce"
    )
    df_venc["dias_restantes"] = (df_venc["fecha"] - pd.Timestamp(hoy)).dt.days

    # ======================================================
    # ARMADO DE VENCIMIENTOS POR CARTERA
    # ======================================================

    registros = []

    for _, cli in df_cartera.iterrows():

        cuit = cli["CUIT"]
        razon = cli.get("RAZON_SOCIAL", "")

        # ARCA
        if cli.get("ARCA") == "SI":
            for _, v in df_venc[df_venc["organismo"] == "ARCA"].iterrows():
                registros.append({
                    "CUIT": cuit,
                    "RAZON_SOCIAL": razon,
                    "ORGANISMO": "ARCA",
                    "IMPUESTO": v["impuesto"],
                    "FECHA": v["fecha"],
                    "DIAS": v["dias_restantes"],
                    "ESTADO": v["estado"]
                })

        # DGR
        if cli.get("DGR_CORRIENTES") == "SI":
            for _, v in df_venc[df_venc["organismo"] == "DGR"].iterrows():
                registros.append({
                    "CUIT": cuit,
                    "RAZON_SOCIAL": razon,
                    "ORGANISMO": "DGR Corrientes",
                    "IMPUESTO": v["impuesto"],
                    "FECHA": v["fecha"],
                    "DIAS": v["dias_restantes"],
                    "ESTADO": v["estado"]
                })

        # ATP
        if cli.get("ATP_CHACO") == "SI":
            for _, v in df_venc[df_venc["organismo"] == "ATP(CHACO)"].iterrows():
                registros.append({
                    "CUIT": cuit,
                    "RAZON_SOCIAL": razon,
                    "ORGANISMO": "ATP Chaco",
                    "IMPUESTO": v["impuesto"],
                    "FECHA": v["fecha"],
                    "DIAS": v["dias_restantes"],
                    "ESTADO": v["estado"]
                })

        # TASA
        if cli.get("TASA_MUNICIPAL") == "SI":
            for _, v in df_venc[df_venc["impuesto"] == "TS"].iterrows():
                registros.append({
                    "CUIT": cuit,
                    "RAZON_SOCIAL": razon,
                    "ORGANISMO": "Tasa Municipal",
                    "IMPUESTO": v["impuesto"],
                    "FECHA": v["fecha"],
                    "DIAS": v["dias_restantes"],
                    "ESTADO": v["estado"]
                })

    df_out = pd.DataFrame(registros)

    # ======================================================
    # VISTA PRINCIPAL
    # ======================================================

    st.markdown("### 📅 Vencimientos de la cartera (ordenados por fecha)")

    if df_out.empty:
        st.warning("No se encontraron vencimientos para la cartera cargada.")
        st.stop()

    df_out = df_out.sort_values("FECHA")

    st.dataframe(
        df_out[
            ["CUIT", "RAZON_SOCIAL", "ORGANISMO", "IMPUESTO", "FECHA", "DIAS", "ESTADO"]
        ],
        use_container_width=True,
        hide_index=True
    )

    # ======================================================
    # DETALLE POR ORGANISMO
    # ======================================================

    with st.expander("📂 Ver vencimientos por organismo y terminación"):
        st.dataframe(
            df_out.sort_values(["ORGANISMO", "FECHA"]),
            use_container_width=True,
            hide_index=True
        )


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

