import hashlib
import base64
from typing import Tuple
from cryptography.fernet import Fernet
import sqlite3
import logging
import tempfile
import os

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
    logger.info('Trying to decrypt the vault')
    vault_path = profile.vault_path.path
    cipher_suite, b64_key = gen_master_key(password)

    try:
        with open(vault_path, 'rb') as f:
            encrypted_data = f.read()
        cipher_suite.decrypt(encrypted_data)
        logger.info('Vault decrypted for profile %s!', profile.name)
        return True
    except Exception as e:
        logger.debug('Error decrypting the vault %s', e)
        return False
    
def save_database(vault_path: str, temp_vault, cipher: Fernet) -> None:
    """
    Re-encrypts the vault from the temporary SQLite database and saves it back to the original path.
    """
    try:
        # Seek to the beginning of the file to ensure full read
        temp_vault.seek(0)
        decrypted_data = temp_vault.read()

        # Encrypt the data
        encrypted_data = cipher.encrypt(decrypted_data)

        # Save in the original vault (replaces the file with the encrypted data)
        with open(vault_path, 'wb') as f:
            f.write(encrypted_data)

        logger.info("Vault successfully updated and encrypted.")
    except Exception as e:
        logger.error("Error saving encrypted vault: %s", e)
        raise

def update_vault_encryption_key(vault_path, cipher: Fernet, password):
    """
    Decrypt the user vault with the actual password and encrypt it again using a new vault key.
    """
    try:
        # Read and decrypt the vault
        with open(vault_path, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = cipher.decrypt(encrypted_data)
        logger.info('Data decrypted for vault %s', vault_path)

        # Write the vault in a temporal file
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as temp_vault:
            temp_vault.write(decrypted_data)
            temp_vault_path = temp_vault.name
            logger.info('Temporary decrypted vault file created: %s', temp_vault_path)

        # Create a new key using the new password
        new_cipher_suite, b64_key = gen_master_key(password)

        # Read the decrypted data and encrypt it again with the new key
        with open(temp_vault_path, 'rb') as f:
            data_to_encrypt = f.read()
        encrypted_data = new_cipher_suite.encrypt(data_to_encrypt)

        # Re-write the original file
        with open(vault_path, 'wb') as f:
            f.write(encrypted_data)
        logger.info('Vault re-encrypted with new key for vault %s', vault_path)

    except Exception as e:
        logger.error('Error updating encryption key for vault %s: %s', vault_path, e)
        raise e

    finally:
        # Delete the temporal file
        if 'temp_vault_path' in locals() and os.path.exists(temp_vault_path):
            os.remove(temp_vault_path)
            logger.info('Temporary file %s removed', temp_vault_path)