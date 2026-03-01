import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
from io import BytesIO

# ======================================================
# 1. CONFIG STREAMLIT (DEBE SER LO PRIMERO)
# ======================================================
st.set_page_config(
    page_title="NEA DATA · Panel Fiscal",
    page_icon="📊",
    layout="wide"
)

# ======================================================
# INIT DB (UNA SOLA VEZ)
# ======================================================

from auth.schema import init_db
init_db()

# ✅ Bootstrap admin (solo si falta)
from auth.bootstrap import ensure_bootstrap_admin
ensure_bootstrap_admin()

# ======================================================
# LOGIN
# ======================================================

from auth.users import authenticate_user
from auth.passwords import hash_password
from auth.db import get_connection


def logout():
    st.session_state.pop("db_user", None)
    st.rerun()


def login_ui():
    st.title("🔐 Acceso al Panel Fiscal")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar")

    if submit:
        user, error = authenticate_user(email.strip(), password)

        if error:
            st.error(error)
            st.stop()

        st.session_state["db_user"] = user
        st.rerun()


db_user = st.session_state.get("db_user")

if not db_user:
    login_ui()
    st.stop()

# ======================================================
# VALIDACIÓN STATUS
# ======================================================

if db_user.get("status") in ("pending", "suspended"):
    st.error("Tu usuario no está activo. Contactá al administrador.")
    st.stop()

# ======================================================
# FORZAR CAMBIO DE PASSWORD
# ======================================================

if db_user.get("must_change_password"):

    st.warning("⚠️ Debés cambiar tu contraseña para continuar.")

    with st.form("change_password_form"):
        p1 = st.text_input("Nueva contraseña", type="password")
        p2 = st.text_input("Repetir contraseña", type="password")
        submit_pw = st.form_submit_button("Guardar")

    if submit_pw:

        if len(p1) < 8:
            st.error("La contraseña debe tener al menos 8 caracteres.")
            st.stop()

        if p1 != p2:
            st.error("Las contraseñas no coinciden.")
            st.stop()

        new_hash = hash_password(p1)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s, must_change_password = false WHERE id = %s",
            (new_hash, db_user["id"])
        )
        conn.commit()
        cur.close()
        conn.close()

        st.success("Contraseña actualizada correctamente.")
        st.session_state["db_user"]["must_change_password"] = False
        st.rerun()

    st.stop()

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
st.sidebar.success(f"👤 {db_user['name']} ({db_user['email']})")
st.sidebar.button("🚪 Cerrar sesión", on_click=logout)

st.sidebar.markdown("## 📊 **NEA DATA**")
st.sidebar.markdown("Soluciones en Ciencia de Datos y Automatización")
st.sidebar.markdown("---")


# Definimos los menús según el rol que traemos de Supabase
if db_user["role"] == "admin":
    # Menú exclusivo para David (Admin)
    MENU = ["🛠 Administración"]
