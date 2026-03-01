# auth/passwords.py
import bcrypt

def hash_password(password: str) -> str:
    if not password or len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
