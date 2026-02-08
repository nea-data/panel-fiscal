import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
from io import BytesIO
from auth.guard import require_admin


# ======================================================
# AUTH / USUARIO ACTUAL + LANDING
# ======================================================
from auth.google_auth import get_current_user
from auth.schema import init_db
from auth.users import upsert_user_on_login

init_db()

current_user = get_current_user()

# ======================================================
# ACCESO PENDIENTE / USUARIO SUSPENDIDO
# ======================================================

if not db_user.get("is_active", False):
    st.markdown("""
    <div style="text-align:center; margin-top:80px;">
        <h2>🔒 Acceso pendiente de habilitación</h2>
        <p style="color:#9CA3AF; font-size:16px;">
            Tu cuenta fue registrada correctamente, pero aún no está habilitada.
        </p>
        <p style="color:#6EE7B7; font-size:15px;">
            📩 Contactá a <b>neadata.contacto@gmail.com</b><br>
            para activar tu suscripción.
        </p>
        <br>
        <p style="color:#6B7280; font-size:13px;">
            NEA DATA · Panel Fiscal
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.stop()


# ------------------------------------------------------
# LANDING DE INGRESO (ANTES DEL LOGIN)
# ------------------------------------------------------
if not current_user or not hasattr(current_user, "email") or not current_user.email:

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align: center;">
            <h2 style="margin-bottom: 0;">📊 NEA DATA · Panel Fiscal</h2>
            <p style="color: #9CA3AF; margin-top: 6px;">
                Gestión fiscal · Consultas de CUIT · Automatización contable
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center;">
                <p style="color: #E5E7EB;">
                    Accedé de forma segura utilizando tu cuenta de Google.
                </p>
                <p style="color: #6B7280; font-size: 13px;">
                    🔐 No almacenamos contraseñas ni claves fiscales.<br>
                    📩 Acceso habilitado solo para usuarios autorizados.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        

    st.stop()

# ------------------------------------------------------
# USUARIO AUTENTICADO (YA CON EMAIL)
# ------------------------------------------------------
db_user = upsert_user_on_login(
    email=current_user.email,
    name=getattr(current_user, "name", "")
)

st.session_state["db_user"] = db_user


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


if db_user["role"] == "admin":
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
# SECCIÓN ADMINISTRACIÓN
# ======================================================
elif seccion == "🛠 Administración":

    from auth.guard import require_admin
    from auth.users import (
        list_users,
        set_user_status,
        set_user_role,
    )
    from auth.subscriptions import (
        create_subscription,
        renew_subscription,
        change_plan,
        suspend_subscription,
    )
    from auth.limits import get_current_period
    from auth.extras import grant_usage_extras, get_usage_extras
    from auth.service import get_usage_status

    # 🔐 Validación real de admin (sin password)
    admin = require_admin()
    admin_email = admin["email"]

    st.markdown("## 🛠 Panel de Administración")

    # ===============================
    # 👤 USUARIOS
    # ===============================
    st.subheader("👤 Usuarios registrados")

    users = list_users()
    if not users:
        st.info("No hay usuarios registrados todavía.")
        st.stop()

    users_df = pd.DataFrame(users)
    st.dataframe(
        users_df[["id", "email", "name", "role", "status", "created_at", "last_login_at"]],
        use_container_width=True,
        hide_index=True,
    )

    selected_email = st.selectbox(
        "Seleccionar usuario",
        users_df["email"]
    )

    selected_user = users_df.loc[
        users_df["email"] == selected_email
    ].iloc[0]

    user_id = int(selected_user["id"])

    st.divider()

    # ===============================
    # 🔧 ESTADO Y ROL
    # ===============================
    st.subheader("🔧 Estado y rol del usuario")

    col1, col2 = st.columns(2)

    with col1:
        new_status = st.selectbox(
            "Estado",
            ["pending", "active", "suspended"],
            index=["pending", "active", "suspended"].index(selected_user["status"])
        )

        if st.button("Guardar estado"):
            set_user_status(
                user_id=user_id,
                status=new_status,
                admin_email=admin_email
            )
            st.success("Estado actualizado.")
            st.rerun()

    with col2:
        new_role = st.selectbox(
            "Rol",
            ["user", "admin"],
            index=["user", "admin"].index(selected_user["role"])
        )

        if st.button("Guardar rol"):
            set_user_role(
                user_id=user_id,
                role=new_role,
                admin_email=admin_email
            )
            st.success("Rol actualizado.")
            st.rerun()

    st.divider()

    # ===============================
    # 📦 SUSCRIPCIÓN (30 días rolling)
    # ===============================
    st.subheader("📦 Suscripción")

    plan_code = st.selectbox(
        "Plan",
        ["FREE", "PRO", "STUDIO"],
        index=1
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Crear suscripción (30 días)"):
            create_subscription(
                user_id=user_id,
                plan_code=plan_code,
                days=30,
                changed_by=f"admin:{admin_email}"
            )
            st.success("Suscripción creada.")
            st.rerun()

    with col2:
        if st.button("🔁 Renovar +30 días"):
            renew_subscription(
                user_id=user_id,
                days=30,
                changed_by=f"admin:{admin_email}"
            )
            st.success("Suscripción renovada.")
            st.rerun()

    with col3:
        if st.button("🔄 Cambiar plan (sin renovar)"):
            change_plan(
                user_id=user_id,
                new_plan_code=plan_code,
                changed_by=f"admin:{admin_email}"
            )
            st.success("Plan actualizado.")
            st.rerun()

    st.divider()

    # ===============================
    # 📊 USO MENSUAL + EXTRAS
    # ===============================
    st.subheader("📊 Uso mensual y extras")

    period = get_current_period()
    status = get_usage_status(user_id)
    extras = get_usage_extras(user_id, period)

    colA, colB, colC = st.columns(3)

    with colA:
        st.metric("CUITs", status["cuit_display"])
    with colB:
        st.metric("Extractores", status["bank_display"])
    with colC:
        st.metric("Días hasta vencimiento", str(status["days_left"] or "-"))

    st.caption(f"Período actual: {period}")

    st.divider()

    st.markdown("### ➕ Otorgar extras para este período")

    col1, col2 = st.columns(2)

    with col1:
        extra_cuit = st.number_input(
            "CUITs extras",
            min_value=0,
            value=int(extras["extra_cuit"]),
            step=10
        )

    with col2:
        extra_bank = st.number_input(
            "Extractores extras",
            min_value=0,
            value=int(extras["extra_bank"]),
            step=1
        )

    note = st.text_input("Nota interna (opcional)")

    if st.button("Guardar extras"):
        grant_usage_extras(
            user_id=user_id,
            period=period,
            extra_cuit=int(extra_cuit),
            extra_bank=int(extra_bank),
            granted_by=f"admin:{admin_email}",
            note=note
        )
        st.success("Extras actualizados.")
        st.rerun()

    st.divider()

    # ===============================
    # ➕ ALTA MANUAL DE USUARIO
    # ===============================
    st.subheader("➕ Alta manual de usuario")

    with st.form("alta_usuario"):
        email = st.text_input("Email")
        name = st.text_input("Nombre")
        plan_code_new = st.selectbox("Plan inicial", ["FREE", "PRO", "STUDIO"])
        submit = st.form_submit_button("Crear usuario")

        if submit:
            from auth.users import upsert_user_on_login

            new_user = upsert_user_on_login(email=email, name=name)

            create_subscription(
                user_id=new_user["id"],
                plan_code=plan_code_new,
                days=30,
                changed_by=f"admin:{admin_email}"
            )

            set_user_status(
                user_id=new_user["id"],
                status="active",
                admin_email=admin_email
            )

            st.success("Usuario creado y activado correctamente.")
            st.rerun()


# ======================================================
# FOOTER
# ======================================================
st.markdown("---")
st.markdown(
    "<small>© 2026 <b>NEA DATA</b> · Soluciones en Ciencia de Datos y Automatización · Corrientes, Argentina</small>",
    unsafe_allow_html=True
)

