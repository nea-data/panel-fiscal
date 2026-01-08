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
# SECCIÓN 1 · PANEL FISCAL (con Cartera)
# ======================================================
if seccion == "📅 Panel Fiscal":

    st.markdown("## 📅 Panel Fiscal")
    st.markdown("<div class='subtitulo'>Gestión por cartera · estudios contables</div>", unsafe_allow_html=True)
    st.markdown("---")

    # ======================================================
    # CARGA BASE VENCIMIENTOS DEL MES (EXCEL)
    # ======================================================
    df_base = cargar_vencimientos()

    # ======================================================
    # PASO 0 · CARTERA (MODELO + CARGA)
    # ======================================================
    st.markdown("### 📥 Paso 0 · Cartera de clientes (Excel)")
    st.caption(
        "Descargá el modelo, completalo con tus CUITs y marcá qué obligaciones aplica para cada cliente. "
        "Luego subilo para generar el resumen del mes."
    )

    # Modelo de cartera (descarga)
    df_modelo_cartera = pd.DataFrame({
        "CUIT": ["20301234567", "27223334445"],
        "RAZON_SOCIAL (opcional)": ["Cliente Ejemplo SA", "Juan Pérez"],
        "ARCA": ["SI", "SI"],           # IVA / Libros / DDJJ ARCA
        "DGR_IIBB": ["SI", "NO"],       # DGR Corrientes IIBB
        "ATP_IIBB": ["NO", "SI"],       # ATP Chaco IIBB
        "TS_MUN": ["NO", "NO"],         # Tasa Municipal
        "OBSERVACIONES": ["Responsable Inscripto", "Monotributo"]
    })

    st.download_button(
        "⬇️ Descargar modelo de cartera (Excel)",
        data=excel_bytes(df_modelo_cartera),
        file_name="modelo_cartera_clientes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    cartera_file = st.file_uploader(
        "📤 Subí tu cartera (Excel)",
        type=["xlsx"],
        help="Debe incluir una columna CUIT y columnas de obligaciones (ARCA, DGR_IIBB, ATP_IIBB, TS_MUN)."
    )

    st.markdown("---")

    # ======================================================
    # TEXTOS + ADVERTENCIAS (más formal)
    # ======================================================
    st.info(
        "🔒 **Confidencialidad y uso de credenciales**\n\n"
        "- Las credenciales y/o claves que puedas utilizar en procesos externos **son responsabilidad del usuario**.\n"
        "- NEA DATA **no almacena** claves ni credenciales de clientes.\n"
        "- Los datos cargados se utilizan **únicamente para el procesamiento solicitado** y para generar el resumen."
    )

    # ======================================================
    # SI NO HAY CARTERA, MOSTRAR VISTA GENERAL (TODOS LOS ORGANISMOS)
    # ======================================================
    if not cartera_file:
        st.markdown("### 👀 Vista general del mes (sin cartera)")
        st.caption("Esta vista muestra vencimientos generales del mes. Para un resumen por clientes, cargá la cartera.")

        # Resumen ejecutivo general
        st.markdown("#### 📊 Resumen Ejecutivo (General)")
        col1, col2, col3, col4 = st.columns(4)

        def _count_estado(df_, e):
            if df_.empty:
                return 0
            return int((df_["estado"] == e).sum())

        col1.metric("🔴 Vence hoy / mañana", _count_estado(df_base, "🔴"))
        col2.metric("🟡 Próximos días", _count_estado(df_base, "🟡"))
        col3.metric("🟢 En regla", _count_estado(df_base, "🟢"))
        col4.metric("⚪ Cumplidos", _count_estado(df_base, "⚪"))

        st.markdown("---")

        # Desplegables por organismo
        st.markdown("#### 📌 Vencimientos por organismo (desplegable)")

        def _tabla_detalle(df_filtro: pd.DataFrame):
            if df_filtro.empty:
                st.info("Sin vencimientos este mes.")
                return
            st.dataframe(
                df_filtro[["terminacion", "vencimiento"]].rename(columns={
                    "terminacion": "Terminación CUIT",
                    "vencimiento": "Vencimiento"
                }),
                hide_index=True,
                use_container_width=True
            )

        with st.expander("🔵 ARCA", expanded=False):
            _tabla_detalle(df_base[df_base["organismo"] == "ARCA"])

        with st.expander("🟢 DGR Corrientes · IIBB", expanded=False):
            _tabla_detalle(df_base[(df_base["organismo"] == "DGR") & (df_base["impuesto"] == "IIBB")])

        with st.expander("🟠 ATP Chaco · IIBB", expanded=False):
            _tabla_detalle(df_base[(df_base["organismo"] == "ATP(CHACO)") & (df_base["impuesto"] == "IIBB")])

        with st.expander("🟣 Tasa Municipal · Corrientes", expanded=False):
            _tabla_detalle(df_base[(df_base["organismo"] == "ACOR") & (df_base["impuesto"] == "TS")])

        st.markdown("---")
        st.markdown("""
        ⚪ **Cumplido** &nbsp;&nbsp; 🔴 **Vence hoy / mañana** &nbsp;&nbsp; 🟡 **Próximos días** &nbsp;&nbsp; 🟢 **En regla**
        """)
        # Cortamos acá si no hay cartera
        st.stop()

    # ======================================================
    # SI HAY CARTERA: PROCESAR (PASO 1+)
    # ======================================================
    try:
        df_cartera = pd.read_excel(cartera_file, dtype=str).fillna("")
    except Exception as e:
        st.error(f"❌ No pude leer la cartera: {e}")
        st.stop()

    # Normalizar columnas
    df_cartera.columns = [normalizar_col(c) for c in df_cartera.columns]

    # Validaciones mínimas
    if "CUIT" not in df_cartera.columns:
        st.error("❌ La cartera debe tener la columna **CUIT**.")
        st.stop()

    # Helpers de flags
    def _norm_flag(x: str) -> bool:
        x = str(x).strip().upper()
        return x in ("SI", "S", "TRUE", "1", "X", "OK")

    # Columnas esperadas (si no están, las creamos en blanco)
    for col in ("ARCA", "DGR_IIBB", "ATP_IIBB", "TS_MUN"):
        if col not in df_cartera.columns:
            df_cartera[col] = ""

    # Normalizar CUIT y marcar flags
    df_cartera["CUIT"] = df_cartera["CUIT"].astype(str).str.replace(r"\D", "", regex=True)
    df_cartera["ARCA_FLAG"] = df_cartera["ARCA"].apply(_norm_flag)
    df_cartera["DGR_FLAG"] = df_cartera["DGR_IIBB"].apply(_norm_flag)
    df_cartera["ATP_FLAG"] = df_cartera["ATP_IIBB"].apply(_norm_flag)
    df_cartera["TS_FLAG"] = df_cartera["TS_MUN"].apply(_norm_flag)

    # Filtrar CUITs válidos
    df_cartera["CUIT_VALIDO"] = df_cartera["CUIT"].apply(lambda x: x.isdigit() and len(x) == 11)
    invalidos = df_cartera[~df_cartera["CUIT_VALIDO"]].copy()

    if not invalidos.empty:
        st.warning("⚠️ Se detectaron CUITs inválidos en la cartera (no se incluirán en el resumen).")
        st.dataframe(invalidos[["CUIT"]].head(50), use_container_width=True)

    df_cartera = df_cartera[df_cartera["CUIT_VALIDO"]].copy()

    if df_cartera.empty:
        st.error("❌ No quedaron CUITs válidos para procesar.")
        st.stop()

    st.markdown("### ✅ Cartera cargada")
    st.caption("Vista previa (primeras filas)")
    st.dataframe(df_cartera.head(50), use_container_width=True)
    st.markdown("---")

    # ======================================================
    # PASO 1 · RESUMEN EJECUTIVO POR CARTERA
    # ======================================================
    st.markdown("### 📊 Paso 1 · Resumen ejecutivo (por cartera)")

    total_cuits = df_cartera["CUIT"].nunique()
    cuits_arca = int(df_cartera["ARCA_FLAG"].sum())
    cuits_dgr = int(df_cartera["DGR_FLAG"].sum())
    cuits_atp = int(df_cartera["ATP_FLAG"].sum())
    cuits_ts = int(df_cartera["TS_FLAG"].sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 CUITs en cartera", total_cuits)
    c2.metric("🔵 ARCA", cuits_arca)
    c3.metric("🟢 DGR IIBB", cuits_dgr)
    c4.metric("🟠 ATP IIBB", cuits_atp)
    c5.metric("🟣 TS Mun", cuits_ts)

    st.markdown("---")

    # ======================================================
    # PASO 2 · ORDEN DE TRABAJO (prioridad)
    # ======================================================
    st.markdown("### 🧠 Paso 2 · Orden de trabajo sugerido")
    st.caption("Regla general: se prioriza ARCA porque desde Libros IVA se devengan IIBB / tasas.")
    st.markdown(
        "- **1) ARCA** → Libros IVA / IVA / base de devengamiento\n"
        "- **2) IIBB** → DGR / ATP según corresponda\n"
        "- **3) Tasas municipales** → TS / otras"
    )

    st.markdown("---")

    # ======================================================
    # PASO 3 · GENERAR VENCIMIENTOS APLICABLES POR CARTERA
    # ======================================================
    # Tomamos terminación de CUIT (último dígito)
    df_cartera["TERMINACION"] = df_cartera["CUIT"].str[-1]

    # Base por organismo
    v_arca = df_base[df_base["organismo"] == "ARCA"].copy()
    v_dgr  = df_base[(df_base["organismo"] == "DGR") & (df_base["impuesto"] == "IIBB")].copy()
    v_atp  = df_base[(df_base["organismo"] == "ATP(CHACO)") & (df_base["impuesto"] == "IIBB")].copy()
    v_ts   = df_base[(df_base["organismo"] == "ACOR") & (df_base["impuesto"] == "TS")].copy()

    # Función: merge por terminación para construir tabla de vencimientos por cliente+organismo
    def _venc_por_flag(df_cli: pd.DataFrame, flag_col: str, df_venc: pd.DataFrame, label_org: str) -> pd.DataFrame:
        base_cli = df_cli[df_cli[flag_col]].copy()
        if base_cli.empty or df_venc.empty:
            return pd.DataFrame()
        out = base_cli.merge(
            df_venc,
            left_on="TERMINACION",
            right_on="terminacion",
            how="left"
        )
        out["ORGANISMO_LABEL"] = label_org
        return out

    df_arca_cli = _venc_por_flag(df_cartera, "ARCA_FLAG", v_arca, "ARCA")
    df_dgr_cli  = _venc_por_flag(df_cartera, "DGR_FLAG",  v_dgr,  "DGR IIBB")
    df_atp_cli  = _venc_por_flag(df_cartera, "ATP_FLAG",  v_atp,  "ATP IIBB")
    df_ts_cli   = _venc_por_flag(df_cartera, "TS_FLAG",   v_ts,   "TS Mun")

    df_cartera_venc = pd.concat([df_arca_cli, df_dgr_cli, df_atp_cli, df_ts_cli], ignore_index=True)
    if df_cartera_venc.empty:
        st.warning("⚠️ No se generaron vencimientos: revisá flags de la cartera o el Excel de vencimientos.")
        st.stop()

    # Limpieza de columnas útiles
    # (si existe RAZON_SOCIAL opcional, mostrar)
    col_rs = "RAZON_SOCIAL (OPCIONAL)" if "RAZON_SOCIAL (OPCIONAL)" in df_cartera_venc.columns else None
    cols_show = ["CUIT"]
    if col_rs:
        cols_show.append(col_rs)

    cols_show += [
        "ORGANISMO_LABEL",
        "impuesto",
        "fecha",
        "dias_restantes",
        "estado",
        "vencimiento",
        "terminacion"
    ]

    # ======================================================
    # PASO 4 · RESUMEN POR PRIORIDAD + DESPLEGABLES POR ORGANISMO
    # ======================================================
    st.markdown("### 📌 Paso 3 · Estado por cartera (organismos)")

    # Conteo estados sobre la cartera (no base completa)
    def _count_estado(df_, e):
        if df_.empty:
            return 0
        return int((df_["estado"] == e).sum())

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("🔴 Vence hoy / mañana", _count_estado(df_cartera_venc, "🔴"))
    r2.metric("🟡 Próximos días", _count_estado(df_cartera_venc, "🟡"))
    r3.metric("🟢 En regla", _count_estado(df_cartera_venc, "🟢"))
    r4.metric("⚪ Cumplidos", _count_estado(df_cartera_venc, "⚪"))

    st.markdown("---")

    # Función de tabla compacta
    def _tabla_org(df_org: pd.DataFrame):
        if df_org.empty:
            st.info("Sin vencimientos para este organismo en la cartera.")
            return
        view = df_org[cols_show].copy()

        # Orden sugerido: primero urgentes, luego por fecha
        order_map = {"🔴": 0, "🟡": 1, "🟢": 2, "⚪": 3}
        view["_ord"] = view["estado"].map(order_map).fillna(9)
        view = view.sort_values(by=["_ord", "fecha", "CUIT"]).drop(columns=["_ord"])

        st.dataframe(
            view.rename(columns={
                "impuesto": "Impuesto",
                "fecha": "Fecha",
                "dias_restantes": "Días",
                "estado": "Estado",
                "vencimiento": "Vencimiento",
                "terminacion": "Term.",
                "ORGANISMO_LABEL": "Organismo"
            }),
            hide_index=True,
            use_container_width=True
        )

    # Desplegables (no cargan la vista)
    # ✅ Prioridad: ARCA primero
    with st.expander("🔵 ARCA (prioridad 1)", expanded=True):
        _tabla_org(df_cartera_venc[df_cartera_venc["ORGANISMO_LABEL"] == "ARCA"])

    with st.expander("🟢 DGR Corrientes · IIBB (prioridad 2)", expanded=False):
        _tabla_org(df_cartera_venc[df_cartera_venc["ORGANISMO_LABEL"] == "DGR IIBB"])

    with st.expander("🟠 ATP Chaco · IIBB (prioridad 2)", expanded=False):
        _tabla_org(df_cartera_venc[df_cartera_venc["ORGANISMO_LABEL"] == "ATP IIBB"])

    with st.expander("🟣 Tasa Municipal (prioridad 3)", expanded=False):
        _tabla_org(df_cartera_venc[df_cartera_venc["ORGANISMO_LABEL"] == "TS Mun"])

    st.markdown("---")
    st.markdown("""
    ⚪ **Cumplido** &nbsp;&nbsp; 🔴 **Vence hoy / mañana** &nbsp;&nbsp; 🟡 **Próximos días** &nbsp;&nbsp; 🟢 **En regla**
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

