import bcrypt

# Ya no usamos CryptContext, usamos la lógica nativa de bcrypt
def hash_password(password: str) -> str:
    """Hashea la contraseña para guardarla en la BD del estudio contable."""
    # Convertimos el string a bytes para el algoritmo
    pwd_bytes = password.encode('utf-8')
    # Generamos el salt y el hash en un solo paso
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    # Retornamos como string para que SQL (psycopg2) lo guarde sin problemas
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verifica la contraseña contra el hash almacenado."""
    if not hashed:
        return False
    try:
        # Bcrypt.checkpw maneja la comparación de forma segura (constant-time)
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed.encode('utf-8')
        )
    except Exception:
        # Manejo de errores por si el hash en la DB está corrupto o vacío
        return False
