import secrets


def create_preview_id():
    return secrets.token_hex(16)