else:
    # Menú exclusivo para los Contadores (Clientes)
    MENU = [
        "📅 Gestión Fiscal", 
        "🔎 Consultor de CUITs", 
        "🏦 Extractos Bancarios", 
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
    from auth.service import consume_quota_db
    from auth.limits import get_current_period
    
    st.markdown("## 🔎 Consultor de CUITs")
    st.markdown("<div class='subtitulo'>Consulta fiscal individual y masiva</div>", unsafe_allow_html=True)
    st.info("🔐 La consulta se realiza en tiempo real. No se almacena información.")
    st.markdown("---")

    tipo = st.radio(
        "Tipo de consulta",
        ["Consulta individual", "Consulta masiva (Excel)"],
        horizontal=True
    )

    # ======================================================
    # CONSULTA INDIVIDUAL (SIN LÍMITE)
    # ======================================================
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

    # ======================================================
    # CONSULTA MASIVA (CON LÍMITE)
    # ======================================================
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

                    # ---------------------------------------------------
                    # 0️⃣ Validar sesión y user_id
                    # ---------------------------------------------------
                    if "db_user" not in st.session_state:
                        st.error("Sesión inválida. Volvé a iniciar sesión.")
                        st.stop()

                    user_id = st.session_state["db_user"]["id"]

                    # ---------------------------------------------------
                    # 1️⃣ Detectar CUIT válidos
                    # ---------------------------------------------------
                    cuits_validos = []

                    for row in df_in.to_dict(orient="records"):
                        raw = (row.get(col_cuit) or "").strip()
                        cuit_norm = "".join(ch for ch in raw if ch.isdigit())

                        if cuit_norm.isdigit() and len(cuit_norm) == 11:
                            cuits_validos.append(cuit_norm)

                    # 🔹 Eliminar duplicados
                    cuits_unicos = list(dict.fromkeys(cuits_validos))
                    total_validos = len(cuits_unicos)

                    if total_validos == 0:
                        st.warning("No se encontraron CUIT válidos en el archivo.")
                        st.stop()

                    # ---------------------------------------------------
                    # 2️⃣ Validar y descontar cupo (ATÓMICO EN DB)
                    # ---------------------------------------------------
                    period = get_current_period()
                    quota = consume_quota_db(user_id, "cuit", total_validos, period)

                    if not quota["allowed"]:
                        st.error(
                            f"No alcanzan los cupos.\n"
                            f"Te quedan {quota['remaining']} disponibles "
                            f"y el archivo contiene {total_validos} CUIT válidos."
                        )
                        st.stop()

                    st.info(
                        f"Se descontarán {total_validos} consultas.\n"
                        f"Uso actual: {quota['used']}/{quota['limit_total']} "
                        f"(Restan {quota['remaining']})."
                    )

                    # ---------------------------------------------------
                    # 3️⃣ Procesar consultas (cobrar solo éxitos)
                    # ---------------------------------------------------
                    resultados = []
                    prog = st.progress(0)
                    consultas_exitosas = 0

                    for i, cuit in enumerate(cuits_unicos, start=1):
                        try:
                            res = consultar_cuit(cuit)
                            resultados.append(res)
                            consultas_exitosas += 1
                        except Exception as e:
                            resultados.append({"CUIT": cuit, "Error": str(e)})

                        prog.progress(int(i * 100 / total_validos))

                    df_out = pd.DataFrame(resultados)

                    # ---------------------------------------------------
                    # 4️⃣ Confirmación de procesamiento
                    # ---------------------------------------------------
                    st.success(
                        f"Consultas procesadas: {total_validos}. "
                        f"Uso actualizado correctamente."
                    )

                    # ---------------------------------------------------
                    # 5️⃣ Mostrar resultados
                    # ---------------------------------------------------
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
# SECCIÓN ADMINISTRACIÓN
# ======================================================
elif seccion == "🛠 Administración":

    from auth.guard import require_admin
    from auth.users import (
        set_user_status,
        set_user_role,
        get_user_by_email,
        set_user_password,
    )
    from auth.subscriptions import (
        create_subscription,
        renew_subscription,
        change_plan,
        suspend_subscription,
    )
    from auth.limits import get_current_period
    from auth.extras import grant_usage_extras, get_usage_extras
    from auth.admin_overview import get_admin_clients_overview
    from auth.db import get_connection
    import secrets

    # 🔐 Seguridad real
    admin = require_admin()
    admin_email = admin.get("email") or "system"

    st.markdown("## 🛠 Panel de Administración")

    period = get_current_period()

    # ======================================================
    # CACHE OVERVIEW (MEJORA PERFORMANCE)
    # ======================================================
    @st.cache_data(ttl=30)
    def load_overview():
        return pd.DataFrame(get_admin_clients_overview())

    df = load_overview()

    if df.empty:
        st.info("No hay clientes registrados todavía.")
        st.stop()

    # ======================================================
    # 1) DASHBOARD GENERAL
    # ======================================================
    total = len(df)
    activos = int((df["subscription_state"] == "ACTIVO").sum())
    vencidos = int((df["subscription_state"] == "VENCIDO").sum())
    por_vencer = int((df["subscription_state"] == "POR_VENCER").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Clientes", total)
    col2.metric("🟢 Activos", activos)
    col3.metric("🔴 Vencidos", vencidos)
    col4.metric("🟡 Por vencer", por_vencer)

    st.divider()

    # ======================================================
    # 2) TABLA CLIENTES
    # ======================================================
    st.markdown("### 📋 Clientes")

    st.dataframe(
        df.sort_values(["subscription_state", "days_left"]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ======================================================
    # 3) GESTIÓN INDIVIDUAL
    # ======================================================
    st.markdown("## 👤 Gestión individual")

    user_email = st.selectbox("Seleccionar cliente", df["email"].tolist())
    sel = df[df["email"] == user_email].iloc[0]
    user_id = int(sel["id"])

    # -----------------------------
    # ESTADO COMERCIAL
    # -----------------------------
    st.markdown("### 📦 Estado comercial")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Plan", sel.get("plan_code") or "-")
    c2.metric("Estado", sel.get("subscription_state"))
    c3.metric("Días restantes", sel.get("days_left") or "-")

    last_login = sel.get("last_login_at")
    if last_login:
        last_login = pd.to_datetime(last_login).strftime("%d/%m/%Y %H:%M")
    else:
        last_login = "Nunca"

    c4.metric("Último login", last_login)

    # ======================================================
    # CONSUMO
    # ======================================================
    st.markdown("### 📊 Consumo")

    st.markdown("**CUIT**")
    st.progress(min(float(sel.get("cuit_usage_pct") or 0) / 100, 1.0))
    st.caption(sel.get("cuit_display"))

    st.markdown("**Extractores**")
    st.progress(min(float(sel.get("bank_usage_pct") or 0) / 100, 1.0))
    st.caption(sel.get("bank_display"))

    st.divider()

    # ======================================================
    # ACCIONES COMERCIALES
    # ======================================================
    st.markdown("### 🎛 Acciones comerciales")

    plan_actual = sel.get("plan_code") or "FREE"

    plan_code = st.selectbox(
        "Plan",
        ["FREE", "PRO", "STUDIO"],
        index=["FREE", "PRO", "STUDIO"].index(plan_actual),
    )

    colA, colB, colC = st.columns(3)

    with colA:
        if st.button("🔁 Renovar 1 mes"):
            days = 7 if plan_code == "FREE" else 30
            renew_subscription(
                user_id=user_id,
                days=days,
                changed_by=f"admin:{admin_email}",
            )
            st.success("Suscripción renovada.")
            st.rerun()

    with colB:
        if st.button("🔄 Cambiar plan"):
            change_plan(
                user_id=user_id,
                new_plan_code=plan_code,
                changed_by=f"admin:{admin_email}",
            )
            st.success("Plan actualizado.")
            st.rerun()

    with colC:
        if st.button("⛔ Suspender"):
            suspend_subscription(
                user_id=user_id,
                changed_by=f"admin:{admin_email}",
            )
            st.warning("Suscripción suspendida.")
            st.rerun()

    st.divider()

    # ======================================================
    # EXTRAS
    # ======================================================
    st.markdown("### ➕ Extras del período")

    extras = get_usage_extras(user_id, period)

    col1, col2 = st.columns(2)

    with col1:
        extra_cuit = st.number_input(
            "CUITs extra",
            min_value=0,
            value=int(extras.get("extra_cuit", 0)),
        )

    with col2:
        extra_bank = st.number_input(
            "Extractores extra",
            min_value=0,
            value=int(extras.get("extra_bank", 0)),
        )

    if st.button("💾 Guardar extras"):
        grant_usage_extras(
            user_id=user_id,
            period=period,
            extra_cuit=int(extra_cuit),
            extra_bank=int(extra_bank),
            granted_by=f"admin:{admin_email}",
            note="",
        )
        st.success("Extras actualizados.")
        st.rerun()

    st.divider()

    # ======================================================
    # CONFIGURACIÓN USUARIO
    # ======================================================
    with st.expander("⚙ Configuración avanzada"):

        col1, col2 = st.columns(2)

        with col1:
            new_status = st.selectbox(
                "Status",
                ["pending", "active", "suspended"],
                index=["pending", "active", "suspended"].index(sel["status"]),
            )

            if st.button("Guardar status"):
                set_user_status(
                    user_id=user_id,
                    status=new_status,
                    admin_email=admin_email,
                )
                st.success("Status actualizado.")
                st.rerun()

        with col2:
            new_role = st.selectbox(
                "Rol",
                ["user", "admin"],
                index=["user", "admin"].index(sel["role"]),
            )

            if st.button("Guardar rol"):
                set_user_role(
                    user_id=user_id,
                    role=new_role,
                    admin_email=admin_email,
                )
                st.success("Rol actualizado.")
                st.rerun()

    st.divider()

    # ======================================================
    # ALTA MANUAL DE CLIENTE
    # ======================================================
    st.markdown("## ➕ Alta manual de cliente")

    with st.form("alta_usuario_form"):

        col1, col2 = st.columns(2)

        with col1:
            email_new = st.text_input("Email del cliente")
            name_new = st.text_input("Nombre / Razón Social")

        with col2:
            plan_new = st.selectbox("Plan inicial", ["FREE", "PRO", "STUDIO"])
            status_new = st.selectbox("Estado inicial", ["active", "pending"])

        submit_new = st.form_submit_button("Crear cliente")

        if submit_new:

            email_clean = email_new.strip().lower()

            if not email_clean or "@" not in email_clean:
                st.error("Ingresá un email válido.")
                st.stop()

            existing_user = get_user_by_email(email_clean)

            if existing_user:
                new_user = existing_user
                st.warning("El usuario ya existe. Se actualizarán datos.")
            else:
                conn = get_connection()
                cur = conn.cursor()

                cur.execute(
                    """
                    INSERT INTO users (email, name, role, status, created_at)
                    VALUES (%s, %s, 'user', %s, CURRENT_TIMESTAMP)
                    RETURNING *
                    """,
                    (email_clean, name_new.strip(), status_new)
                )

                new_user = dict(cur.fetchone())
                conn.commit()
                cur.close()
                conn.close()

            temp_password = secrets.token_urlsafe(10)

            set_user_password(
                user_id=new_user["id"],
                password=temp_password,
                admin_email=f"admin:{admin_email}",
            )

            create_subscription(
                user_id=new_user["id"],
                plan_code=plan_new,
                days=None,
                changed_by=f"admin:{admin_email}",
            )

            set_user_status(
                user_id=new_user["id"],
                status=status_new,
                admin_email=admin_email,
            )

            st.success("✅ Cliente creado correctamente.")
            st.info(f"🔑 Contraseña temporal: {temp_password}")
            st.warning("⚠️ Copiar ahora. Luego solo podrá resetearse.")

            st.rerun()
# ======================================================
# FOOTER
# ======================================================
st.markdown("---")
st.markdown(
    "<small>© 2026 <b>NEA DATA</b> · Soluciones en Ciencia de Datos y Automatización · Corrientes, Argentina</small>",
    unsafe_allow_html=True
)

