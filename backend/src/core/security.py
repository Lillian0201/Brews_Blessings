from werkzeug.security import check_password_hash, generate_password_hash


def password_matches(stored: str, given: str) -> bool:
    try:
        return check_password_hash(stored, given)
    except ValueError:
        return False


def hash_password(password: str) -> str:
    return generate_password_hash(password)
