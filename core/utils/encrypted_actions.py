import hashlib
import base64
from typing import Tuple
from cryptography.fernet import Fernet
import sqlite3
import logging
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def gen_master_key(password) -> Tuple[Fernet,str]:
    """
    Generates a SHA256 hash of the master key, it generates
    a private key for Fernet use
    The master key will not be stored
    Returns a tuple with the Fernet Object, or the base64 master key
    """
    logger.info('Generating master key')
    sha256_hash = hashlib.sha256(password.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(sha256_hash)
    logger.info('Master key generated!')
    return Fernet(fernet_key), fernet_key.decode()

def create_vault(vault_path, password):
    """
    Creates an empty SQLite file and cypher it using the generated key using the master key
    """
    logger.debug('Creating vault, path: %s', vault_path)
    connection = sqlite3.connect(vault_path)
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS credentials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service TEXT NOT NULL,
                        description TEXT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL
                    )''')
    connection.commit()
    connection.close()
    logger.info('Vault created!')

    logger.info('Encrypting the file!')
    # cipher the file
    cipher_suite, b64_key = gen_master_key(password)
    with open(vault_path, 'rb') as f:
        data = f.read()
    encrypted_data = cipher_suite.encrypt(data)

    with open(vault_path, 'wb') as f:
        f.write(encrypted_data)
    logger.info('Vault encrypted!')

def check_master_key(profile, password):
    """
    Checks if the master key can decrypt his vault
    """
    logging.info('Trying to decrypt the vault')
    vault_path = profile.vault_path.path
    cipher_suite, b64_key = gen_master_key(password)

    try:
        with open(vault_path, 'rb') as f:
            encrypted_data = f.read()
        cipher_suite.decrypt(encrypted_data)
        logging.info('Vault decrypted for profile %s!', profile.name)
        return True
    except Exception as e:
        logging.debug('Error decrypting the vault %s', e)
        return False
    
def save_database(vault_path: str, temp_vault, cipher: Fernet) -> None:
    """
    Re-encrypts the vault from the temporary SQLite database and saves it back to the original path.
    """
    try:
        # Volver a posicionar el puntero del archivo al inicio para leerlo completo
        temp_vault.seek(0)
        decrypted_data = temp_vault.read()

        # Encriptar los datos
        encrypted_data = cipher.encrypt(decrypted_data)

        # Guardar sobre el vault original
        with open(vault_path, 'wb') as f:
            f.write(encrypted_data)

        logger.info("Vault successfully updated and encrypted.")
    except Exception as e:
        logger.error("Error saving encrypted vault: %s", e)
        raise
