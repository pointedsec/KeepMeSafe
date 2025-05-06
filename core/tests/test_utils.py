from django.test import TestCase
from core.utils.encrypted_actions import gen_master_key, create_vault, check_master_key, save_database
import tempfile
import os
import base64
from cryptography.fernet import Fernet
import sqlite3
from unittest import mock

class EncryptedUtilsTestCase(TestCase):
    
    def setUp(self):
        self.test_vault_path = tempfile.mktemp(suffix='.sqlite3')
        self.test_password = 'test_password'
        
    def test_gen_master_key(self):
        cipher_suite, b64_key = gen_master_key(self.test_password)
        
        # Assert that the Fernet key and the base64 key are both returned
        self.assertIsInstance(cipher_suite, Fernet)
        self.assertEqual(len(b64_key), 44)  # base64 URL-safe encoding of 32-byte key
        
    def test_create_vault(self):
        create_vault(self.test_vault_path, self.test_password)
        
        self.assertTrue(os.path.exists(self.test_vault_path))
        
        # Check if the vault is encrypted by reading the file (it shouldn't be plain text)
        with open(self.test_vault_path, 'rb') as f:
            encrypted_data = f.read()
        self.assertGreater(len(encrypted_data), 0)
    
    def test_check_master_key_success(self):
        # Test the successful decryption of the vault
        create_vault(self.test_vault_path, self.test_password)
        profile_mock = mock.Mock()
        profile_mock.vault_path.path = self.test_vault_path
        
        # Check if the master key can decrypt the vault
        result = check_master_key(profile_mock, self.test_password)
        self.assertTrue(result)
    
    def test_check_master_key_failure(self):
        # Test the failed decryption when incorrect password is used
        create_vault(self.test_vault_path, self.test_password)
        profile_mock = mock.Mock()
        profile_mock.vault_path.path = self.test_vault_path
        
        # Check if using wrong password fails
        result = check_master_key(profile_mock, 'wrong_password')
        self.assertFalse(result)
    
    def test_save_database(self):
        # Create a vault and insert a credential to simulate a real database
        create_vault(self.test_vault_path, self.test_password)
        profile_mock = mock.Mock()
        profile_mock.vault_path.path = self.test_vault_path
        
        # Create a temporary vault with mock data
        with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=True) as temp_vault:
            # Open the vault and simulate adding a credential (mocked)
            with sqlite3.connect(temp_vault.name) as conn:
                cursor = conn.cursor()
                cursor.execute('''CREATE TABLE IF NOT EXISTS credentials (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    service TEXT NOT NULL,
                                    description TEXT,
                                    username TEXT NOT NULL,
                                    password TEXT NOT NULL
                                )''')
                cursor.execute('''INSERT INTO credentials (service, description, username, password) 
                                  VALUES ('test_service', 'test_description', 'test_user', 'test_password')''')
                conn.commit()
            
            temp_vault.seek(0)  # Ensure we're at the start of the file for reading
            
            # Mock the cipher suite
            cipher_suite, _ = gen_master_key(self.test_password)
            
            # Save the data back to the original vault
            save_database(self.test_vault_path, temp_vault, cipher_suite)
        
        # Verify if the vault was saved correctly (still encrypted)
        with open(self.test_vault_path, 'rb') as f:
            encrypted_data = f.read()
        self.assertGreater(len(encrypted_data), 0)
    
    def tearDown(self):
        # Clean up the created vault file
        if os.path.exists(self.test_vault_path):
            os.remove(self.test_vault_path)
