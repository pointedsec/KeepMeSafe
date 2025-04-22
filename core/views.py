from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProfileForm, LoginProfileForm, CredentialForm
import sqlite3
import os
from django.conf import settings
import tempfile
import logging
import uuid
from .models import Profile
from .utils.encrypted_actions import gen_master_key, create_vault, check_master_key, save_database
from cryptography.fernet import Fernet
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                logging.debug('Incorrect password introduced for a profile')
                form.add_error('password', 'The profile and master password combination is incorrect')
    else:
        form = LoginProfileForm()

    return render(request, 'core/login_profile.html', {'form': form})

def profile_accessed(request, profile_id):
    encoded_key = request.session.get('vault_key')
    if not encoded_key:
        return redirect('/')
    
    form = CredentialForm(request.POST or None)

    try:
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

        # Write the decrypted vault in a temporal file
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=True) as temp_vault:
            temp_vault.write(decrypted_data)
            temp_vault.flush()

            # Create a db instance with that file
            with sqlite3.connect(temp_vault.name) as conn:
                cursor = conn.cursor()
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
                    save_database(vault_path, temp_vault, cipher)
                 
                # Delete a credential
                if 'delete_credential' in request.POST:
                    credential_id = request.POST['delete_credential']
                    cursor.execute("DELETE FROM credentials WHERE id = ?", (credential_id,))
                    conn.commit()
                    save_database(vault_path, temp_vault, cipher)
                    form = CredentialForm(None)

                # Edit a credential
                if 'edit_credential' in request.POST:
                    credential_id = request.POST['edit_credential']
                    edited_service = request.POST['edited_service']
                    edited_description = request.POST['edited_description']
                    edited_user = request.POST['edited_user']
                    edited_password = request.POST['edited_password']
                    print(credential_id, edited_service, edited_description, edited_user, edited_password)
                    cursor.execute("UPDATE credentials SET service = ?, description = ?, username = ?, password = ? WHERE id = ?", (edited_service, edited_description, edited_user, edited_password, credential_id))
                    conn.commit()
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


    