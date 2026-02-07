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
    "🏦 Extractos Bancarios",
    "📤 Emitidos / Recibidos"
]


if is_admin_email and st.session_state.admin_ok:
    MENU.append("🛠 Administración")


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
# SECCIÓN 1 · GESTIÓN FISCAL
# ======================================================

if seccion == "📅 Gestión Fiscal":

    st.markdown("## 📅 Gestión fiscal por cartera")
    st.markdown(
        "Listado automático de vencimientos del mes corriente. "
        "Las fechas se obtienen directamente del calendario fiscal oficial."
    )
    st.markdown("---")

    # ======================================================
    # MODELO DE CARTERA
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

    st.info(
        "💡 Podés subir tu cartera para ver los vencimientos por cliente. "
        "Si no subís ningún archivo, abajo podés consultar el calendario fiscal completo."
    )

    # ======================================================
    # CARGA DE VENCIMIENTOS (BASE OFICIAL)
    # ======================================================
    df_venc = cargar_vencimientos()

    # ======================================================
    # CRUCE CARTERA ↔ VENCIMIENTOS (OPCIONAL)
    # ======================================================
    if archivo is not None:

        df_cartera = pd.read_excel(archivo)
        df_cartera.columns = df_cartera.columns.str.upper().str.strip()

        for col in ["ARCA", "DGR_CORRIENTES", "ATP_CHACO", "TASA_MUNICIPAL"]:
            if col in df_cartera.columns:
                df_cartera[col] = (
                    df_cartera[col]
                    .astype(str)
                    .str.upper()
                    .str.strip()
                )

        registros = []

        for _, row in df_cartera.iterrows():

            if row.get("ARCA") == "SI":
                df_org = df_venc[df_venc["organismo"] == "ARCA"]

            elif row.get("DGR_CORRIENTES") == "SI":
                df_org = df_venc[df_venc["organismo"] == "DGR"]

            elif row.get("ATP_CHACO") == "SI":
                df_org = df_venc[df_venc["organismo"] == "ATP(CHACO)"]

            elif row.get("TASA_MUNICIPAL") == "SI":
                df_org = df_venc[df_venc["impuesto"] == "TS"]

            else:
                continue

            for _, v in df_org.iterrows():
                registros.append({
                    "CUIT": row["CUIT"],
                    "RAZON_SOCIAL": row.get("RAZON_SOCIAL"),
                    "ORGANISMO": v["organismo"],
                    "IMPUESTO": v["impuesto"],
                    "TERMINACION": v["terminacion"],
                    "FECHA": v["fecha"]
                })

        df_clientes = pd.DataFrame(registros)

        if not df_clientes.empty:
            st.markdown("### 🧾 Vencimientos por cliente")
            st.dataframe(
                df_clientes.sort_values("FECHA"),
                use_container_width=True,
                hide_index=True
            )

    # ======================================================
    # CALENDARIO FISCAL DEL MES (SIEMPRE VISIBLE)
    # ======================================================
    st.markdown("---")
    st.markdown("## 📆 Calendario fiscal del mes")

    with st.expander("📂 ARCA · IVA"):
        st.dataframe(
            df_venc[df_venc["organismo"] == "ARCA"][
                ["terminacion", "impuesto", "fecha"]
            ].sort_values("fecha"),
            use_container_width=True,
            hide_index=True
        )

    with st.expander("📂 DGR Corrientes · IIBB"):
        st.dataframe(
            df_venc[df_venc["organismo"] == "DGR"][
                ["terminacion", "impuesto", "fecha"]
            ].sort_values("fecha"),
            use_container_width=True,
            hide_index=True
        )

    with st.expander("📂 ATP Chaco · IIBB"):
        st.dataframe(
            df_venc[df_venc["organismo"] == "ATP(CHACO)"][
                ["terminacion", "impuesto", "fecha"]
            ].sort_values("fecha"),
            use_container_width=True,
            hide_index=True
        )

    with st.expander("📂 Tasas Municipales"):
        st.dataframe(
            df_venc[df_venc["impuesto"] == "TS"][
                ["terminacion", "organismo", "fecha"]
            ].sort_values("fecha"),
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
# SECCIÓN 3 · EXTRACTOS BANCARIOS
# ======================================================
elif seccion == "🏦 Extractos Bancarios":

    st.markdown("## 🏦 Extractor de extractos bancarios")
    st.markdown(
        "<div class='subtitulo'>Detección automática de banco y generación de Excel</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    st.info(
        "📄 Subí un **extracto bancario en PDF**.\n\n"
        "🔍 El sistema detecta automáticamente el banco.\n"
        "📊 Se genera un Excel con los movimientos normalizados."
    )

    pdf_file = st.file_uploader(
        "📎 Subí el extracto bancario (PDF)",
        type=["pdf"]
    )

    if pdf_file is not None:

        try:
            # ✅ IMPORT CORRECTO DEL SERVICIO
            from external.extractor_bancario.service import extract_bank_statement

            with st.spinner("Procesando extracto bancario..."):

                # Leer bytes del PDF
                pdf_bytes = pdf_file.read()

                # ✅ Llamada correcta al servicio
                result = extract_bank_statement(
                    pdf_bytes=pdf_bytes,
                    filename=pdf_file.name,
                )

            # -----------------------------
            # RESULTADOS
            # -----------------------------
            st.success(
                f"🏦 Banco detectado: **{result.profile.detected_bank.upper()}**"
            )
            st.info(f"📄 Tipo de documento: {result.profile.document_type}")

            if result.transactions:
                df_tx = pd.DataFrame(result.transactions)

                st.markdown("### 📋 Movimientos detectados")
                st.dataframe(
                    df_tx,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "⬇️ Descargar extracto en Excel",
                    data=excel_bytes(df_tx),
                    file_name="extracto_bancario.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.warning("⚠️ No se detectaron movimientos en el documento.")

            # -----------------------------
            # WARNINGS
            # -----------------------------
            if result.warnings:
                st.markdown("### ⚠️ Advertencias")
                for w in result.warnings:
                    st.warning(f"{w.code} · {w.message}")

            # -----------------------------
            # TRAZA DEL PARSER
            # -----------------------------
            with st.expander("🧠 Detalle técnico del procesamiento"):
                for t in result.parser_trace:
                    st.code(t)

                st.write("Confidence score:", result.confidence_score)

        except Exception as e:
            st.error("❌ Error procesando el extracto bancario.")
            st.exception(e)


# ======================================================
# SECCIÓN 4 · EMITIDOS / RECIBIDOS
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

