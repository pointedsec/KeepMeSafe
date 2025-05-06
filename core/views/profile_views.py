from django.shortcuts import render, redirect, get_object_or_404
from core.forms import ProfileForm, CredentialForm
import sqlite3
import os
from django.conf import settings
import tempfile
import logging
import uuid
from core.models import Profile
from core.utils.encrypted_actions import create_vault, save_database
from cryptography.fernet import Fernet
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_profile(request):
    # Only admins can create vaults
    if not request.session.get('admin_authenticated'):
        return redirect('admin_gate')
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            profile = form.save(commit=False)

            # Generate the vault_path
            vault_path = os.path.join(settings.MEDIA_ROOT, 'vaults', f"{uuid.uuid4()}.sqlite3")
            logger.info('Vault path generated %s', vault_path)
            # Create the encrypted vault, cypher it and save the model
            create_vault(vault_path, password)
            profile.vault_path = vault_path
            profile.save()
            request.session.pop('admin_authenticated', None)
            return redirect('profile_created', profile_id=profile.id)
        else:
            return render(request, 'core/create_profile.html', {'form': form})
    else:
        form = ProfileForm()
        
    return render(request, 'core/create_profile.html', {'form': form})

def profile_created(request, profile_id):
    return render(request, 'core/profile_created.html', {'profile_id': profile_id})

# Also this method insert, update or delete a credential
def profile_accessed(request, profile_id):
    encoded_key = request.session.get('vault_key')
    if not encoded_key:
        logger.error('Profile accessed without vault key..')
        return redirect('/')
    
    form = CredentialForm(request.POST or None)

    try:
        logger.info('Fernet created with vault key')
        cipher = Fernet(encoded_key.encode())
    except Exception as e:
        logger.error("Error decoding vault key: %s", e)
        return redirect('/')

    profile = get_object_or_404(Profile, id=profile_id)
    vault_path = profile.vault_path.path

    try:
        # Read and decrypt the vault
        with open(vault_path, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = cipher.decrypt(encrypted_data)
        logger.info('Data decrypted for vault %s', profile.name)

        # Write the decrypted vault in a temporal file
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=True) as temp_vault:
            temp_vault.write(decrypted_data)
            temp_vault.flush()
            logger.info('Temporal decrypted vault file created for vault %s', profile.name)

            # Create a db instance with that file
            with sqlite3.connect(temp_vault.name) as conn:
                cursor = conn.cursor()
                logger.info('sqlite3 instance created for vault %s', profile.name)
                # Add a new credential
                if request.method == 'POST' and form.is_valid():
                    cursor.execute(
                    "INSERT INTO credentials (service, description, username, password) VALUES (?, ?, ?, ?)",
                    (
                        form.cleaned_data['service'],
                        form.cleaned_data['description'],
                        form.cleaned_data['username'],
                        form.cleaned_data['password']
                    )
                    )
                    conn.commit()
                    logger.info('inserted credential in vault %s', profile.name)
                    form = CredentialForm(None)
                    save_database(vault_path, temp_vault, cipher)
                 
                # Delete a credential
                if 'delete_credential' in request.POST:
                    credential_id = request.POST['delete_credential']
                    cursor.execute("DELETE FROM credentials WHERE id = ?", (credential_id,))
                    conn.commit()
                    logger.info('Delete credential in vault %s', profile.name)
                    save_database(vault_path, temp_vault, cipher)
                    form = CredentialForm(None)

                # Edit a credential
                if 'edit_credential' in request.POST:
                    credential_id = request.POST['edit_credential']
                    edited_service = request.POST['edited_service']
                    edited_description = request.POST['edited_description']
                    edited_user = request.POST['edited_user']
                    edited_password = request.POST['edited_password']
                    cursor.execute("UPDATE credentials SET service = ?, description = ?, username = ?, password = ? WHERE id = ?", (edited_service, edited_description, edited_user, edited_password, credential_id))
                    conn.commit()
                    logger.info('Updated credential in vault %s', profile.name)
                    save_database(vault_path, temp_vault, cipher)
                    form = CredentialForm(None)

                cursor.execute("SELECT id, service, description, username, password FROM credentials")
                credentials = cursor.fetchall()


    except Exception as e:
        logger.error("Error decrypting or loading the vault: %s", e)
        return redirect('/')        

    return render(request, 'core/profile_accessed.html', {
        'profile': profile,
        'credentials': credentials,
        'form': form
    })
