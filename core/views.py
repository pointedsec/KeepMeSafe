from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProfileForm, LoginProfileForm
import hashlib
from cryptography.fernet import Fernet
import sqlite3
import os
import io
from django.conf import settings
from typing import Tuple 
import base64
import logging
import uuid
from .models import Profile

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
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        logging.info('Vault decrypted for profile %s!', profile.name)
        return True
    except Exception as e:
        logging.debug('Error decrypting the vault %s', e)
        return False

def create_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            profile = form.save(commit=False)

            # Generate the vault_path
            vault_path = os.path.join(settings.MEDIA_ROOT, 'vaults', f"{uuid.uuid4()}.sqlite3")
            logging.info('Vault path generated %s', vault_path)
            # Create the encrypted vault, cypher it and save the model
            create_vault(vault_path, password)
            profile.vault_path = vault_path
            profile.save()

            return redirect('profile_created', profile_id=profile.id)
    else:
        form = ProfileForm()
        
    return render(request, 'core/create_profile.html', {'form': form})

def profile_created(request, profile_id):
    return render(request, 'core/profile_created.html', {'profile_id': profile_id})

def login_profile(request):
    if request.method == 'POST':
        form = LoginProfileForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['name']
            password = form.cleaned_data['password']
            # Check if a profile exists with that username
            try:
                profile = Profile.objects.get(name=username)
                # Check if the password is valid for his vault
                if check_master_key(profile, password):
                    logging.debug('Profile accesed succesfully, profile: %s', username)
                    fernet, encoded_key = gen_master_key(password)
                    request.session['vault_key'] = encoded_key
                    return redirect('profile_accessed', profile_id=profile.id)
                else:
                    form.add_error('password', 'The profile and master password combination is incorrect')
            except Profile.DoesNotExist:
                logging.debug('Incorrect password introduced for profile: %s', profile.name)
                form.add_error('password', 'The profile and master password combination is incorrect')
    else:
        form = LoginProfileForm()

    return render(request, 'core/login_profile.html', {'form': form})

def profile_accessed(request, profile_id):
    encoded_key = request.session.get('vault_key')
    if not encoded_key:
        return redirect('login_profile')
    try:
        cipher = Fernet(encoded_key.encode())
    except Exception:
        return redirect('login_profile')
    
    # Check if Profile exists
    profile = get_object_or_404(Profile, id=profile_id)

    # TODO: Decrypt user vault
    