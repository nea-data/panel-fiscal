import pandas as pd

REQUIRED_COLUMNS = [
    "cuit", "clave", "nombre",
    "emitidos", "recibidos",
    "desde", "hasta"
]

def cargar_clientes(path_excel: str) -> list[dict]:
    df = pd.read_excel(path_excel)

    # -------------------------
    # Validación de columnas
    # -------------------------
    faltantes = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en el Excel: {faltantes}")

    clientes = []

    for idx, row in df.iterrows():
        cuit = str(row["cuit"]).strip()
        clave = str(row["clave"]).strip()
        nombre = str(row["nombre"]).strip()

        emitidos = str(row["emitidos"]).strip().upper() == "SI"
        recibidos = str(row["recibidos"]).strip().upper() == "SI"

        desde = str(row["desde"]).strip()
        hasta = str(row["hasta"]).strip()

        # Validaciones suaves
        if not cuit or not clave:
            continue

        if not emitidos and not recibidos:
            continue

        clientes.append({
            "usuario": cuit,
            "clave": clave,
            "nombre": nombre,
            "emitidos": emitidos,
            "recibidos": recibidos,
            "desde": desde,
            "hasta": hasta
        })

    return clientes
